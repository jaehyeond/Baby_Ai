"""
NeuralSubstrate: 뇌의 물리적 기반

모든 에이전트(뉴런)가 하나의 기질에서 동작
- HTTP 서버 없이 직접 실행
- 단일 프로세스에서 모든 처리
- 메모리 공유 가능

이것이 진짜 "뇌"처럼 작동하는 핵심:
- 뉴런들이 별도 서버가 아닌 하나의 시스템에 존재
- 시냅스(연결)는 직접 함수 호출
- 학습 결과는 메모리/파일로 영속화
"""

import asyncio
from dataclasses import dataclass, field
from typing import Optional, Any
from enum import Enum

# 에이전트 임포트 (HTTP 서버 없이 직접 사용)
from agents.coder.agent import CoderAgent
from agents.tester.agent import TesterAgent
from agents.reviewer.agent import ReviewerAgent

from .layer import LayerType, LayerStatus, AgentNode
from .visualizer import NeuralVisualizer, create_visualizer


class AgentRole(Enum):
    """에이전트 역할"""
    CODER = "coder"
    TESTER = "tester"
    REVIEWER = "reviewer"
    # 향후 확장
    ROUTER = "router"
    PLANNER = "planner"
    MONITOR = "monitor"


@dataclass
class AgentResult:
    """에이전트 실행 결과"""
    agent_id: str
    success: bool
    output: str
    error: Optional[str] = None
    execution_time_ms: float = 0.0


@dataclass
class SubstrateConfig:
    """Substrate 설정"""
    max_iterations: int = 3
    verbose: bool = True
    # 향후 확장: 학습된 가중치 파일 경로 등


