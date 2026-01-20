"""
Baby Neural Substrate 단위 테스트

실행: python -m neural.baby.test_baby
"""

from neural.baby import (
    EmotionalCore,
    EmotionalState,
    Emotion,
    EmotionType,
    CuriosityEngine,
    CuriositySignal,
    LearningZone,
    MemorySystem,
    Experience,
    DevelopmentStage,
    DevelopmentTracker,
    SelfModel,
    Capability,
    Preference,
    BabyConfig,
)


def test_emotional_core():
    """감정 핵심 테스트"""
    print("\n[Test] EmotionalCore")

    core = EmotionalCore()

    # 초기 상태
    state = core.get_state()
    assert state.curiosity > 0.7  # 아기는 호기심 높게 시작
    assert state.fear < 0.3       # 두려움은 낮게

    # 성공 시 감정 변화
    core.on_success(0.3)
    new_state = core.get_state()
    assert new_state.joy > state.joy

    # 실패 시 감정 변화
    core.on_failure(0.3)
    after_fail = core.get_state()
    assert after_fail.frustration > 0

    # 행동 조절
    core._emotions[EmotionType.FEAR].intensity = 0.8
    action = core.modulate_action("generate")
    assert action == "cautious_generate"

    print("  [OK] EmotionalCore working correctly")


def test_curiosity_engine():
    """호기심 엔진 테스트"""
    print("\n[Test] CuriosityEngine")

    engine = CuriosityEngine()

    # 간단한 호기심 계산
    signal = engine.compute_simple_curiosity(
        success=True,
        output="def fibonacci(n): pass",
        task_type="function",
    )

    assert isinstance(signal, CuriositySignal)
    assert 0 <= signal.intrinsic_reward <= 1
    assert signal.zone in LearningZone

    # 새로운 상태는 새로움 높음
    assert signal.novelty > 0

    # 같은 상태 다시 → 새로움 낮음
    signal2 = engine.compute_simple_curiosity(
        success=True,
        output="def fibonacci(n): pass",
        task_type="function",
    )
    assert signal2.novelty < signal.novelty

    print("  [OK] CuriosityEngine working correctly")


def test_memory_system():
    """기억 시스템 테스트"""
    print("\n[Test] MemorySystem")

    memory = MemorySystem()

    # 경험 기록
    exp = memory.record_experience(
        request="피보나치 함수 작성",
        action="def fib(n): return n if n < 2 else fib(n-1) + fib(n-2)",
        outcome="성공",
        success=True,
        emotional_weight=0.8,
        task_type="function",
    )

    assert exp.id is not None
    assert exp.success is True

    # 유사 경험 회상
    similar = memory.episodic.recall_similar("피보나치")
    assert len(similar) > 0

    # 성공 경험 회상
    successful = memory.episodic.recall_successful("function")
    assert len(successful) > 0

    # 통계
    stats = memory.get_stats()
    assert stats["episodic"]["total"] > 0

    print("  [OK] MemorySystem working correctly")


def test_development_tracker():
    """발달 추적 테스트"""
    print("\n[Test] DevelopmentTracker")

    tracker = DevelopmentTracker()

    # 초기 단계
    assert tracker.stage == DevelopmentStage.NEWBORN

    # 경험 누적
    for i in range(5):
        tracker.record_experience(success=True, task_type="test")

    # 능력 확인
    assert tracker.has_capability("basic_response")
    assert tracker.has_capability("pattern_detection")

    # 진행 상황
    progress = tracker.get_progress()
    assert progress["experience_count"] == 5
    assert progress["success_rate"] == 1.0

    # 학습률 조정
    modifier = tracker.get_learning_rate_modifier()
    assert modifier > 1.0  # 어린 단계는 빠른 학습

    print("  [OK] DevelopmentTracker working correctly")


def test_self_model():
    """자아 모델 테스트"""
    print("\n[Test] SelfModel")

    self_model = SelfModel()

    # 능력 등록
    self_model.register_capability("coding", "코드 작성")
    self_model.register_capability("testing", "테스트 작성")

    # 능력 업데이트
    self_model.update_capability("coding", success=True)
    self_model.update_capability("coding", success=True)
    self_model.update_capability("testing", success=False)

    # 자신있게 할 수 있는지
    coding_cap = self_model.get_capability("coding")
    testing_cap = self_model.get_capability("testing")
    assert coding_cap.confidence > testing_cap.confidence

    # 선호 업데이트
    self_model.update_preference("python", "language", positive_outcome=True)
    self_model.update_preference("python", "language", positive_outcome=True)
    assert self_model.likes("python")

    # 한계 추가
    self_model.add_limitation("complex_math")
    assert self_model.has_limitation("complex_math")

    # 자기 설명
    desc = self_model.generate_self_description()
    assert "나는" in desc

    print("  [OK] SelfModel working correctly")


def test_baby_config():
    """Baby 설정 테스트"""
    print("\n[Test] BabyConfig")

    config = BabyConfig(
        max_iterations=5,
        verbose=False,
        enable_emotions=True,
    )

    assert config.max_iterations == 5
    assert config.verbose is False
    assert config.enable_emotions is True

    print("  [OK] BabyConfig working correctly")


def test_integration():
    """통합 테스트 (에이전트 없이)"""
    print("\n[Test] Integration (without agents)")

    # 모든 컴포넌트 생성
    emotions = EmotionalCore()
    curiosity = CuriosityEngine()
    memory = MemorySystem()
    development = DevelopmentTracker()
    self_model = SelfModel()

    # 시뮬레이션: 성공적인 경험
    # 1. 요청 처리 시작
    request = "피보나치 함수 작성"

    # 2. 감정 상태 확인
    emotional_state = emotions.get_state()
    exploration_rate = emotions.get_exploration_rate()

    # 3. 결과 (시뮬레이션)
    success = True
    output = "def fib(n): return n if n < 2 else fib(n-1) + fib(n-2)"

    # 4. 호기심 신호
    curiosity_signal = curiosity.compute_simple_curiosity(
        success=success,
        output=output,
        task_type="function",
    )

    # 5. 감정 업데이트
    if success:
        emotions.on_success()
    else:
        emotions.on_failure()

    emotions.on_novelty(curiosity_signal.novelty)

    # 6. 기억 저장
    experience = memory.record_experience(
        request=request,
        action=output,
        outcome="success",
        success=success,
        emotional_weight=emotions.get_memory_weight(),
        curiosity_signal=curiosity_signal.intrinsic_reward,
        task_type="function",
    )

    # 7. 발달 업데이트
    dev_result = development.record_experience(success=success, task_type="function")

    # 8. 자아 업데이트
    self_model.register_capability("function_writing", "함수 작성")
    self_model.update_capability("function_writing", success)

    # 검증
    assert experience.success is True
    assert development._experience_count == 1
    assert emotions.get_state().joy > emotional_state.joy

    print("  [OK] Integration test passed")


def run_all_tests():
    """모든 테스트 실행"""
    print("=" * 60)
    print("       BABY NEURAL SUBSTRATE UNIT TESTS")
    print("=" * 60)

    tests = [
        test_emotional_core,
        test_curiosity_engine,
        test_memory_system,
        test_development_tracker,
        test_self_model,
        test_baby_config,
        test_integration,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"  [FAIL] {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"  [ERROR] {test.__name__}: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
