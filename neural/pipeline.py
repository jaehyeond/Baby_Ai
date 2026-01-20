"""
NeuralPipeline: Agentic Neural Network의 Forward Pass 구현

Forward Pass: Request → Layer 0 → Layer 1 → ... → Layer 4 → Output
Backward Pass: Feedback → Textual Backpropagation → 프롬프트/가중치 업데이트 (Phase 8)

핵심 개념 (arXiv:2506.09046):
- Forward Pass: 순차적/병렬 레이어 실행
- Feedback Loop: 실패 시 재시도 (최대 3회)
- Neuromodulation: 반복별 전략 변화

참고: docs/NEURAL_A2A_ARCHITECTURE.md
"""

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Any, Callable, TYPE_CHECKING

from .layer import (
    NeuralLayer,
    LayerConfig,
    LayerType,
    LayerStatus,
    LayerOutput,
    AgentNode,
    create_default_layers,
)

if TYPE_CHECKING:
    from .visualizer import NeuralVisualizer


class PipelineStatus(Enum):
    """파이프라인 상태"""
    # 초기 상태
    PENDING = "pending"

    # 실행 단계
    RUNNING = "running"
    LAYER_EXECUTING = "layer_executing"

    # 피드백 단계
    FEEDBACK_RECEIVED = "feedback_received"
    RETRYING = "retrying"

    # 종료 상태
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


class FeedbackStrategy(Enum):
    """피드백 전략 (Neuromodulation 기반)"""
    BASIC = "basic"           # 직접적 오류 수정
    CONTEXTUAL = "contextual" # 더 많은 컨텍스트 추가
    STRATEGIC = "strategic"   # 완전히 다른 접근법


@dataclass
class ForwardResult:
    """Forward Pass 결과"""
    status: PipelineStatus
    final_output: str = ""
    layer_outputs: list[LayerOutput] = field(default_factory=list)
    iterations: int = 1
    feedback_history: list[str] = field(default_factory=list)
    total_time_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def is_success(self) -> bool:
        return self.status == PipelineStatus.COMPLETED

    def add_layer_output(self, output: LayerOutput) -> None:
        """레이어 출력 추가"""
        self.layer_outputs.append(output)


@dataclass
class PipelineConfig:
    """파이프라인 설정"""
    max_iterations: int = 3       # 최대 피드백 루프 횟수
    timeout_seconds: float = 300  # 전체 타임아웃 (5분)
    enable_feedback_loop: bool = True  # 피드백 루프 활성화
    verbose: bool = True          # 상세 로깅


class Neuromodulator:
    """
    신경조절 시스템 - 동적 전략 조정

    뇌 과학적 근거:
    - 도파민: 보상/동기, 학습 신호
    - 노르에피네프린: 각성, 탐색/활용 균형
    """

    def __init__(self):
        self.dopamine_level = 0.5      # 보상 신호
        self.norepinephrine_level = 0.5  # 탐색 vs 활용

    def update_on_success(self) -> None:
        """성공 시 도파민 증가 → 현재 전략 강화"""
        self.dopamine_level = min(1.0, self.dopamine_level + 0.2)
        self.norepinephrine_level = max(0.0, self.norepinephrine_level - 0.1)

    def update_on_failure(self) -> None:
        """실패 시 노르에피네프린 증가 → 탐색 모드"""
        self.dopamine_level = max(0.0, self.dopamine_level - 0.1)
        self.norepinephrine_level = min(1.0, self.norepinephrine_level + 0.2)

    def get_strategy(self, iteration: int) -> FeedbackStrategy:
        """반복 횟수와 조절물질 수준에 따른 전략"""
        if iteration == 1:
            return FeedbackStrategy.BASIC
        elif iteration == 2:
            return FeedbackStrategy.CONTEXTUAL
        else:
            return FeedbackStrategy.STRATEGIC

    def reset(self) -> None:
        """상태 초기화"""
        self.dopamine_level = 0.5
        self.norepinephrine_level = 0.5


