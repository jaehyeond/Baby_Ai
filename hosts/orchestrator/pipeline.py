"""멀티에이전트 파이프라인 정의"""

from dataclasses import dataclass
from typing import Optional
from enum import Enum

from .agent_client import AgentPool


class PipelineStep(Enum):
    """파이프라인 단계"""
    CODE = "code"      # 코드 생성
    TEST = "test"      # 코드 테스트
    REVIEW = "review"  # 코드 리뷰


@dataclass
class PipelineResult:
    """파이프라인 실행 결과"""
    step: PipelineStep
    agent_name: str
    success: bool
    content: str
    error: Optional[str] = None


class CodePipeline:
    """코드 생성 → 테스트 → 리뷰 파이프라인"""

    def __init__(self, agent_pool: AgentPool):
        self.pool = agent_pool
        self.results: list[PipelineResult] = []

    async def run(self, user_request: str) -> list[PipelineResult]:
        """
        전체 파이프라인 실행

        Args:
            user_request: 사용자의 코드 생성 요청

        Returns:
            각 단계별 결과 리스트
        """
        self.results = []

        # Step 1: 코드 생성
        print(f"\n{'='*50}")
        print("[1/3] Coder Agent - 코드 생성 중...")
        print(f"{'='*50}")

        try:
            generated_code = await self.pool.call("coder", user_request)
            self.results.append(PipelineResult(
                step=PipelineStep.CODE,
                agent_name=self.pool.get("coder").name,
                success=True,
                content=generated_code,
            ))
            print(f"[OK] 코드 생성 완료 ({len(generated_code)} chars)")
        except Exception as e:
            self.results.append(PipelineResult(
                step=PipelineStep.CODE,
                agent_name="Coder Agent",
                success=False,
                content="",
                error=str(e),
            ))
            print(f"[FAIL] 코드 생성 실패: {e}")
            return self.results

        # Step 2: 코드 테스트
        print(f"\n{'='*50}")
        print("[2/3] Tester Agent - 코드 테스트 중...")
        print(f"{'='*50}")

        try:
            test_result = await self.pool.call("tester", generated_code)
            self.results.append(PipelineResult(
                step=PipelineStep.TEST,
                agent_name=self.pool.get("tester").name,
                success=True,
                content=test_result,
            ))
            print(f"[OK] 테스트 완료")
        except Exception as e:
            self.results.append(PipelineResult(
                step=PipelineStep.TEST,
                agent_name="Tester Agent",
                success=False,
                content="",
                error=str(e),
            ))
            print(f"[FAIL] 테스트 실패: {e}")

        # Step 3: 코드 리뷰
        print(f"\n{'='*50}")
        print("[3/3] Reviewer Agent - 코드 리뷰 중...")
        print(f"{'='*50}")

        try:
            review_result = await self.pool.call("reviewer", generated_code)
            self.results.append(PipelineResult(
                step=PipelineStep.REVIEW,
                agent_name=self.pool.get("reviewer").name,
                success=True,
                content=review_result,
            ))
            print(f"[OK] 리뷰 완료")
        except Exception as e:
            self.results.append(PipelineResult(
                step=PipelineStep.REVIEW,
                agent_name="Reviewer Agent",
                success=False,
                content="",
                error=str(e),
            ))
            print(f"[FAIL] 리뷰 실패: {e}")

        return self.results

    def format_report(self) -> str:
        """결과를 보고서 형식으로 포맷"""
        lines = []
        lines.append("\n" + "=" * 60)
        lines.append("            멀티에이전트 파이프라인 결과 보고서")
        lines.append("=" * 60)

        for result in self.results:
            status = "[PASS]" if result.success else "[FAIL]"
            lines.append(f"\n## {result.step.value.upper()} - {result.agent_name} {status}")
            lines.append("-" * 40)

            if result.success:
                # 내용이 길면 일부만 표시
                content = result.content
                if len(content) > 1000:
                    content = content[:1000] + "\n... (truncated)"
                lines.append(content)
            else:
                lines.append(f"Error: {result.error}")

        lines.append("\n" + "=" * 60)
        success_count = sum(1 for r in self.results if r.success)
        lines.append(f"완료: {success_count}/{len(self.results)} 단계 성공")
        lines.append("=" * 60)

        return "\n".join(lines)
