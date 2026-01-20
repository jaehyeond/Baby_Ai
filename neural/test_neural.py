"""
Neural A2A 단위 테스트

실행: python -m neural.test_neural
"""

import asyncio
from neural import (
    NeuralLayer,
    LayerConfig,
    LayerType,
    LayerStatus,
    AgentNode,
    NeuralPipeline,
    PipelineConfig,
    Neuromodulator,
    FeedbackStrategy,
    create_code_pipeline,
    # Substrate
    NeuralSubstrate,
    SubstrateConfig,
    AgentResult,
    AgentRole,
)


def test_layer_creation():
    """레이어 생성 테스트"""
    print("\n[Test] Layer Creation")

    config = LayerConfig(
        layer_index=2,
        layer_type=LayerType.PROCESSING,
        name="Processing Layer",
        description="코드 생성",
    )
    layer = NeuralLayer(config)

    assert layer.layer_index == 2
    assert layer.layer_type == LayerType.PROCESSING
    assert layer.name == "Processing Layer"
    assert layer.status == LayerStatus.IDLE
    assert layer.node_count == 0

    print("  [OK] Layer created successfully")


def test_agent_node():
    """에이전트 노드 테스트"""
    print("\n[Test] Agent Node")

    node = AgentNode(
        agent_id="coder",
        agent_url="http://localhost:9999",
        role="코드 생성",
        port=9999,
    )

    assert node.agent_id == "coder"
    assert node.weight == 1.0
    assert node.success_rate == 0.0

    # 실행 기록
    node.record_execution(True)
    node.record_execution(True)
    node.record_execution(False)

    assert node.execution_count == 3
    assert node.success_count == 2
    assert abs(node.success_rate - 0.666) < 0.01

    print("  [OK] Agent node working correctly")


def test_layer_with_nodes():
    """노드가 있는 레이어 테스트"""
    print("\n[Test] Layer with Nodes")

    layer = NeuralLayer(LayerConfig(
        layer_index=3,
        layer_type=LayerType.EVALUATION,
        name="Evaluation Layer",
    ))

    layer.add_node(AgentNode(
        agent_id="tester",
        agent_url="http://localhost:9998",
        role="테스트",
        port=9998,
    ))

    layer.add_node(AgentNode(
        agent_id="reviewer",
        agent_url="http://localhost:9997",
        role="리뷰",
        port=9997,
    ))

    assert layer.node_count == 2
    assert len(layer.active_nodes) == 2
    assert layer.get_node("tester") is not None
    assert layer.get_node("unknown") is None

    # 노드 제거
    removed = layer.remove_node("tester")
    assert removed is not None
    assert layer.node_count == 1

    print("  [OK] Layer with nodes working correctly")


def test_neuromodulator():
    """신경조절 시스템 테스트"""
    print("\n[Test] Neuromodulator")

    nm = Neuromodulator()

    # 초기 상태
    assert nm.dopamine_level == 0.5
    assert nm.norepinephrine_level == 0.5

    # Iteration 1: BASIC
    assert nm.get_strategy(1) == FeedbackStrategy.BASIC

    # 실패 후
    nm.update_on_failure()
    assert nm.dopamine_level < 0.5
    assert nm.norepinephrine_level > 0.5

    # Iteration 2: CONTEXTUAL
    assert nm.get_strategy(2) == FeedbackStrategy.CONTEXTUAL

    # Iteration 3: STRATEGIC
    assert nm.get_strategy(3) == FeedbackStrategy.STRATEGIC

    # 리셋
    nm.reset()
    assert nm.dopamine_level == 0.5

    print("  [OK] Neuromodulator working correctly")


def test_pipeline_creation():
    """파이프라인 생성 테스트"""
    print("\n[Test] Pipeline Creation")

    pipeline = create_code_pipeline()

    assert len(pipeline.layers) == 2
    assert 2 in pipeline.layers  # Processing layer
    assert 3 in pipeline.layers  # Evaluation layer

    processing = pipeline.get_layer(2)
    assert processing is not None
    assert processing.node_count == 1  # coder

    evaluation = pipeline.get_layer(3)
    assert evaluation is not None
    assert evaluation.node_count == 2  # tester, reviewer

    print("  [OK] Pipeline created successfully")


def test_pipeline_config():
    """파이프라인 설정 테스트"""
    print("\n[Test] Pipeline Config")

    config = PipelineConfig(
        max_iterations=5,
        timeout_seconds=600,
        verbose=False,
    )

    pipeline = NeuralPipeline(config)
    assert pipeline.config.max_iterations == 5
    assert pipeline.config.timeout_seconds == 600
    assert pipeline.config.verbose is False

    print("  [OK] Pipeline config working correctly")


def test_layer_types():
    """레이어 타입 열거형 테스트"""
    print("\n[Test] Layer Types")

    assert LayerType.INPUT.value == "input"
    assert LayerType.EXECUTIVE.value == "executive"
    assert LayerType.PROCESSING.value == "processing"
    assert LayerType.EVALUATION.value == "evaluation"
    assert LayerType.OUTPUT.value == "output"

    print("  [OK] Layer types defined correctly")


def test_substrate_creation():
    """NeuralSubstrate 생성 테스트"""
    print("\n[Test] NeuralSubstrate Creation")

    config = SubstrateConfig(
        max_iterations=5,
        verbose=False,
    )
    substrate = NeuralSubstrate(config)

    assert substrate.config.max_iterations == 5
    assert substrate.config.verbose is False
    assert substrate._initialized is False  # Lazy loading
    assert len(substrate._agents) == 0
    assert substrate._weights["coder"] == 1.0

    print("  [OK] NeuralSubstrate created successfully")


def test_agent_role():
    """AgentRole 열거형 테스트"""
    print("\n[Test] AgentRole Enum")

    assert AgentRole.CODER.value == "coder"
    assert AgentRole.TESTER.value == "tester"
    assert AgentRole.REVIEWER.value == "reviewer"
    assert AgentRole.ROUTER.value == "router"
    assert AgentRole.PLANNER.value == "planner"

    print("  [OK] AgentRole enum defined correctly")


def test_agent_result():
    """AgentResult 테스트"""
    print("\n[Test] AgentResult")

    result = AgentResult(
        agent_id="coder",
        success=True,
        output="def hello(): pass",
        execution_time_ms=150.5,
    )

    assert result.agent_id == "coder"
    assert result.success is True
    assert result.output == "def hello(): pass"
    assert result.error is None
    assert result.execution_time_ms == 150.5

    # 실패 결과
    fail_result = AgentResult(
        agent_id="tester",
        success=False,
        output="",
        error="Test failed",
    )

    assert fail_result.success is False
    assert fail_result.error == "Test failed"

    print("  [OK] AgentResult working correctly")


def run_all_tests():
    """모든 테스트 실행"""
    print("=" * 60)
    print("       NEURAL A2A UNIT TESTS")
    print("=" * 60)

    tests = [
        test_layer_creation,
        test_agent_node,
        test_layer_with_nodes,
        test_neuromodulator,
        test_pipeline_creation,
        test_pipeline_config,
        test_layer_types,
        # Substrate tests
        test_substrate_creation,
        test_agent_role,
        test_agent_result,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"  [FAIL] FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"  [FAIL] ERROR: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