class NeuralPipeline:
    """
    Neural Pipeline: Forward Pass + Feedback Loop

    ANN 기반 멀티에이전트 파이프라인:
    - 레이어별 순차 실행 (Forward Pass)
    - 실패 시 피드백 루프 (최대 3회)
    - Neuromodulation 기반 전략 조정

    현재 구현 (Phase 7):
    - Layer 2 (Processing): Coder
    - Layer 3 (Evaluation): Tester, Reviewer
    - 피드백 루프: Evaluation 실패 시 → Processing 재시도
    """

    def __init__(self, config: Optional[PipelineConfig] = None):
        self.config = config or PipelineConfig()
        self.layers: dict[int, NeuralLayer] = {}
        self.status = PipelineStatus.PENDING
        self.neuromodulator = Neuromodulator()

        # 결과 저장
        self._current_result: Optional[ForwardResult] = None

        # 평가 함수 (커스터마이징 가능)
        self._evaluator: Optional[Callable[[str], tuple[bool, str]]] = None

        # Visualizer (lazy import)
        self._visualizer: Optional["NeuralVisualizer"] = None

    def _get_visualizer(self) -> "NeuralVisualizer":
        """Visualizer 인스턴스 가져오기 (lazy loading)"""
        if self._visualizer is None:
            from .visualizer import create_visualizer
            self._visualizer = create_visualizer(use_colors=True)
        return self._visualizer

    def add_layer(self, layer: NeuralLayer) -> None:
        """레이어 추가"""
        self.layers[layer.layer_index] = layer

    def get_layer(self, index: int) -> Optional[NeuralLayer]:
        """레이어 조회"""
        return self.layers.get(index)

    def set_evaluator(self, evaluator: Callable[[str], tuple[bool, str]]) -> None:
        """
        평가 함수 설정

        Args:
            evaluator: (output) -> (success: bool, feedback: str)
        """
        self._evaluator = evaluator

    async def forward(
        self,
        input_data: str,
        agent_pool: Any,  # AgentPool
    ) -> ForwardResult:
        """
        Forward Pass 실행

        Args:
            input_data: 초기 입력 (사용자 요청)
            agent_pool: A2A AgentPool 인스턴스

        Returns:
            ForwardResult: 실행 결과
        """
        start_time = asyncio.get_event_loop().time()
        self.status = PipelineStatus.RUNNING
        self.neuromodulator.reset()

        # Visualizer 가져오기
        viz = self._get_visualizer() if self.config.verbose else None

        result = ForwardResult(
            status=PipelineStatus.RUNNING,
            metadata={"input": input_data}
        )
        self._current_result = result

        iteration = 1
        current_input = input_data
        context: dict[str, Any] = {}
        last_processing_output = ""

        # 시작 시각화
        if viz:
            viz.print_forward_pass_start(input_data, self.config.max_iterations)
            viz.print_network_diagram(self.layers)

        while iteration <= self.config.max_iterations:
            strategy = self.neuromodulator.get_strategy(iteration)

            if viz:
                viz.print_iteration_start(iteration, self.config.max_iterations, strategy.value)

            # 피드백 컨텍스트 설정
            if iteration > 1:
                context["iteration"] = iteration
                context["strategy"] = strategy.value

            # Forward Pass through layers
            layer_success = True

            for layer_idx in sorted(self.layers.keys()):
                layer = self.layers[layer_idx]
                layer_start_time = time.time()

                if viz:
                    viz.print_layer_start(layer)

                # 레이어 실행
                layer_output = await layer.forward(
                    current_input,
                    agent_pool,
                    context=context if iteration > 1 else None
                )

                layer_time_ms = (time.time() - layer_start_time) * 1000
                result.add_layer_output(layer_output)

                if viz:
                    viz.print_layer_complete(layer, layer_output.is_success, layer_time_ms)

                    # 에이전트 출력 표시
                    for agent_id, output in layer_output.outputs.items():
                        viz.print_agent_output(agent_id, output, max_lines=3)

                    if layer_output.errors:
                        for aid, err in layer_output.errors.items():
                            print(f"    [ERROR] {aid}: {err}")

                # Processing Layer 출력 저장
                if layer.layer_type == LayerType.PROCESSING:
                    last_processing_output = layer.get_weighted_output()
                    current_input = last_processing_output

                # Evaluation Layer 결과 확인
                if layer.layer_type == LayerType.EVALUATION:
                    eval_output = layer.get_weighted_output()

                    # 커스텀 평가 함수 사용
                    if self._evaluator:
                        success, feedback = self._evaluator(eval_output)
                    else:
                        # 기본 평가: 출력에 "PASS" 또는 긍정적 키워드 포함 여부
                        success, feedback = self._default_evaluate(eval_output)

                    if not success:
                        layer_success = False
                        context["feedback"] = feedback
                        result.feedback_history.append(feedback)

                        if viz:
                            viz.print_feedback(feedback, iteration)

                # 레이어 실패 시 중단
                if layer_output.status == LayerStatus.FAILED:
                    layer_success = False
                    break

            # 흐름도 출력
            if viz:
                status_str = "SUCCESS" if layer_success else "NEEDS RETRY"
                viz.print_flow_diagram(self.layers, iteration, status_str)

            # 성공 시 종료
            if layer_success:
                self.neuromodulator.update_on_success()
                result.status = PipelineStatus.COMPLETED
                result.final_output = last_processing_output
                break

            # 실패 시 재시도 준비
            self.neuromodulator.update_on_failure()
            result.iterations = iteration

            if iteration < self.config.max_iterations:
                if viz:
                    print(f"\n[RETRY] Moving to iteration {iteration + 1}...")

                # 입력 리셋 (원본 + 피드백)
                current_input = input_data

                # 레이어 초기화
                for layer in self.layers.values():
                    layer.reset()

            iteration += 1

        # 최종 상태 결정
        if result.status != PipelineStatus.COMPLETED:
            result.status = PipelineStatus.FAILED
            result.final_output = last_processing_output  # 마지막 시도 결과

        # 시간 계산
        end_time = asyncio.get_event_loop().time()
        result.total_time_ms = (end_time - start_time) * 1000
        result.iterations = iteration if iteration <= self.config.max_iterations else self.config.max_iterations

        self.status = result.status

        # 최종 보고서 출력
        if viz:
            viz.print_final_report(
                success=result.is_success,
                iterations=result.iterations,
                max_iterations=self.config.max_iterations,
                total_time_ms=result.total_time_ms,
                final_output=result.final_output,
                layer_outputs=result.layer_outputs,
                feedback_history=result.feedback_history,
                layers=self.layers,
            )

        return result

    def _default_evaluate(self, evaluation_output: str) -> tuple[bool, str]:
        """
        기본 평가 로직

        Returns:
            (success: bool, feedback: str)
        """
        output_lower = evaluation_output.lower()

        # 성공 키워드
        success_keywords = [
            "pass", "passed", "success", "correct", "works",
            "approved", "good", "excellent", "완료", "성공", "통과"
        ]

        # 실패 키워드
        failure_keywords = [
            "fail", "failed", "error", "bug", "issue", "problem",
            "incorrect", "wrong", "실패", "오류", "에러", "버그"
        ]

        # 키워드 기반 판단
        has_success = any(kw in output_lower for kw in success_keywords)
        has_failure = any(kw in output_lower for kw in failure_keywords)

        if has_failure and not has_success:
            # 피드백 추출 시도
            feedback = self._extract_feedback(evaluation_output)
            return False, feedback

        return True, ""

    def _extract_feedback(self, evaluation_output: str) -> str:
        """평가 출력에서 피드백 추출"""
        # 간단한 추출: 전체 출력을 피드백으로 사용
        # Phase 8에서 LLM 기반 피드백 추출로 개선 예정
        lines = evaluation_output.strip().split("\n")

        # 첫 500자 또는 처음 10줄
        if len(evaluation_output) > 500:
            return evaluation_output[:500] + "..."

        return "\n".join(lines[:10])

    def create_report(self) -> str:
        """실행 결과 보고서 생성"""
        if not self._current_result:
            return "No execution result available."

        result = self._current_result
        lines = []

        lines.append("\n" + "=" * 70)
        lines.append("           NEURAL A2A PIPELINE EXECUTION REPORT")
        lines.append("=" * 70)

        # 기본 정보
        status_icon = "✓" if result.is_success else "✗"
        lines.append(f"\n{status_icon} Status: {result.status.value}")
        lines.append(f"  Iterations: {result.iterations}/{self.config.max_iterations}")
        lines.append(f"  Total Time: {result.total_time_ms:.2f}ms")

        # 레이어별 결과
        lines.append(f"\n{'-'*40}")
        lines.append("LAYER EXECUTION SUMMARY")
        lines.append(f"{'-'*40}")

        for layer_output in result.layer_outputs:
            layer = self.layers.get(layer_output.layer_index)
            layer_name = layer.name if layer else f"Layer {layer_output.layer_index}"
            status = "✓" if layer_output.is_success else "✗"

            lines.append(f"\n[{layer_output.layer_index}] {layer_name} {status}")

            for agent_id, output in layer_output.outputs.items():
                preview = output[:100].replace("\n", " ")
                lines.append(f"    {agent_id}: {preview}...")

            for agent_id, error in layer_output.errors.items():
                lines.append(f"    {agent_id} ERROR: {error}")

        # 피드백 이력
        if result.feedback_history:
            lines.append(f"\n{'-'*40}")
            lines.append("FEEDBACK HISTORY")
            lines.append(f"{'-'*40}")

            for i, feedback in enumerate(result.feedback_history, 1):
                lines.append(f"\n[Iteration {i+1}] {feedback[:200]}...")

        # 최종 출력
        if result.final_output:
            lines.append(f"\n{'-'*40}")
            lines.append("FINAL OUTPUT")
            lines.append(f"{'-'*40}")

            output_preview = result.final_output
            if len(output_preview) > 1000:
                output_preview = output_preview[:1000] + "\n... (truncated)"
            lines.append(output_preview)

        lines.append("\n" + "=" * 70)

        return "\n".join(lines)

    def reset(self) -> None:
        """파이프라인 초기화"""
        self.status = PipelineStatus.PENDING
        self.neuromodulator.reset()
        self._current_result = None

        for layer in self.layers.values():
            layer.reset()


