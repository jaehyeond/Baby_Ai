"""
Cognitive Router Test

인지적 모델 라우팅 시스템 테스트
"""

import sys
import os
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dotenv import load_dotenv
load_dotenv()


def main():
    print("\n" + "="*60)
    print("Cognitive Router Test")
    print("="*60)

    from neural.baby.cognitive_router import (
        CognitiveRouter,
        TaskContext,
        DevelopmentStage,
        TaskComplexity,
        Urgency,
    )

    router = CognitiveRouter()

    # 1. 복잡도 분석 테스트
    print("\n[1] 복잡도 분석 테스트...")
    test_tasks = [
        ("안녕!", TaskComplexity.TRIVIAL),
        ("피보나치 함수 구현해줘", TaskComplexity.SIMPLE),
        ("이진탐색 알고리즘을 설명하고 구현해줘", TaskComplexity.MODERATE),
        ("마이크로서비스 아키텍처를 설계하고 장단점을 분석해줘", TaskComplexity.COMPLEX),
        ("분산 시스템에서 CAP 정리를 고려한 최적의 데이터베이스 설계 전략을 비교 분석하고, 각 시나리오별 트레이드오프를 상세히 설명해줘", TaskComplexity.CRITICAL),
    ]

    for task, expected in test_tasks:
        complexity = router.analyze_complexity(task)
        status = "✅" if complexity == expected else "⚠️"
        print(f"   {status} '{task[:30]}...' → {complexity.name} (예상: {expected.name})")

    # 2. 발달 단계별 라우팅 테스트
    print("\n[2] 발달 단계별 라우팅 테스트...")
    test_task = "퀵소트 알고리즘을 분석하고 구현해줘"

    for stage in DevelopmentStage:
        context = TaskContext(
            task=test_task,
            development_stage=stage,
        )
        decision = router.route(context)
        print(f"   {stage.name}: {decision.model_key} (Thinking: {decision.thinking_level})")
        print(f"      └─ {decision.reasoning}")

    # 3. 긴급도별 라우팅 테스트
    print("\n[3] 긴급도별 라우팅 테스트...")
    for urgency in Urgency:
        context = TaskContext(
            task="복잡한 시스템 설계해줘",
            development_stage=DevelopmentStage.CHILD,
            urgency=urgency,
        )
        decision = router.route(context)
        print(f"   {urgency.name}: {decision.model_key}")

    # 4. 감정 상태 영향 테스트
    print("\n[4] 감정 상태 영향 테스트...")
    emotions_tests = [
        ({"curiosity": 0.9, "joy": 0.5}, "높은 호기심"),
        ({"frustration": 0.8, "sadness": 0.3}, "높은 좌절감"),
        ({"joy": 0.7, "curiosity": 0.3}, "일반 상태"),
    ]

    for emotions, desc in emotions_tests:
        context = TaskContext(
            task="API 설계해줘",
            development_stage=DevelopmentStage.TODDLER,
            emotional_state=emotions,
        )
        decision = router.route(context)
        print(f"   {desc}: {decision.model_key}")
        print(f"      └─ {decision.reasoning}")

    # 5. 이전 실패 고려 테스트
    print("\n[5] 이전 실패 고려 테스트...")
    for failures in [0, 1, 2, 3]:
        context = TaskContext(
            task="버그 수정해줘",
            development_stage=DevelopmentStage.INFANT,
            previous_failures=failures,
        )
        decision = router.route(context)
        print(f"   실패 {failures}회: {decision.model_key} (Thinking: {decision.thinking_level})")

    # 6. 실제 LLM 호출 테스트 (선택적)
    print("\n[6] 실제 LLM 호출 테스트...")
    try:
        context = TaskContext(
            task="1+1은?",
            development_stage=DevelopmentStage.NEWBORN,
            urgency=Urgency.IMMEDIATE,
        )

        response = router.generate(
            task="1+1은 뭐야? 한 단어로 대답해",
            context=context,
            max_tokens=50,
        )

        print(f"   ✅ 응답: {response.strip()}")

    except Exception as e:
        print(f"   ⚠️ LLM 호출 실패 (API 키 필요): {e}")

    # 7. 라우팅 통계
    print("\n[7] 라우팅 통계...")
    stats = router.get_routing_stats()
    print(f"   총 라우팅: {stats['total_routes']}회")
    print(f"   모델 분포: {stats.get('model_distribution', {})}")
    print(f"   평균 비용 계수: {stats.get('average_cost_factor', 0):.2f}")

    print("\n" + "="*60)
    print("✅ Cognitive Router 테스트 완료!")
    print("="*60)


if __name__ == "__main__":
    main()
