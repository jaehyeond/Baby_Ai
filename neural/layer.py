"""
NeuralLayer: Agentic Neural Network의 레이어 추상화

뇌 영역 매핑:
- Layer 0 (Input): Router - 시상 (정보 라우팅)
- Layer 1 (Executive): Planner, Monitor - 전전두엽, ACC
- Layer 2 (Processing): Coder, Executor - 소뇌 (정밀 실행)
- Layer 3 (Evaluation): Tester, Reviewer - 안와전두피질 (가치 평가)
- Layer 4 (Output): Aggregator - 결과 통합

참고: arXiv:2506.09046 - Agentic Neural Networks
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Any
from datetime import datetime


class LayerType(Enum):
    """레이어 타입 (뇌 영역 매핑)"""
    INPUT = "input"           # Layer 0: 입력/라우팅 (시상)
    EXECUTIVE = "executive"   # Layer 1: 계획/감시 (전전두엽)
    PROCESSING = "processing" # Layer 2: 실행/코딩 (소뇌)
    EVALUATION = "evaluation" # Layer 3: 테스트/리뷰 (안와전두피질)
    OUTPUT = "output"         # Layer 4: 결과 통합


class LayerStatus(Enum):
    """레이어 실행 상태"""
    IDLE = "idle"              # 대기
    PROCESSING = "processing"  # 처리 중
    COMPLETED = "completed"    # 완료
    FAILED = "failed"          # 실패
    SKIPPED = "skipped"        # 건너뜀


@dataclass
class AgentNode:
    """
    에이전트 노드 (뉴런)

    레이어 내 개별 에이전트를 나타냄
    """
    agent_id: str           # 에이전트 식별자 (예: "coder", "tester")
    agent_url: str          # A2A 서버 URL
    role: str               # 역할 설명
    llm_model: str = "claude-sonnet"  # 사용 LLM
    port: int = 9999        # 포트 번호

    # 가중치 (Textual Backpropagation에서 업데이트)
    weight: float = 1.0     # 연결 가중치 (0.0 ~ 2.0)
    bias: float = 0.0       # 바이어스

    # 런타임 상태
    is_active: bool = True
    last_output: Optional[str] = None
    last_error: Optional[str] = None
    execution_count: int = 0
    success_count: int = 0

    @property
    def success_rate(self) -> float:
        """성공률"""
        if self.execution_count == 0:
            return 0.0
        return self.success_count / self.execution_count

    def record_execution(self, success: bool) -> None:
        """실행 기록"""
        self.execution_count += 1
        if success:
            self.success_count += 1


@dataclass
class LayerConfig:
    """레이어 설정"""
    layer_index: int              # 레이어 인덱스 (0~4)
    layer_type: LayerType         # 레이어 타입
    name: str                     # 레이어 이름
    description: str = ""         # 설명
    parallel_execution: bool = False  # 병렬 실행 여부
    max_retries: int = 1          # 최대 재시도 횟수
    timeout_seconds: float = 120.0  # 타임아웃


@dataclass
class LayerOutput:
    """레이어 출력"""
    layer_index: int
    status: LayerStatus
    outputs: dict[str, str] = field(default_factory=dict)  # agent_id -> output
    errors: dict[str, str] = field(default_factory=dict)   # agent_id -> error
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def is_success(self) -> bool:
        """모든 에이전트 성공 여부"""
        return self.status == LayerStatus.COMPLETED and not self.errors

    @property
    def combined_output(self) -> str:
        """모든 출력 결합"""
        return "\n\n".join(
            f"[{agent_id}]\n{output}"
            for agent_id, output in self.outputs.items()
        )


class NeuralLayer:
    """
    Neural Layer: 에이전트 레이어 추상화

    뇌의 뉴런 집단처럼, 같은 레이어의 에이전트들은
    유사한 역할을 수행하고 협력/경쟁함

    특징:
    - 레이어 내 병렬 실행 지원
    - 가중치 기반 출력 조합
    - 실패 시 재시도 메커니즘
    """

    def __init__(self, config: LayerConfig):
        self.config = config
        self.nodes: dict[str, AgentNode] = {}
        self.status = LayerStatus.IDLE
        self._last_output: Optional[LayerOutput] = None

    @property
    def layer_index(self) -> int:
        return self.config.layer_index

    @property
    def layer_type(self) -> LayerType:
        return self.config.layer_type

    @property
    def name(self) -> str:
        return self.config.name

    def add_node(self, node: AgentNode) -> None:
        """에이전트 노드 추가"""
        self.nodes[node.agent_id] = node

    def remove_node(self, agent_id: str) -> Optional[AgentNode]:
        """에이전트 노드 제거"""
        return self.nodes.pop(agent_id, None)

    def get_node(self, agent_id: str) -> Optional[AgentNode]:
        """에이전트 노드 조회"""
        return self.nodes.get(agent_id)

    @property
    def active_nodes(self) -> list[AgentNode]:
        """활성 노드 목록"""
        return [n for n in self.nodes.values() if n.is_active]

    @property
    def node_count(self) -> int:
        """노드 수"""
        return len(self.nodes)

    async def forward(
        self,
        input_data: str,
        agent_pool: Any,  # AgentPool
        context: Optional[dict] = None,
    ) -> LayerOutput:
        """
        Forward Pass: 레이어 실행

        Args:
            input_data: 이전 레이어 출력 또는 초기 입력
            agent_pool: A2A AgentPool 인스턴스
            context: 추가 컨텍스트 (피드백, 메타데이터 등)

        Returns:
            LayerOutput: 레이어 실행 결과
        """
        self.status = LayerStatus.PROCESSING
        outputs: dict[str, str] = {}
        errors: dict[str, str] = {}

        active = self.active_nodes
        if not active:
            self.status = LayerStatus.SKIPPED
            return LayerOutput(
                layer_index=self.layer_index,
                status=LayerStatus.SKIPPED,
                metadata={"reason": "No active nodes"}
            )

        # 컨텍스트가 있으면 입력에 추가
        enriched_input = self._enrich_input(input_data, context)

        # 병렬 실행 (TODO: asyncio.gather로 구현)
        # 현재는 순차 실행
        for node in active:
            try:
                # AgentPool에 등록 확인
                try:
                    agent_pool.get(node.agent_id)
                except KeyError:
                    # 등록되지 않은 에이전트는 건너뜀
                    errors[node.agent_id] = f"Agent not registered in pool"
                    node.record_execution(False)
                    continue

                # 에이전트 호출
                result = await agent_pool.call(node.agent_id, enriched_input)

                # 가중치 적용 (메타데이터로 저장)
                outputs[node.agent_id] = result
                node.last_output = result
                node.record_execution(True)

            except Exception as e:
                errors[node.agent_id] = str(e)
                node.last_error = str(e)
                node.record_execution(False)

        # 상태 결정
        if outputs and not errors:
            self.status = LayerStatus.COMPLETED
        elif outputs:
            self.status = LayerStatus.COMPLETED  # 일부 성공
        else:
            self.status = LayerStatus.FAILED

        self._last_output = LayerOutput(
            layer_index=self.layer_index,
            status=self.status,
            outputs=outputs,
            errors=errors,
            metadata={
                "layer_name": self.name,
                "layer_type": self.layer_type.value,
                "context": context,
            }
        )

        return self._last_output

    def _enrich_input(
        self,
        input_data: str,
        context: Optional[dict]
    ) -> str:
        """컨텍스트로 입력 강화"""
        if not context:
            return input_data

        parts = [input_data]

        # 피드백 추가
        if "feedback" in context:
            parts.append(f"\n\n[Previous Feedback]\n{context['feedback']}")

        # 오류 정보 추가
        if "errors" in context:
            parts.append(f"\n\n[Previous Errors]\n{context['errors']}")

        # 반복 횟수
        if "iteration" in context:
            iteration = context["iteration"]
            if iteration > 1:
                parts.append(f"\n\n[Iteration {iteration}] Please improve based on feedback.")

        return "\n".join(parts)

    def update_weights(self, gradients: dict[str, float]) -> None:
        """
        가중치 업데이트 (Textual Backpropagation)

        Args:
            gradients: agent_id -> gradient value
        """
        for agent_id, gradient in gradients.items():
            node = self.nodes.get(agent_id)
            if node:
                # 학습률 적용
                learning_rate = 0.1
                node.weight = max(0.1, min(2.0, node.weight + learning_rate * gradient))

    def get_weighted_output(self) -> str:
        """가중치 적용된 출력 (우선순위 기반)"""
        if not self._last_output or not self._last_output.outputs:
            return ""

        # 가중치 높은 순으로 정렬
        sorted_nodes = sorted(
            self.active_nodes,
            key=lambda n: n.weight,
            reverse=True
        )

        # 가장 높은 가중치 에이전트의 출력 반환
        for node in sorted_nodes:
            if node.agent_id in self._last_output.outputs:
                return self._last_output.outputs[node.agent_id]

        return self._last_output.combined_output

    def reset(self) -> None:
        """레이어 상태 초기화"""
        self.status = LayerStatus.IDLE
        self._last_output = None
        for node in self.nodes.values():
            node.last_output = None
            node.last_error = None

    def __repr__(self) -> str:
        return (
            f"NeuralLayer({self.layer_index}: {self.name}, "
            f"type={self.layer_type.value}, nodes={self.node_count})"
        )


# 기본 레이어 설정 팩토리
def create_default_layers() -> list[NeuralLayer]:
    """기본 5개 레이어 생성"""
    configs = [
        LayerConfig(
            layer_index=0,
            layer_type=LayerType.INPUT,
            name="Input Layer",
            description="태스크 분류 및 라우팅 (시상)",
        ),
        LayerConfig(
            layer_index=1,
            layer_type=LayerType.EXECUTIVE,
            name="Executive Layer",
            description="계획 수립 및 감시 (전전두엽, ACC)",
            parallel_execution=True,
        ),
        LayerConfig(
            layer_index=2,
            layer_type=LayerType.PROCESSING,
            name="Processing Layer",
            description="코드 생성 및 실행 (소뇌)",
            parallel_execution=True,
            max_retries=3,
        ),
        LayerConfig(
            layer_index=3,
            layer_type=LayerType.EVALUATION,
            name="Evaluation Layer",
            description="테스트 및 리뷰 (안와전두피질)",
            parallel_execution=True,
        ),
        LayerConfig(
            layer_index=4,
            layer_type=LayerType.OUTPUT,
            name="Output Layer",
            description="결과 통합 및 피드백 수집",
        ),
    ]

    return [NeuralLayer(config) for config in configs]