def create_code_pipeline() -> NeuralPipeline:
    """
    코드 생성 파이프라인 팩토리

    현재 구현 (Phase 7):
    - Layer 2: Coder (Processing)
    - Layer 3: Tester, Reviewer (Evaluation)

    Returns:
        설정된 NeuralPipeline 인스턴스
    """
    pipeline = NeuralPipeline(PipelineConfig(
        max_iterations=3,
        verbose=True,
    ))

    # Layer 2: Processing (코드 생성)
    processing_layer = NeuralLayer(LayerConfig(
        layer_index=2,
        layer_type=LayerType.PROCESSING,
        name="Processing Layer",
        description="코드 생성 및 실행 (소뇌)",
        max_retries=1,
    ))
    processing_layer.add_node(AgentNode(
        agent_id="coder",
        agent_url="http://localhost:9999",
        role="코드 생성",
        llm_model="claude-sonnet",
        port=9999,
    ))
    pipeline.add_layer(processing_layer)

    # Layer 3: Evaluation (테스트 + 리뷰)
    evaluation_layer = NeuralLayer(LayerConfig(
        layer_index=3,
        layer_type=LayerType.EVALUATION,
        name="Evaluation Layer",
        description="테스트 및 리뷰 (안와전두피질)",
        parallel_execution=True,
    ))
    evaluation_layer.add_node(AgentNode(
        agent_id="tester",
        agent_url="http://localhost:9998",
        role="코드 테스트",
        llm_model="claude-sonnet",
        port=9998,
    ))
    evaluation_layer.add_node(AgentNode(
        agent_id="reviewer",
        agent_url="http://localhost:9997",
        role="코드 리뷰",
        llm_model="claude-sonnet",
        port=9997,
    ))
    pipeline.add_layer(evaluation_layer)

    return pipeline
