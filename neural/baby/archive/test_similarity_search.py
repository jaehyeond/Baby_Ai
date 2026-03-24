"""
Similarity Search Deep Test

유사도 검색 상세 테스트
"""

import sys
import os
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dotenv import load_dotenv
load_dotenv()

from neural.baby.db import get_brain_db
from neural.baby.embeddings import create_embedding, cosine_similarity


def main():
    print("\n" + "="*60)
    print("Similarity Search Deep Test")
    print("="*60)

    db = get_brain_db()

    # 1. 현재 임베딩이 있는 경험 확인
    print("\n[1] 임베딩이 있는 경험 조회...")
    experiences = db.client.table("experiences").select("id, task, embedding").execute()

    exp_with_embedding = None
    for exp in experiences.data:
        has_emb = exp.get('embedding') is not None
        print(f"   - {exp['task'][:30]}: embedding={'Yes' if has_emb else 'No'}")
        if has_emb:
            exp_with_embedding = exp

    if not exp_with_embedding:
        print("\n   ❌ 임베딩이 있는 경험이 없습니다!")
        return

    # 2. RPC를 통한 유사도 검색 (DB 내부에서 계산)
    print(f"\n[2] DB 내부 유사도 검색 테스트...")

    queries = [
        "정렬 알고리즘",
        "버블 정렬",
        "bubble sort",
        "sorting algorithm",
        "퀵소트",
        "날씨가 좋다",
    ]

    for query in queries:
        query_emb = create_embedding(query)
        results = db.search_similar_experiences(
            embedding=query_emb,
            threshold=0.0,  # 모든 결과
            limit=1,
        )
        if results:
            sim = results[0]['similarity']
            emoji = "🟢" if sim > 0.5 else "🟡" if sim > 0.3 else "🔴"
            print(f"   {emoji} '{query}' → 유사도: {sim:.4f}")
        else:
            print(f"   🔴 '{query}' → 결과 없음")

    # 3. RPC 함수 직접 호출 테스트
    print(f"\n[3] RPC 함수 테스트 (threshold=0.3)...")
    test_query = "정렬 알고리즘"
    query_emb = create_embedding(test_query)

    results = db.search_similar_experiences(
        embedding=query_emb,
        threshold=0.3,  # 낮은 threshold
        limit=10,
    )

    if results:
        print(f"   ✅ {len(results)}개 결과 발견:")
        for r in results:
            print(f"      - [{r['similarity']:.4f}] {r['task']}")
    else:
        print("   ⚠️ 결과 없음")

    # 4. 기존 경험에 임베딩 추가
    print(f"\n[4] 기존 경험에 임베딩 추가 중...")
    for exp in experiences.data:
        if exp.get('embedding') is None:
            task = exp['task']
            print(f"   - '{task}' 임베딩 생성...")

            emb = create_embedding(task)
            db.client.table("experiences").update({
                "embedding": emb
            }).eq("id", exp['id']).execute()
            print(f"     ✅ 완료")

    # 5. 다시 검색
    print(f"\n[5] 임베딩 추가 후 재검색 (threshold=0.3)...")
    results = db.search_similar_experiences(
        embedding=query_emb,
        threshold=0.3,
        limit=10,
    )

    if results:
        print(f"   ✅ {len(results)}개 결과 발견:")
        for r in results:
            print(f"      - [{r['similarity']:.4f}] {r['task']}")
    else:
        print("   ⚠️ 결과 없음")

    print("\n" + "="*60)
    print("테스트 완료!")
    print("="*60)


if __name__ == "__main__":
    main()
