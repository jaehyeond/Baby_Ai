#!/usr/bin/env python
"""
World Model 테스트 스크립트

World Model 기능 테스트:
1. 예측 (Prediction) 생성
2. 시뮬레이션 (Simulation) 실행
3. 상상 (Imagination) 세션
4. DB 저장 확인
"""

import os
import sys

# 프로젝트 루트 추가
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from dotenv import load_dotenv
load_dotenv()

from neural.baby.db import get_brain_db
from neural.baby.llm_client import get_llm_client
from neural.baby.world_model import (
    WorldModel,
    PredictionType,
    SimulationType,
    ImaginationType,
)


def test_prediction():
    """예측 테스트"""
    print("\n" + "=" * 60)
    print("1. PREDICTION TEST")
    print("=" * 60)

    db = get_brain_db()
    llm = get_llm_client()

    wm = WorldModel(
        db=db,
        llm_client=llm,
        development_stage=3,  # TODDLER
        verbose=True,
    )

    # 예측 가능 여부 확인
    print(f"\nCan predict: {wm.can_predict()}")

    # 예측 생성
    result = wm.make_prediction(
        scenario="피보나치 함수를 작성하는 작업을 수행할 때",
        prediction_type=PredictionType.OUTCOME,
    )

    if result:
        print(f"\n[SUCCESS] Prediction created:")
        print(f"  ID: {result.prediction_id}")
        print(f"  Prediction: {result.prediction[:100]}...")
        print(f"  Confidence: {result.confidence:.2f}")
        print(f"  Reasoning: {result.reasoning[:100]}...")
    else:
        print("[FAILED] Could not create prediction")


def test_simulation():
    """시뮬레이션 테스트"""
    print("\n" + "=" * 60)
    print("2. SIMULATION TEST")
    print("=" * 60)

    db = get_brain_db()
    llm = get_llm_client()

    wm = WorldModel(
        db=db,
        llm_client=llm,
        development_stage=3,  # TODDLER
        verbose=True,
    )

    # 시뮬레이션 가능 여부 확인
    print(f"\nCan simulate: {wm.can_simulate()}")

    # 시뮬레이션 실행
    result = wm.run_simulation(
        initial_state={"code": "incomplete", "tests": "failing"},
        goal="모든 테스트 통과",
        simulation_type=SimulationType.PLANNING,
        max_steps=3,
    )

    if result:
        print(f"\n[SUCCESS] Simulation completed:")
        print(f"  ID: {result.simulation_id}")
        print(f"  Steps: {len(result.steps)}")
        print(f"  Success Probability: {result.success_probability:.2f}")
        for i, step in enumerate(result.steps, 1):
            print(f"  Step {i}: {step.get('action', 'N/A')[:50]}...")
    else:
        print("[FAILED] Could not run simulation")


def test_imagination():
    """상상 테스트"""
    print("\n" + "=" * 60)
    print("3. IMAGINATION TEST")
    print("=" * 60)

    db = get_brain_db()
    llm = get_llm_client()

    wm = WorldModel(
        db=db,
        llm_client=llm,
        development_stage=3,  # TODDLER
        verbose=True,
    )

    # 상상 가능 여부 확인
    print(f"\nCan imagine: {wm.can_imagine()}")

    # 상상 세션 시작
    session_id = wm.start_imagination(
        topic="코드 작성의 새로운 방법",
        trigger="curiosity_test",
        imagination_type=ImaginationType.EXPLORATION,
        curiosity_level=0.8,
    )

    if session_id:
        print(f"\n[SUCCESS] Imagination session started: {session_id}")

        # 생각 몇 개 생성
        for i in range(3):
            thought = wm.imagine_thought(thought_type="exploration")
            if thought:
                print(f"  Thought {i+1}: {thought.get('content', 'N/A')[:50]}...")

        # 세션 종료
        result = wm.end_imagination()
        if result:
            print(f"\n[SUCCESS] Imagination session ended:")
            print(f"  Topic: {result.topic}")
            print(f"  Thoughts: {len(result.thoughts)}")
            print(f"  Insights: {result.insights[:3] if result.insights else 'None'}")
    else:
        print("[FAILED] Could not start imagination session")


def test_causal_discovery():
    """인과관계 발견 테스트"""
    print("\n" + "=" * 60)
    print("4. CAUSAL DISCOVERY TEST")
    print("=" * 60)

    db = get_brain_db()
    llm = get_llm_client()

    wm = WorldModel(
        db=db,
        llm_client=llm,
        development_stage=4,  # CHILD - 인과 추론 가능
        verbose=True,
    )

    # 인과 추론 가능 여부 확인
    print(f"\nCan reason causally: {wm.can_reason_causally()}")

    # 직접 인과관계 발견
    result = wm.discover_causal_relation(
        cause_concept="질문",
        effect_concept="호기심",
        evidence="테스트: 질문을 하면 호기심이 생김",
    )

    if result:
        print(f"\n[SUCCESS] Causal relation discovered:")
        print(f"  ID: {result.get('id', 'N/A')}")
        print(f"  Type: {result.get('relationship_type', 'N/A')}")
        print(f"  Strength: {result.get('causal_strength', 0):.2f}")
    else:
        print("[INFO] Could not discover causal relation (concepts may not exist)")

    # 경험에서 인과관계 추출
    relations = wm.extract_causal_relations_from_experience(
        experience={
            "task": "새로운 개념을 배우는 대화",
            "success": True,
            "task_type": "learning",
        },
        emotional_state={
            "curiosity": 0.8,
            "joy": 0.7,
            "fear": 0.1,
            "frustration": 0.1,
        },
    )

    print(f"\n[RESULTS] Causal relations from experience: {len(relations)}")
    for rel in relations[:5]:
        print(f"  - {rel.get('relationship_type', 'N/A')}: strength={rel.get('causal_strength', 0):.2f}")


