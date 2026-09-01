"""멀티에이전트 파이프라인 정의 — 그래프 구조.

    입력 ─→ coder ─┬─→ tester   ─┐
                   └─→ reviewer ─┴─→ 판정 ─┬─ PASS → 끝
                        (병렬)             │
                        ↑                  └─ FAIL → coder (최대 max_attempts 회)
                        └──────────────────────┘

바뀐 점 (직선 파이프라인에서):
  ① 팬아웃      tester 와 reviewer 는 둘 다 생성 코드만 받는 독립 노드다. 같이 돌린다.
                실측 기준선: coder 4.0s + tester 10.5s + reviewer 22.5s = 37.0s 직렬
                             → coder 4.0s + max(10.5, 22.5) = 26.5s (약 28% 단축)
  ② 판정        "예외가 안 났다"는 성공이 아니다. 코드가 실제로 쓸 만한지 결정론적으로 본다.
                (기준선 첫 파일럿에서 coder 가 빈 문자열을 냈는데 [OK] 로 통과했다.)
  ③ 되돌아가기   판정이 FAIL 이면 실패 이유와 리뷰를 붙여 coder 를 다시 부른다.
  ④ 상태 저장   시도마다 runs/<run_id>/ 에 남긴다. 죽어도 어디서 끊겼는지 남는다.

판정은 LLM 에게 묻지 않는다. 기본 판정기는 구문 검사까지만 하고, 더 강한 검사(예: 실제
실행)가 필요하면 `verify` 로 주입한다 — 임의 코드 실행을 기본값으로 켜지 않기 위해서다.
"""

from __future__ import annotations

import ast
import asyncio
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Awaitable, Callable, Optional

from .agent_client import AgentPool


class PipelineStep(Enum):
    """파이프라인 단계"""
    CODE = "code"        # 코드 생성
    TEST = "test"        # 코드 테스트
    REVIEW = "review"    # 코드 리뷰
    VERDICT = "verdict"  # 판정 (LLM 아님)


@dataclass
class PipelineResult:
    """파이프라인 실행 결과"""
    step: PipelineStep
    agent_name: str
    success: bool
    content: str
    error: Optional[str] = None
    attempt: int = 1


@dataclass
class Verdict:
    """판정 결과. passed 가 False 면 reason 을 coder 에게 돌려준다."""
    passed: bool
    reason: str = ""
    checks: dict = field(default_factory=dict)


# 판정기 서명: (생성코드, tester 응답) -> Verdict
Verifier = Callable[[str, str], Verdict]

_CODE_BLOCK = re.compile(r"```(?:python|py)?\s*\n(.*?)```", re.S)
_FAIL_MARKS = ("테스트 실패", "오류 발생", "SyntaxError", "NameError", "Traceback")


def extract_code(text: str) -> str:
    """응답에서 파이썬 코드를 뽑는다. 코드블록이 없으면 본문 자체를 코드로 본다.

    (coder 의 시스템 프롬프트가 "마크다운 코드 블록을 쓰지 마세요"라고 지시하므로
     둘 다 나올 수 있다.)
    """
    blocks = _CODE_BLOCK.findall(text or "")
    if blocks:
        return max(blocks, key=len).strip()
    return (text or "").strip()


def default_verify(code_text: str, test_text: str) -> Verdict:
    """기본 판정 — 결정론적. LLM 에게 "잘 됐냐"고 묻지 않는다."""
    code = extract_code(code_text)
    checks = {"non_empty": bool(code), "parses": False, "tester_no_failure": True}

    if not code:
        return Verdict(False, "빈 응답 (코드 없음)", checks)

    try:
        ast.parse(code)
        checks["parses"] = True
    except SyntaxError as e:
        return Verdict(False, f"구문 오류: {e.msg} (line {e.lineno})", checks)

    hit = next((m for m in _FAIL_MARKS if m in (test_text or "")), None)
    if hit:
        checks["tester_no_failure"] = False
        return Verdict(False, f"tester 가 실패를 보고함: {hit}", checks)

    return Verdict(True, "", checks)


