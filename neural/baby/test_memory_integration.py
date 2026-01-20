"""
Memory System Integration Test

MemorySystem의 Supabase 연동 통합 테스트
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
    print("Memory System Integration Test")
    print("="*60)

    from neural.baby.memory import MemorySystem

    # 1. MemorySystem 초기화 (Supabase 모드)
    print("\n[1] MemorySystem 초기화 (Supabase 모드)...")
    memory = MemorySystem(use_supabase=True)
    print(f"   {memory}")

    stats = memory.get_stats()
    print(f"   Episodic backend: {stats['episodic']['backend']}")
    print(f"   Semantic backend: {stats['semantic']['backend']}")
    print(f"   Procedural backend: {stats['procedural']['backend']}")

    # 2. 경험 기록 테스트
    print("\n[2] 경험 기록 테스트...")
    test_experiences = [
        {
            "request": "이진탐색 알고리즘 구현해줘",
            "action": "def binary_search(arr, target): ...",
            "outcome": "success",
            "success": True,
            "task_type": "algorithm",
            "emotion_snapshot": {"curiosity": 0.8, "joy": 0.6, "dominant": "curiosity"},
        },
        {
            "request": "팩토리얼 함수 만들어줘",
            "action": "def factorial(n): return 1 if n <= 1 else n * factorial(n-1)",
            "outcome": "success",
            "success": True,
            "task_type": "function",
            "emotion_snapshot": {"curiosity": 0.5, "joy": 0.8, "dominant": "joy"},
        },
    ]

    for exp_data in test_experiences:
        exp = memory.record_experience(**exp_data)
        print(f"   ✅ '{exp_data['request'][:30]}...'")
        print(f"      ID: {exp.id}, DB_ID: {exp.db_id}")

    # 3. 통계 확인
    print("\n[3] 통계 확인...")
    stats = memory.get_stats()
    print(f"   Episodic:")
    print(f"     - Local: {stats['episodic']['total_local']}")
    print(f"     - Supabase: {stats['episodic']['total_supabase']}")
    print(f"   Semantic:")
    print(f"     - Local: {stats['semantic']['knowledge_count']}")
    print(f"     - Supabase: {stats['semantic']['supabase_concepts']}")
    print(f"   Procedural:")
    print(f"     - Local: {stats['procedural']['procedure_count']}")
    print(f"     - Supabase: {stats['procedural']['supabase_patterns']}")

    # 4. 유사 경험 검색 테스트
    print("\n[4] 유사 경험 검색 테스트...")
    queries = [
        "탐색 알고리즘",
        "재귀 함수",
        "정렬",
    ]

    for query in queries:
        similar = memory.episodic.recall_similar(query, n=2)
        print(f"   Query: '{query}'")
        if similar:
            for exp in similar:
                print(f"     → {exp.request[:40]}...")
        else:
            print(f"     → (결과 없음)")

    # 5. 태스크를 위한 기억 회상 테스트
    print("\n[5] 태스크 기억 회상 테스트...")
    recalled = memory.recall_for_task("이진탐색 구현", task_type="algorithm")
    print(f"   유사 경험: {len(recalled['similar_experiences'])}개")
    print(f"   성공 예시: {len(recalled['successful_examples'])}개")
    print(f"   패턴: {recalled['patterns'][:3] if recalled['patterns'] else '없음'}")
    print(f"   최적 접근법: {recalled['best_approach'][:50] if recalled['best_approach'] else '없음'}")

    # 6. 최근 경험 조회
    print("\n[6] 최근 경험 조회...")
    recent = memory.episodic.recall_recent(5)
    print(f"   최근 {len(recent)}개 경험:")
    for exp in recent:
        success_icon = "✓" if exp.success else "✗"
        print(f"     [{success_icon}] {exp.request[:40]}...")

    # 7. 성공한 경험 조회
    print("\n[7] 성공한 경험 조회...")
    successful = memory.episodic.recall_successful(n=3)
    print(f"   성공 경험 {len(successful)}개:")
    for exp in successful:
        print(f"     ✓ {exp.request[:40]}...")

    print("\n" + "="*60)
    print("✅ 메모리 시스템 통합 테스트 완료!")
    print("="*60)


if __name__ == "__main__":
    main()
