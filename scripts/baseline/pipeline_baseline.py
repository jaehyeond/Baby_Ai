"""A2A CodePipeline 기준선 측정 — 그래프화(팬아웃·판정·되돌아가기) 전후 비교용.

측정 대상은 `hosts/orchestrator/pipeline.py`의 CodePipeline 그대로다. **소스를 고치지 않는다.**
단계별 시간은 `AgentPool.call`을 타이밍 래퍼로 감싸서 뺀다(비침습).

판정은 전부 결정론적 코드로 한다. LLM에게 "잘 됐냐"고 묻지 않는다:
  code_extracted -> syntax_ok -> contract_ok -> tests_pass (준비한 assert를 별도 프로세스로 실행)

⚠ 생성된 코드를 실행한다. 임시 폴더 + 별도 프로세스 + 타임아웃으로 제한하지만
   임의 코드 실행임에는 변함이 없다. 과제는 순수 함수만 요구하도록 골랐다.

사용법 (에이전트 3개를 먼저 띄운 뒤):
    python scripts/baseline/pipeline_baseline.py --tag before_graph
    python scripts/baseline/pipeline_baseline.py --tag before_graph --pilot   # 1과제 1회만
"""
from __future__ import annotations

import argparse
import ast
import asyncio
import json
import platform
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from hosts.orchestrator.agent_client import AgentPool  # noqa: E402
from hosts.orchestrator.pipeline import CodePipeline, PipelineStep  # noqa: E402

OUT_ROOT = PROJECT_ROOT / "claudedocs" / "baseline"

# --------------------------------------------------------------------------- 과제 세트
# 조건: 순수 함수 · 정답이 하나 · 엉성한 구현이 걸리는 경계값 포함.
TASKS = [
    {
        "id": "reverse_words",
        "func": "reverse_words",
        "prompt": (
            "파이썬 함수 reverse_words(s: str) -> str 를 작성해줘. "
            "문자열의 단어 순서를 뒤집어 하나의 공백으로 이어 반환한다. "
            "앞뒤 공백과 중복 공백은 제거한다. 빈 문자열은 빈 문자열을 반환한다."
        ),
        "asserts": [
            'assert reverse_words("hello world foo") == "foo world hello"',
            'assert reverse_words("  a   b  ") == "b a"',
            'assert reverse_words("") == ""',
            'assert reverse_words("one") == "one"',
        ],
    },
    {
        "id": "merge_intervals",
        "func": "merge_intervals",
        "prompt": (
            "파이썬 함수 merge_intervals(intervals: list[list[int]]) -> list[list[int]] 를 작성해줘. "
            "겹치거나 맞닿은 구간을 병합해 시작점 오름차순 리스트로 반환한다. "
            "빈 입력은 빈 리스트를 반환한다."
        ),
        "asserts": [
            "assert merge_intervals([[1,3],[2,6],[8,10]]) == [[1,6],[8,10]]",
            "assert merge_intervals([]) == []",
            "assert merge_intervals([[1,4],[4,5]]) == [[1,5]]",
            "assert merge_intervals([[5,6],[1,2]]) == [[1,2],[5,6]]",
        ],
    },
    {
        "id": "is_balanced",
        "func": "is_balanced",
        "prompt": (
            "파이썬 함수 is_balanced(s: str) -> bool 을 작성해줘. "
            "괄호 (), [], {} 가 올바르게 짝지어지고 중첩됐으면 True. "
            "괄호 외 문자는 무시한다. 빈 문자열은 True."
        ),
        "asserts": [
            'assert is_balanced("({[]})") is True',
            'assert is_balanced("(]") is False',
            'assert is_balanced("") is True',
            'assert is_balanced("a(b)c[d]") is True',
            'assert is_balanced("(") is False',
        ],
    },
    {
        "id": "top_k_frequent",
        "func": "top_k_frequent",
        "prompt": (
            "파이썬 함수 top_k_frequent(nums: list[int], k: int) -> list[int] 를 작성해줘. "
            "빈도가 높은 순으로 k개를 반환한다. 빈도가 같으면 값이 작은 것이 먼저 온다."
        ),
        "asserts": [
            "assert top_k_frequent([1,1,1,2,2,3], 2) == [1,2]",
            "assert top_k_frequent([1], 1) == [1]",
            "assert top_k_frequent([3,3,2,2,1], 2) == [2,3]",
        ],
    },
    {
        "id": "roman_to_int",
        "func": "roman_to_int",
        "prompt": (
            "파이썬 함수 roman_to_int(s: str) -> int 를 작성해줘. "
            "로마 숫자 문자열을 정수로 바꾼다. IV, IX, XL, XC, CD, CM 뺄셈 표기를 지원한다."
        ),
        "asserts": [
            'assert roman_to_int("III") == 3',
            'assert roman_to_int("IV") == 4',
            'assert roman_to_int("MCMXCIV") == 1994',
            'assert roman_to_int("LVIII") == 58',
        ],
    },
]

