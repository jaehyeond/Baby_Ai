"""
Embedding & Supabase Integration Test

OpenAI 임베딩 + Supabase pgvector 통합 테스트
"""

import sys
import os
import io

# Windows 콘솔 UTF-8 설정
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 프로젝트 루트를 path에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dotenv import load_dotenv
load_dotenv()


def test_openai_connection():
    """Step 1: OpenAI API 연결 테스트"""
    print("\n" + "="*60)
    print("Step 1: OpenAI API 연결 테스트")
    print("="*60)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key == "your-openai-api-key-here":
        print("❌ OPENAI_API_KEY가 설정되지 않음")
        return False

    print(f"✅ API Key 발견: {api_key[:20]}...{api_key[-10:]}")

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)

        # 간단한 모델 조회로 연결 확인
        models = client.models.list()
        embedding_models = [m.id for m in models.data if "embedding" in m.id]
        print(f"✅ OpenAI 연결 성공!")
        print(f"   사용 가능한 임베딩 모델: {embedding_models[:5]}")
        return True

    except Exception as e:
        print(f"❌ OpenAI 연결 실패: {e}")
        return False


def test_embedding_generation():
    """Step 2: 임베딩 생성 테스트"""
    print("\n" + "="*60)
    print("Step 2: 임베딩 벡터 생성 테스트")
    print("="*60)

    try:
        from neural.baby.embeddings import create_embedding, EMBEDDING_MODEL, EMBEDDING_DIMENSIONS

        test_text = "피보나치 함수를 파이썬으로 구현하기"
        print(f"   테스트 텍스트: '{test_text}'")
        print(f"   모델: {EMBEDDING_MODEL}")

        embedding = create_embedding(test_text)

        print(f"✅ 임베딩 생성 성공!")
        print(f"   벡터 차원: {len(embedding)} (예상: {EMBEDDING_DIMENSIONS})")
        print(f"   샘플 값: [{embedding[0]:.6f}, {embedding[1]:.6f}, ... {embedding[-1]:.6f}]")

        # 차원 확인
        assert len(embedding) == EMBEDDING_DIMENSIONS, f"차원 불일치: {len(embedding)} != {EMBEDDING_DIMENSIONS}"

        return embedding

    except Exception as e:
        print(f"❌ 임베딩 생성 실패: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_cosine_similarity():
    """Step 3: 코사인 유사도 테스트"""
    print("\n" + "="*60)
    print("Step 3: 코사인 유사도 계산 테스트")
    print("="*60)

    try:
        from neural.baby.embeddings import create_embedding, cosine_similarity

        texts = [
            "피보나치 함수를 파이썬으로 구현",
            "피보나치 수열 알고리즘 코딩",  # 유사함
            "오늘 날씨가 좋습니다",          # 관련 없음
            "재귀 함수로 피보나치 계산",     # 유사함
        ]

        print("   임베딩 생성 중...")
        embeddings = [create_embedding(t) for t in texts]

        print("\n   유사도 결과:")
        base = embeddings[0]
        for i, (text, emb) in enumerate(zip(texts[1:], embeddings[1:]), 1):
            sim = cosine_similarity(base, emb)
            emoji = "🟢" if sim > 0.7 else "🟡" if sim > 0.4 else "🔴"
            print(f"   {emoji} '{texts[0][:20]}...' ↔ '{text[:20]}...': {sim:.4f}")

        print("\n✅ 유사도 계산 성공!")
        return True

    except Exception as e:
        print(f"❌ 유사도 계산 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_supabase_connection():
    """Step 4: Supabase 연결 테스트"""
    print("\n" + "="*60)
    print("Step 4: Supabase 연결 테스트")
    print("="*60)

    try:
        from neural.baby.db import get_brain_db

        db = get_brain_db()
        stats = db.get_stats()

        print(f"✅ Supabase 연결 성공!")
        print(f"   experiences: {stats['experiences_count']}개")
        print(f"   concepts: {stats['concepts_count']}개")
        print(f"   patterns: {stats['patterns_count']}개")

        # baby_state 확인
        state = db.get_baby_state()
        if state:
            print(f"\n   Baby State:")
            print(f"   - development_stage: {state.get('development_stage', 0)}")
            print(f"   - experience_count: {state.get('experience_count', 0)}")

        return db

    except Exception as e:
        print(f"❌ Supabase 연결 실패: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_experience_with_embedding(db):
    """Step 5: 임베딩 포함 경험 저장 테스트"""
    print("\n" + "="*60)
    print("Step 5: 임베딩 포함 경험 저장 테스트")
    print("="*60)

    try:
        from neural.baby.embeddings import create_experience_embedding

        task = "버블소트 알고리즘 구현"
        task_type = "coding"
        output = "def bubble_sort(arr): ..."
        success = True

        print(f"   태스크: '{task}'")
        print(f"   임베딩 생성 중...")

        # 임베딩 생성
        embedding = create_experience_embedding(task, task_type, output, success)
        print(f"   임베딩 차원: {len(embedding)}")

        # DB에 저장
        print(f"   Supabase에 저장 중...")
        result = db.insert_experience(
            task=task,
            task_type=task_type,
            output=output,
            success=success,
            embedding=embedding,
            emotional_salience=0.7,
            dominant_emotion="curiosity",
            emotion_snapshot={"curiosity": 0.8, "joy": 0.5},
            tags=["algorithm", "sorting", "python"],
        )

        print(f"✅ 경험 저장 성공!")
        print(f"   ID: {result.get('id', 'N/A')}")
        print(f"   created_at: {result.get('created_at', 'N/A')}")

        return result.get('id')

    except Exception as e:
        print(f"❌ 경험 저장 실패: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_similarity_search(db):
    """Step 6: 벡터 유사도 검색 테스트"""
    print("\n" + "="*60)
    print("Step 6: pgvector 유사도 검색 테스트")
    print("="*60)

    try:
        from neural.baby.embeddings import create_embedding

        query = "정렬 알고리즘 코딩"
        print(f"   검색 쿼리: '{query}'")

        # 쿼리 임베딩 생성
        query_embedding = create_embedding(query)
        print(f"   쿼리 임베딩 생성 완료")

        # 유사 경험 검색
        print(f"   유사 경험 검색 중...")
        results = db.search_similar_experiences(
            embedding=query_embedding,
            threshold=0.5,
            limit=5,
        )

        if results:
            print(f"\n✅ 유사 경험 {len(results)}개 발견:")
            for i, exp in enumerate(results, 1):
                sim = exp.get('similarity', 0)
                task = exp.get('task', 'N/A')[:40]
                emoji = "🟢" if sim > 0.8 else "🟡" if sim > 0.6 else "🔴"
                print(f"   {i}. {emoji} [{sim:.4f}] {task}")
        else:
            print("⚠️ 유사 경험 없음 (threshold=0.5 이상)")
            print("   힌트: 더 많은 경험을 저장하면 검색 결과가 나옵니다")

        return True

    except Exception as e:
        print(f"❌ 유사도 검색 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_concept_with_embedding(db):
    """Step 7: 개념 저장 + 경험-개념 연결 테스트"""
    print("\n" + "="*60)
    print("Step 7: 개념 저장 및 연결 테스트")
    print("="*60)

    try:
        from neural.baby.embeddings import create_concept_embedding

        concept_name = "sorting_algorithm"
        category = "algorithm"
        description = "정렬 알고리즘: 데이터를 순서대로 배열하는 알고리즘"

        # 기존 개념 확인
        existing = db.get_concept_by_name(concept_name)
        if existing:
            print(f"   기존 개념 발견: {existing.get('id')}")
            return existing.get('id')

        # 임베딩 생성
        embedding = create_concept_embedding(concept_name, category, description)
        print(f"   임베딩 차원: {len(embedding)}")

        # 개념 저장
        result = db.insert_concept(
            name=concept_name,
            category=category,
            description=description,
            embedding=embedding,
        )

        print(f"✅ 개념 저장 성공!")
        print(f"   ID: {result.get('id', 'N/A')}")
        print(f"   name: {result.get('name', 'N/A')}")

        return result.get('id')

    except Exception as e:
        print(f"❌ 개념 저장 실패: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """전체 테스트 실행"""
    print("\n" + "="*60)
    print("🧠 Baby Brain: Embedding & Supabase Integration Test")
    print("="*60)

    results = {
        "openai_connection": False,
        "embedding_generation": False,
        "cosine_similarity": False,
        "supabase_connection": False,
        "experience_with_embedding": False,
        "similarity_search": False,
        "concept_with_embedding": False,
    }

    # Step 1: OpenAI 연결
    results["openai_connection"] = test_openai_connection()
    if not results["openai_connection"]:
        print("\n⛔ OpenAI 연결 실패 - 테스트 중단")
        return

    # Step 2: 임베딩 생성
    embedding = test_embedding_generation()
    results["embedding_generation"] = embedding is not None
    if not results["embedding_generation"]:
        print("\n⛔ 임베딩 생성 실패 - 테스트 중단")
        return

    # Step 3: 유사도 계산
    results["cosine_similarity"] = test_cosine_similarity()

    # Step 4: Supabase 연결
    db = test_supabase_connection()
    results["supabase_connection"] = db is not None
    if not results["supabase_connection"]:
        print("\n⛔ Supabase 연결 실패 - 테스트 중단")
        return

    # Step 5: 임베딩 포함 경험 저장
    exp_id = test_experience_with_embedding(db)
    results["experience_with_embedding"] = exp_id is not None

    # Step 6: 유사도 검색
    results["similarity_search"] = test_similarity_search(db)

    # Step 7: 개념 저장
    concept_id = test_concept_with_embedding(db)
    results["concept_with_embedding"] = concept_id is not None

    # 결과 요약
    print("\n" + "="*60)
    print("📊 테스트 결과 요약")
    print("="*60)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, passed_test in results.items():
        emoji = "✅" if passed_test else "❌"
        print(f"   {emoji} {test_name}")

    print(f"\n   총 {passed}/{total} 테스트 통과")

    if passed == total:
        print("\n🎉 모든 테스트 통과! 임베딩 + Supabase 연동 완료!")
    else:
        print(f"\n⚠️ {total - passed}개 테스트 실패")


if __name__ == "__main__":
    main()