class NeuralSubstrate:
    """
    Neural Substrate: 뇌의 물리적 기반

    모든 에이전트가 하나의 프로세스에서 실행됨
    - 터미널 여러 개 필요 없음
    - HTTP 통신 오버헤드 없음
    - 진짜 뇌처럼 통합된 시스템

    사용법:
        substrate = NeuralSubstrate()
        result = await substrate.process("피보나치 함수를 작성해줘")
    """

    def __init__(self, config: Optional[SubstrateConfig] = None):
        self.config = config or SubstrateConfig()
        self._viz = create_visualizer() if self.config.verbose else None

        # 에이전트 인스턴스 (메모리에 로드)
        self._agents: dict[str, Any] = {}
        self._initialized = False

        # 학습된 가중치 (Phase 8에서 활용)
        self._weights: dict[str, float] = {
            "coder": 1.0,
            "tester": 1.0,
            "reviewer": 1.0,
        }

    def _initialize_agents(self) -> None:
        """에이전트 초기화 (lazy loading)"""
        if self._initialized:
            return

        if self._viz:
            self._viz.print_subheader("INITIALIZING NEURAL SUBSTRATE")

        try:
            self._agents["coder"] = CoderAgent()
            if self._viz:
                print("  [OK] Coder neuron loaded")

            self._agents["tester"] = TesterAgent()
            if self._viz:
                print("  [OK] Tester neuron loaded")

            self._agents["reviewer"] = ReviewerAgent()
            if self._viz:
                print("  [OK] Reviewer neuron loaded")

            self._initialized = True

            if self._viz:
                print(f"\n  Substrate ready: {len(self._agents)} neurons active")

        except Exception as e:
            raise RuntimeError(f"Failed to initialize substrate: {e}")

    async def _call_agent(self, agent_id: str, input_data: str) -> AgentResult:
        """
        에이전트 직접 호출 (HTTP 없이)

        Args:
            agent_id: 에이전트 식별자
            input_data: 입력 데이터

        Returns:
            AgentResult
        """
        import time
        start_time = time.time()

        agent = self._agents.get(agent_id)
        if not agent:
            return AgentResult(
                agent_id=agent_id,
                success=False,
                output="",
                error=f"Agent '{agent_id}' not found"
            )

        try:
            # 에이전트별 메서드 호출
            if agent_id == "coder":
                output = await agent.generate(input_data)
            elif agent_id == "tester":
                output = await agent.analyze_and_test(input_data)
            elif agent_id == "reviewer":
                output = await agent.review(input_data)
            else:
                output = ""

            execution_time = (time.time() - start_time) * 1000

            return AgentResult(
                agent_id=agent_id,
                success=True,
                output=output,
                execution_time_ms=execution_time
            )

        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return AgentResult(
                agent_id=agent_id,
                success=False,
                output="",
                error=str(e),
                execution_time_ms=execution_time
            )

    async def process(self, user_request: str) -> dict[str, Any]:
        """
        요청 처리 (Forward Pass)

        단일 명령으로 전체 파이프라인 실행:
        1. Coder: 코드 생성
        2. Tester: 코드 테스트
        3. Reviewer: 코드 리뷰
        4. 피드백 루프 (실패 시 재시도)

        Args:
            user_request: 사용자 요청

        Returns:
            처리 결과 딕셔너리
        """
        # 에이전트 초기화
        self._initialize_agents()

        if self._viz:
            self._viz.print_header("NEURAL SUBSTRATE - Forward Pass")
            print(f"\n[INPUT] {user_request[:80]}{'...' if len(user_request) > 80 else ''}")

        results: dict[str, AgentResult] = {}
        iteration = 1
        success = False
        feedback_context = ""

        while iteration <= self.config.max_iterations and not success:
            if self._viz:
                strategy = "BASIC" if iteration == 1 else ("CONTEXTUAL" if iteration == 2 else "STRATEGIC")
                self._viz.print_iteration_start(iteration, self.config.max_iterations, strategy)

            # === Layer 2: Processing (Coder) ===
            if self._viz:
                print(f"\n[LAYER 2] Processing - Coder")
                print(f"  Generating code...", end="", flush=True)

            coder_input = user_request
            if feedback_context:
                coder_input = f"{user_request}\n\n[Previous Feedback]\n{feedback_context}"

            coder_result = await self._call_agent("coder", coder_input)
            results["coder"] = coder_result

            if self._viz:
                status = "[OK]" if coder_result.success else "[X]"
                print(f"\r  {status} Completed in {coder_result.execution_time_ms:.0f}ms")
                if coder_result.success:
                    preview = coder_result.output[:100].replace('\n', ' ')
                    print(f"      Output: {preview}...")

            if not coder_result.success:
                if self._viz:
                    print(f"  [ERROR] {coder_result.error}")
                break

            generated_code = coder_result.output

            # === Layer 3: Evaluation (Tester + Reviewer) ===
            if self._viz:
                print(f"\n[LAYER 3] Evaluation - Tester & Reviewer")

            # Tester
            if self._viz:
                print(f"  Testing code...", end="", flush=True)

            tester_result = await self._call_agent("tester", generated_code)
            results["tester"] = tester_result

            if self._viz:
                status = "[OK]" if tester_result.success else "[X]"
                print(f"\r  {status} Tester completed in {tester_result.execution_time_ms:.0f}ms")

            # Reviewer
            if self._viz:
                print(f"  Reviewing code...", end="", flush=True)

            reviewer_result = await self._call_agent("reviewer", generated_code)
            results["reviewer"] = reviewer_result

            if self._viz:
                status = "[OK]" if reviewer_result.success else "[X]"
                print(f"\r  {status} Reviewer completed in {reviewer_result.execution_time_ms:.0f}ms")

            # === 평가 ===
            eval_success, feedback = self._evaluate_results(tester_result, reviewer_result)

            if self._viz:
                print(f"\n  [EVALUATION] {'PASS' if eval_success else 'NEEDS IMPROVEMENT'}")

            if eval_success:
                success = True
            else:
                feedback_context = feedback
                if self._viz and iteration < self.config.max_iterations:
                    print(f"  [FEEDBACK] {feedback[:150]}...")
                    print(f"\n  Retrying with feedback...")
                iteration += 1

        # === 최종 결과 ===
        total_time = sum(r.execution_time_ms for r in results.values())

        if self._viz:
            self._print_final_report(success, iteration, results, total_time)

        return {
            "success": success,
            "iterations": iteration,
            "code": results.get("coder", AgentResult("coder", False, "")).output,
            "test_result": results.get("tester", AgentResult("tester", False, "")).output,
            "review_result": results.get("reviewer", AgentResult("reviewer", False, "")).output,
            "total_time_ms": total_time,
        }

    def _evaluate_results(
        self,
        tester_result: AgentResult,
        reviewer_result: AgentResult
    ) -> tuple[bool, str]:
        """테스트/리뷰 결과 평가"""
        # 둘 다 성공해야 함
        if not tester_result.success or not reviewer_result.success:
            errors = []
            if not tester_result.success:
                errors.append(f"Tester: {tester_result.error}")
            if not reviewer_result.success:
                errors.append(f"Reviewer: {reviewer_result.error}")
            return False, "\n".join(errors)

        # 테스트 결과 분석
        test_output = tester_result.output.lower()
        review_output = reviewer_result.output.lower()

        # 실패 키워드
        failure_keywords = ["error", "fail", "bug", "issue", "problem", "오류", "실패", "버그"]
        success_keywords = ["pass", "success", "correct", "good", "성공", "통과", "정상"]

        has_failure = any(kw in test_output for kw in failure_keywords)
        has_success = any(kw in test_output for kw in success_keywords)

        # 리뷰 점수 추출 시도 (예: "8/10", "점수: 7")
        import re
        score_match = re.search(r'(\d+)\s*/\s*10', review_output)
        review_score = int(score_match.group(1)) if score_match else 7

        if has_failure and not has_success:
            feedback = f"Test issues found. Review score: {review_score}/10\n"
            feedback += tester_result.output[:300]
            return False, feedback

        if review_score < 6:
            feedback = f"Review score too low: {review_score}/10\n"
            feedback += reviewer_result.output[:300]
            return False, feedback

        return True, ""

    def _print_final_report(
        self,
        success: bool,
        iterations: int,
        results: dict[str, AgentResult],
        total_time: float
    ) -> None:
        """최종 보고서 출력"""
        if not self._viz:
            return

        self._viz.print_header("EXECUTION COMPLETE")

        status = "[SUCCESS]" if success else "[FAILED]"
        print(f"\n{status} Completed in {iterations} iteration(s)")
        print(f"Total time: {total_time:.0f}ms ({total_time/1000:.1f}s)")

        self._viz.print_subheader("AGENT RESULTS")
        for agent_id, result in results.items():
            status = "[OK]" if result.success else "[X]"
            print(f"  {status} {agent_id}: {result.execution_time_ms:.0f}ms")

        if success and "coder" in results:
            self._viz.print_subheader("GENERATED CODE")
            print(results["coder"].output)

        print("\n" + "=" * 70)
        if success:
            print("Pipeline completed successfully!")
        else:
            print(f"Pipeline failed after {iterations} iterations.")


async def run_substrate(user_request: str, max_iterations: int = 3) -> dict:
    """
    Substrate 실행 헬퍼 함수

    사용법:
        result = await run_substrate("피보나치 함수를 작성해줘")
    """
    substrate = NeuralSubstrate(SubstrateConfig(
        max_iterations=max_iterations,
        verbose=True,
    ))
    return await substrate.process(user_request)