CODE_BLOCK = re.compile(r"```(?:python|py)?\s*\n(.*?)```", re.S)


# --------------------------------------------------------------------------- 결정론적 판정
def extract_code(text: str) -> str | None:
    """응답에서 파이썬 코드를 뽑는다. 코드블록이 여럿이면 가장 긴 것."""
    blocks = CODE_BLOCK.findall(text or "")
    if blocks:
        return max(blocks, key=len).strip()
    # 코드블록이 없으면 본문 전체가 코드인지 본다
    try:
        ast.parse(text or "")
        return (text or "").strip() or None
    except SyntaxError:
        return None


def syntax_ok(code: str) -> bool:
    try:
        ast.parse(code)
        return True
    except SyntaxError:
        return False


def defines(code: str, func: str) -> bool:
    """요구한 이름이 def 또는 대입으로 최상위에 정의됐는가."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return False
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == func:
            return True
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == func:
                    return True
    return False


def run_asserts(code: str, asserts: list[str], timeout: float = 10.0) -> dict:
    """생성 코드 + assert 를 별도 프로세스로 실행. 임시 폴더, 타임아웃."""
    script = code + "\n\n# ---- checks ----\n" + "\n".join(asserts) + '\nprint("ALL_OK")\n'
    with tempfile.TemporaryDirectory(prefix="a2a_baseline_") as td:
        path = Path(td) / "candidate.py"
        path.write_text(script, encoding="utf-8")
        try:
            p = subprocess.run([sys.executable, str(path)], cwd=td, capture_output=True,
                               text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return {"passed": False, "reason": "timeout", "stderr": ""}
    ok = p.returncode == 0 and "ALL_OK" in (p.stdout or "")
    if ok:
        reason = ""
    else:
        tail = [ln for ln in (p.stderr or "").strip().splitlines() if ln.strip()]
        reason = tail[-1] if tail else f"exit_{p.returncode}"
    return {"passed": ok, "reason": reason, "stderr": (p.stderr or "")[-800:]}


def score(task: dict, coder_text: str) -> dict:
    """coder 응답 하나를 4단계로 판정한다. 앞 단계가 실패하면 뒤는 False."""
    code = extract_code(coder_text)
    out = {"code_extracted": code is not None, "syntax_ok": False,
           "contract_ok": False, "tests_pass": False, "fail_reason": "", "code_chars": 0}
    if code is None:
        out["fail_reason"] = "no_code_block"
        return out
    out["code_chars"] = len(code)
    out["syntax_ok"] = syntax_ok(code)
    if not out["syntax_ok"]:
        out["fail_reason"] = "syntax_error"
        return out
    out["contract_ok"] = defines(code, task["func"])
    if not out["contract_ok"]:
        out["fail_reason"] = f"missing_def:{task['func']}"
        return out
    r = run_asserts(code, task["asserts"])
    out["tests_pass"] = r["passed"]
    if not r["passed"]:
        out["fail_reason"] = f"assert_failed:{r['reason'][:120]}"
        out["stderr_tail"] = r["stderr"]
    return out


# --------------------------------------------------------------------------- 실행
def instrument(pool: AgentPool, sink: dict) -> None:
    """pool.call 을 타이밍 래퍼로 감싼다 (파이프라인 소스는 안 고침)."""
    original = pool.call

    async def timed(agent_id: str, content: str):
        t0 = time.perf_counter()
        try:
            return await original(agent_id, content)
        finally:
            sink.setdefault(agent_id, []).append(time.perf_counter() - t0)

    pool.call = timed  # type: ignore[method-assign]


async def one_run(pool: AgentPool, task: dict) -> dict:
    """파이프라인 1회. 반환: 원문 + 시간 + 판정."""
    timings: dict[str, list[float]] = {}
    instrument(pool, timings)
    pipeline = CodePipeline(pool)

    t0 = time.perf_counter()
    results = await pipeline.run(task["prompt"])
    wall = time.perf_counter() - t0

    # 되돌아가기가 있으면 같은 단계가 여러 번 나온다 — 마지막 것이 최종 산출물이다.
    by_step = {r.step.value: r for r in results}
    coder_text = by_step.get(PipelineStep.CODE.value).content if PipelineStep.CODE.value in by_step else ""
    verdict = score(task, coder_text)

    attempts = max((r.attempt for r in results), default=1)
    last = [r for r in results if r.attempt == attempts]
    # steps_ok = "마지막 시도에서 예외가 없었나". 중간 시도의 실패는 되돌아가기가 흡수한 것이므로
    # 세지 않는다 (직선 구조에서는 시도가 1회뿐이라 예전 정의와 같은 값이 나온다).
    steps_ok = all(r.success for r in last)
    v = by_step.get(PipelineStep.VERDICT.value) if hasattr(PipelineStep, "VERDICT") else None

    return {
        "task_id": task["id"],
        "wall_s": wall,
        "step_wall_s": {k: sum(v) for k, v in timings.items()},
        "steps_ok": steps_ok,
        "attempts_used": attempts,
        "pipeline_verdict": (None if v is None else bool(v.success)),  # 파이프라인 자신의 판정
        "steps_done": len(results),
        "step_errors": {r.step.value: r.error for r in last if not r.success},
        **verdict,
        "raw": {f"{r.step.value}#{r.attempt}": r.content for r in results},
    }


async def main_async(args) -> int:
    tasks = TASKS[:1] if args.pilot else TASKS
    reps = 1 if args.pilot else args.reps
    stamp = datetime.now().strftime("%Y%m%d-%H%M")
    out_dir = OUT_ROOT / f"pipeline_{args.tag}_{stamp}"
    (out_dir / "raw").mkdir(parents=True, exist_ok=True)

    rows: list[dict] = []
    async with AgentPool() as pool:
        for name, url in (("coder", args.coder), ("tester", args.tester), ("reviewer", args.reviewer)):
            card = await pool.register(name, url)
            print(f"  연결됨 {name:9s} {card.name}  ({url})")
        print()

        for task in tasks:
            for rep in range(reps):
                label = f"{task['id']}#{rep + 1}"
                print(f"[{label}] 실행…", flush=True)
                try:
                    row = await one_run(pool, task)
                except Exception as e:                      # 파이프라인 자체가 죽은 경우
                    row = {"task_id": task["id"], "wall_s": None, "steps_ok": False,
                           "code_extracted": False, "syntax_ok": False, "contract_ok": False,
                           "tests_pass": False, "fail_reason": f"pipeline_crash:{e}", "raw": {}}
                row["rep"] = rep + 1
                raw = row.pop("raw", {})
                (out_dir / "raw" / f"{task['id']}_{rep + 1}.json").write_text(
                    json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
                rows.append(row)
                print(f"[{label}] steps_ok={row['steps_ok']} tests_pass={row['tests_pass']} "
                      f"({row.get('fail_reason') or 'ok'}) {row.get('wall_s') or 0:.1f}s", flush=True)

    with open(out_dir / "results.jsonl", "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    n = len(rows)
    def rate(k: str) -> float:
        return sum(1 for r in rows if r.get(k)) / n if n else 0.0
    walls = [r["wall_s"] for r in rows if r.get("wall_s")]
    step_totals: dict[str, float] = {}
    for r in rows:
        for k, v in (r.get("step_wall_s") or {}).items():
            step_totals[k] = step_totals.get(k, 0.0) + v

    result = {
        "run_id": out_dir.name, "gate": "A2A-baseline", "kind": "pipeline_baseline",
        "tag": args.tag, "created": datetime.now().isoformat(timespec="seconds"),
        "host": platform.node(), "pilot": bool(args.pilot),
        "topology": "linear: coder -> tester -> reviewer (no fan-out, no verdict, no back-edge)",
        "n_tasks": len(tasks), "reps": reps, "n_runs": n,
        "rates": {k: rate(k) for k in
                  ("steps_ok", "code_extracted", "syntax_ok", "contract_ok", "tests_pass")},
        "wall_s": {"mean": (sum(walls) / len(walls)) if walls else None,
                   "min": min(walls) if walls else None, "max": max(walls) if walls else None,
                   "total": sum(walls) if walls else None},
        "step_wall_s_total": step_totals,
        "fail_reasons": sorted({r.get("fail_reason") for r in rows if r.get("fail_reason")}),
        "per_task": {t["id"]: {
            "tests_pass": sum(1 for r in rows if r["task_id"] == t["id"] and r.get("tests_pass")),
            "n": sum(1 for r in rows if r["task_id"] == t["id"]),
        } for t in tasks},
    }
    (out_dir / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [f"# A2A CodePipeline 기준선 — {args.tag}", "",
             f"- run: `{out_dir.name}`  ·  구조: {result['topology']}",
             f"- 과제 {len(tasks)} × 반복 {reps} = {n}회", "",
             "| 지표 | 비율 |", "|---|---|"]
    for k, v in result["rates"].items():
        lines.append(f"| `{k}` | {v * 100:.0f} % |")
    lines += ["", f"- 1회 평균 {result['wall_s']['mean'] or 0:.1f} s "
                  f"(최소 {result['wall_s']['min'] or 0:.1f} / 최대 {result['wall_s']['max'] or 0:.1f})",
              f"- 에이전트별 누적: " + ", ".join(f"{k} {v:.0f}s" for k, v in sorted(step_totals.items())),
              "", "## 과제별 tests_pass", "", "| 과제 | 통과/시도 |", "|---|---|"]
    for tid, d in result["per_task"].items():
        lines.append(f"| {tid} | {d['tests_pass']}/{d['n']} |")
    if result["fail_reasons"]:
        lines += ["", "## 실패 이유", ""] + [f"- `{x}`" for x in result["fail_reasons"]]
    (out_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"\n결과: {out_dir}")
    print(f"  steps_ok {result['rates']['steps_ok'] * 100:.0f} %  vs  "
          f"tests_pass {result['rates']['tests_pass'] * 100:.0f} %   <- 이 차이가 '판정 없음'의 크기")
    return 0


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="A2A CodePipeline 기준선 측정")
    p.add_argument("--tag", required=True, help="before_graph / after_graph 등")
    p.add_argument("--reps", type=int, default=3, help="과제당 반복 (기본 3)")
    p.add_argument("--pilot", action="store_true", help="1과제 1회만 (배관 확인용)")
    p.add_argument("--coder", default="http://localhost:9999")
    p.add_argument("--tester", default="http://localhost:9998")
    p.add_argument("--reviewer", default="http://localhost:9996")
    return p.parse_args(argv)


if __name__ == "__main__":
    sys.exit(asyncio.run(main_async(parse_args())))