def test_prediction_verification():
    """예측 자동 검증 테스트"""
    print("\n" + "=" * 60)
    print("5. PREDICTION AUTO-VERIFICATION TEST")
    print("=" * 60)

    db = get_brain_db()
    llm = get_llm_client()

    wm = WorldModel(
        db=db,
        llm_client=llm,
        development_stage=4,  # CHILD
        verbose=True,
    )

    # 현재 미검증 예측 수 확인
    unverified_before = db.get_unverified_predictions(limit=50)
    print(f"\n[BEFORE] 미검증 예측: {len(unverified_before)}개")

    # 자동 검증 실행
    verified = wm.auto_verify_predictions(
        current_experience={
            "task": "algorithm 유형의 작업 완료",
            "success": True,
            "task_type": "algorithm",
        }
    )

    print(f"\n[RESULTS] 이번에 검증된 예측: {len(verified)}개")
    for v in verified:
        result = "[O] 정확" if v.get("was_correct") else "[X] 부정확"
        print(f"  - {result}: {v.get('scenario', 'N/A')}")

    # 검증 후 미검증 예측 수 확인
    unverified_after = db.get_unverified_predictions(limit=50)
    print(f"\n[AFTER] 미검증 예측: {len(unverified_after)}개")


def test_auto_generation():
    """자동 생성 테스트 (예측 검증 포함)"""
    print("\n" + "=" * 60)
    print("6. AUTO-GENERATION TEST (with Auto-Verification)")
    print("=" * 60)

    db = get_brain_db()
    llm = get_llm_client()

    wm = WorldModel(
        db=db,
        llm_client=llm,
        development_stage=4,  # CHILD - 인과 추론 포함
        verbose=True,
    )

    # 경험에서 자동 생성 (검증도 포함)
    results = wm.auto_generate_from_experience(
        experience={
            "task": "정렬 알고리즘 구현",
            "success": True,
            "task_type": "algorithm",
        },
        emotional_state={
            "curiosity": 0.8,
            "joy": 0.6,
            "fear": 0.1,
            "frustration": 0.1,
        },
    )

    print(f"\n[RESULTS]")
    print(f"  Verified Predictions: {len(results.get('verified_predictions', []))}")
    print(f"  New Prediction: {'Yes' if results.get('prediction') else 'No'}")
    print(f"  Simulation: {'Yes' if results.get('simulation') else 'No'}")
    print(f"  Imagination: {'Yes' if results.get('imagination') else 'No'}")
    print(f"  Causal Relations: {len(results.get('causal_relations', []))}")


def test_db_stats():
    """DB 통계 확인"""
    print("\n" + "=" * 60)
    print("7. DATABASE STATS")
    print("=" * 60)

    db = get_brain_db()

    # 최근 예측 조회
    predictions = db.get_recent_predictions(limit=5)
    print(f"\nRecent Predictions: {len(predictions)}")
    for p in predictions[:3]:
        print(f"  - {p.get('scenario', 'N/A')[:40]}... (conf: {p.get('confidence', 0):.2f})")

    # 최근 시뮬레이션 조회
    simulations = db.get_recent_simulations(limit=5)
    print(f"\nRecent Simulations: {len(simulations)}")
    for s in simulations[:3]:
        print(f"  - {s.get('target_goal', 'N/A')[:40]}... (prob: {s.get('success_probability', 0):.2f})")

    # 최근 상상 세션 조회
    sessions = db.get_recent_imagination_sessions(limit=5)
    print(f"\nRecent Imagination Sessions: {len(sessions)}")
    for sess in sessions[:3]:
        print(f"  - {sess.get('topic', 'N/A')[:40]}...")

    # 인과 모델 조회
    causal_models = db.get_causal_models(min_confidence=0.0, limit=10)
    print(f"\nCausal Models: {len(causal_models)}")
    for cm in causal_models[:5]:
        print(f"  - {cm.get('relationship_type', 'N/A')}: strength={cm.get('causal_strength', 0):.2f}, conf={cm.get('confidence', 0):.2f}")


def main():
    print("\n" + "=" * 60)
    print("  WORLD MODEL TEST SUITE")
    print("=" * 60)

    # API 키 확인
    if not os.getenv("GOOGLE_API_KEY") and not os.getenv("OPENAI_API_KEY"):
        print("\n[ERROR] No API key found. Set GOOGLE_API_KEY or OPENAI_API_KEY")
        return

    if not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_ANON_KEY"):
        print("\n[ERROR] Supabase credentials not found")
        return

    try:
        test_prediction()
        test_simulation()
        test_imagination()
        test_causal_discovery()
        test_prediction_verification()
        test_auto_generation()
        test_db_stats()

        print("\n" + "=" * 60)
        print("  ALL TESTS COMPLETED")
        print("=" * 60 + "\n")

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