class CodePipeline:
    """coder → (tester ∥ reviewer) → 판정 → (실패 시 coder 로 되돌아감)"""

    def __init__(self, agent_pool: AgentPool, *, max_attempts: int = 2,
                 verify: Optional[Verifier] = None,
                 runs_root: Optional[str | Path] = None):
        self.pool = agent_pool
        self.max_attempts = max(1, max_attempts)
        self.verify: Verifier = verify or default_verify
        self.runs_root = Path(runs_root) if runs_root else None
        self.results: list[PipelineResult] = []
        self.run_id: str = ""
        self.attempts: list[dict] = []

    # ------------------------------------------------------------------ 노드
    async def _code(self, prompt: str, attempt: int) -> PipelineResult:
        try:
            content = await self.pool.call("coder", prompt)
            return PipelineResult(PipelineStep.CODE, self.pool.get("coder").name,
                                  True, content, attempt=attempt)
        except Exception as e:
            return PipelineResult(PipelineStep.CODE, "Coder Agent", False, "",
                                  str(e), attempt=attempt)

    async def _one(self, agent_id: str, step: PipelineStep, payload: str,
                   attempt: int) -> PipelineResult:
        try:
            content = await self.pool.call(agent_id, payload)
            return PipelineResult(step, self.pool.get(agent_id).name, True, content,
                                  attempt=attempt)
        except Exception as e:
            return PipelineResult(step, f"{agent_id.capitalize()} Agent", False, "",
                                  str(e), attempt=attempt)

    # ------------------------------------------------------------------ 실행
    async def run(self, user_request: str) -> list[PipelineResult]:
        """그래프를 끝까지 돈다. 반환값은 모든 시도의 단계 결과(시간순)."""
        self.results = []
        self.attempts = []
        self.run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
        prompt = user_request

        for attempt in range(1, self.max_attempts + 1):
            print(f"\n{'=' * 50}\n[시도 {attempt}/{self.max_attempts}] coder\n{'=' * 50}")
            code_res = await self._code(prompt, attempt)
            self.results.append(code_res)
            if not code_res.success:
                print(f"[FAIL] 코드 생성 실패: {code_res.error}")
                self._record(attempt, code_res.content, Verdict(False, f"coder 오류: {code_res.error}"))
                break
            print(f"[OK] 코드 생성 ({len(code_res.content)} chars)")

            # ---- ① 팬아웃: tester ∥ reviewer (둘 다 생성 코드만 받는 독립 노드)
            print(f"{'=' * 50}\n[시도 {attempt}] tester ∥ reviewer (병렬)\n{'=' * 50}")
            test_res, review_res = await asyncio.gather(
                self._one("tester", PipelineStep.TEST, code_res.content, attempt),
                self._one("reviewer", PipelineStep.REVIEW, code_res.content, attempt),
            )
            self.results.extend([test_res, review_res])
            for r, label in ((test_res, "테스트"), (review_res, "리뷰")):
                print(f"[{'OK' if r.success else 'FAIL'}] {label}" +
                      (f": {r.error}" if not r.success else ""))

            # ---- ② 판정 (LLM 아님)
            verdict = self.verify(code_res.content, test_res.content if test_res.success else "")
            self.results.append(PipelineResult(
                PipelineStep.VERDICT, "verify()", verdict.passed,
                json.dumps({"passed": verdict.passed, "reason": verdict.reason,
                            "checks": verdict.checks}, ensure_ascii=False),
                None if verdict.passed else verdict.reason, attempt))
            print(f"[판정] {'PASS' if verdict.passed else 'FAIL'}"
                  f"{'' if verdict.passed else ' — ' + verdict.reason}")

            self._record(attempt, code_res.content, verdict,
                         test_res.content if test_res.success else "",
                         review_res.content if review_res.success else "")

            if verdict.passed:
                break

            # ---- ③ 되돌아가기: 실패 이유 + 리뷰를 붙여 coder 를 다시 부른다
            if attempt < self.max_attempts:
                print(f"[되돌아가기] coder 재실행 (시도 {attempt + 1})")
                prompt = (
                    f"{user_request}\n\n"
                    f"# 이전 시도가 반려되었다 (시도 {attempt})\n"
                    f"## 반려 사유\n{verdict.reason}\n\n"
                    f"## 이전 코드\n```python\n{extract_code(code_res.content)}\n```\n\n"
                    f"## 리뷰 의견\n{(review_res.content or '(없음)')[:1500]}\n\n"
                    f"위 사유를 반드시 고쳐서 코드를 다시 작성하라."
                )

        self._save()
        return self.results

    # ------------------------------------------------------------------ ④ 상태
    def _record(self, attempt: int, code: str, verdict: Verdict,
                test: str = "", review: str = "") -> None:
        self.attempts.append({
            "attempt": attempt, "passed": verdict.passed, "reason": verdict.reason,
            "checks": verdict.checks, "code_chars": len(code or ""),
            "test_chars": len(test or ""), "review_chars": len(review or ""),
        })

    def _save(self) -> None:
        """시도 기록을 runs/<run_id>/ 에 남긴다. runs_root 를 안 주면 건너뛴다."""
        if self.runs_root is None:
            return
        run_dir = self.runs_root / self.run_id
        (run_dir / "raw").mkdir(parents=True, exist_ok=True)
        for r in self.results:
            name = f"attempt-{r.attempt:02d}__{r.step.value}.txt"
            (run_dir / "raw" / name).write_text(r.content or (r.error or ""), encoding="utf-8")
        final = self.attempts[-1] if self.attempts else {}
        (run_dir / "result.json").write_text(json.dumps({
            "run_id": self.run_id, "kind": "code_pipeline",
            "topology": "coder -> (tester || reviewer) -> verdict -> back-edge",
            "created": datetime.now().isoformat(timespec="seconds"),
            "max_attempts": self.max_attempts,
            "attempts_used": len(self.attempts),
            "verdict": "PASS" if final.get("passed") else "FAIL",
            "reason": final.get("reason", ""),
            "attempts": self.attempts,
        }, ensure_ascii=False, indent=2), encoding="utf-8")

    # ------------------------------------------------------------------ 보고
    def format_report(self) -> str:
        lines = ["\n" + "=" * 60,
                 "            멀티에이전트 그래프 결과 보고서",
                 "=" * 60,
                 f"run: {self.run_id} · 시도 {len(self.attempts)}/{self.max_attempts}"]
        for result in self.results:
            status = "[PASS]" if result.success else "[FAIL]"
            lines.append(f"\n## (시도 {result.attempt}) {result.step.value.upper()} - "
                         f"{result.agent_name} {status}")
            lines.append("-" * 40)
            if result.success:
                content = result.content
                lines.append(content if len(content) <= 1000 else content[:1000] + "\n... (truncated)")
            else:
                lines.append(f"Error: {result.error}")
        final = self.attempts[-1] if self.attempts else {}
        lines += ["\n" + "=" * 60,
                  f"최종 판정: {'PASS' if final.get('passed') else 'FAIL'}"
                  f"{'' if final.get('passed') else ' — ' + final.get('reason', '')}",
                  "=" * 60]
        return "\n".join(lines)
