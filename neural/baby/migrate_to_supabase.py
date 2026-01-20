"""
Migration Script: .baby_memory/ JSON → Supabase

기존 로컬 JSON 파일의 데이터를 Supabase DB로 마이그레이션합니다.

사용법:
    cd e:\A2A\our-a2a-project
    .\.venv\Scripts\python.exe -m neural.baby.migrate_to_supabase
"""

import os
import json
import sys
from datetime import datetime
from typing import Optional

# 프로젝트 루트를 path에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dotenv import load_dotenv
load_dotenv()


def migrate_baby_state(state_path: str, db) -> bool:
    """baby_state 마이그레이션"""
    if not os.path.exists(state_path):
        print(f"[SKIP] {state_path} 없음")
        return False

    with open(state_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    development = data.get("development", {})
    self_model = data.get("self_model", {})

    print(f"[INFO] baby_state 마이그레이션 시작")
    print(f"  - Stage: {development.get('stage', 0)}")
    print(f"  - Experience Count: {development.get('experience_count', 0)}")
    print(f"  - Success Count: {development.get('success_count', 0)}")

    # Supabase 업데이트
    try:
        result = db.update_baby_state(
            development_stage=development.get("stage", 0),
            experience_count=development.get("experience_count", 0),
            success_count=development.get("success_count", 0),
            milestones=development.get("milestones", []),
            capabilities=self_model.get("assessment", {}).get("strengths", []),
            preferences={},
            limitations=self_model.get("assessment", {}).get("limitations", []),
        )
        print(f"[OK] baby_state 마이그레이션 완료")
        return True
    except Exception as e:
        print(f"[ERROR] baby_state 마이그레이션 실패: {e}")
        return False


def migrate_experiences(episodic_path: str, db, embedder) -> int:
    """experiences 마이그레이션"""
    if not os.path.exists(episodic_path):
        print(f"[SKIP] {episodic_path} 없음")
        return 0

    with open(episodic_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    short_term = data.get("short_term", [])
    long_term = data.get("long_term", [])
    all_experiences = short_term + long_term

    print(f"[INFO] experiences 마이그레이션 시작: {len(all_experiences)}개")

    migrated = 0
    for exp in all_experiences:
        try:
            # 임베딩 생성 (가능한 경우)
            embedding = None
            if embedder:
                try:
                    embed_text = f"{exp.get('request', '')} {exp.get('action', '')[:500]}"
                    embedding = embedder(embed_text)
                except Exception as e:
                    print(f"  [WARN] 임베딩 생성 실패: {e}")

            # Supabase에 저장
            result = db.insert_experience(
                task=exp.get("request", ""),
                task_type=exp.get("task_type", "default"),
                output=exp.get("action", ""),
                success=exp.get("success", False),
                emotional_salience=exp.get("emotional_weight", 0.5),
                embedding=embedding,
                tags=[exp.get("task_type", "default")],
            )

            if result:
                migrated += 1
                print(f"  [OK] {exp.get('id', 'N/A')}: {exp.get('request', '')[:30]}...")
            else:
                print(f"  [FAIL] {exp.get('id', 'N/A')}")

        except Exception as e:
            print(f"  [ERROR] {exp.get('id', 'N/A')}: {e}")

    print(f"[OK] experiences 마이그레이션 완료: {migrated}/{len(all_experiences)}개")
    return migrated


def migrate_semantic(semantic_path: str, db, embedder) -> int:
    """semantic_concepts 마이그레이션"""
    if not os.path.exists(semantic_path):
        print(f"[SKIP] {semantic_path} 없음")
        return 0

    with open(semantic_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    knowledge = data.get("knowledge", {})
    print(f"[INFO] semantic_concepts 마이그레이션 시작: {len(knowledge)}개")

    migrated = 0
    for name, info in knowledge.items():
        try:
            # 임베딩 생성
            embedding = None
            if embedder:
                try:
                    category = info.get("category", "") if isinstance(info, dict) else ""
                    embed_text = f"{name} {category}"
                    embedding = embedder(embed_text)
                except:
                    pass

            # Supabase에 저장
            category = info.get("category", "") if isinstance(info, dict) else ""
            description = info.get("description", "") if isinstance(info, dict) else str(info)

            result = db.insert_concept(
                name=name,
                category=category,
                description=description,
                embedding=embedding,
            )

            if result:
                migrated += 1

        except Exception as e:
            # 중복 키 에러는 무시
            if "duplicate" not in str(e).lower():
                print(f"  [ERROR] {name}: {e}")

    print(f"[OK] semantic_concepts 마이그레이션 완료: {migrated}개")
    return migrated


def migrate_procedural(procedural_path: str, db) -> int:
    """procedural_patterns 마이그레이션"""
    if not os.path.exists(procedural_path):
        print(f"[SKIP] {procedural_path} 없음")
        return 0

    with open(procedural_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    procedures = data.get("procedures", {})
    print(f"[INFO] procedural_patterns 마이그레이션 시작: {len(procedures)}개")

    migrated = 0
    for key, proc in procedures.items():
        try:
            task_type = proc.get("task_type", key.split(":")[0] if ":" in key else key)
            approach = proc.get("approach", proc.get("steps", [""])[0] if proc.get("steps") else "")

            if not approach:
                continue

            # 성공/실패 횟수 기반으로 여러 번 기록
            success_count = proc.get("success_count", 0)
            failure_count = proc.get("failure_count", 0)

            # 최소 한 번은 기록
            if success_count == 0 and failure_count == 0:
                success_count = proc.get("uses", 1)

            # 성공 기록
            for _ in range(min(success_count, 5)):  # 최대 5번
                db.upsert_pattern(task_type=task_type, approach=approach[:100], success=True)

            # 실패 기록
            for _ in range(min(failure_count, 5)):
                db.upsert_pattern(task_type=task_type, approach=approach[:100], success=False)

            migrated += 1

        except Exception as e:
            print(f"  [ERROR] {key}: {e}")

    print(f"[OK] procedural_patterns 마이그레이션 완료: {migrated}개")
    return migrated


def main():
    """메인 마이그레이션 함수"""
    print("=" * 60)
    print("Baby Brain Migration: JSON → Supabase")
    print("=" * 60)

    # 경로 설정
    base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    memory_path = os.path.join(base_path, ".baby_memory")

    print(f"\n[INFO] 소스 경로: {memory_path}")

    if not os.path.exists(memory_path):
        print(f"[ERROR] .baby_memory/ 디렉토리가 없습니다!")
        return

    # Supabase 연결
    print("\n[INFO] Supabase 연결 중...")
    try:
        from neural.baby.db import get_brain_db
        db = get_brain_db()
        print("[OK] Supabase 연결 성공")
    except Exception as e:
        print(f"[ERROR] Supabase 연결 실패: {e}")
        return

    # 임베딩 함수 (선택적)
    embedder = None
    try:
        from neural.baby.embeddings import safe_create_embedding
        embedder = safe_create_embedding
        print("[OK] OpenAI 임베딩 활성화")
    except Exception as e:
        print(f"[WARN] OpenAI 임베딩 비활성화: {e}")
        print("  → 임베딩 없이 마이그레이션을 진행합니다.")

    print("\n" + "-" * 60)

    # 1. baby_state 마이그레이션
    state_path = os.path.join(memory_path, "state.json")
    migrate_baby_state(state_path, db)

    print("-" * 60)

    # 2. experiences 마이그레이션
    episodic_path = os.path.join(memory_path, "episodic.json")
    migrate_experiences(episodic_path, db, embedder)

    print("-" * 60)

    # 3. semantic_concepts 마이그레이션
    semantic_path = os.path.join(memory_path, "semantic.json")
    migrate_semantic(semantic_path, db, embedder)

    print("-" * 60)

    # 4. procedural_patterns 마이그레이션
    procedural_path = os.path.join(memory_path, "procedural.json")
    migrate_procedural(procedural_path, db)

    print("\n" + "=" * 60)
    print("마이그레이션 완료!")
    print("=" * 60)

    # 최종 통계
    try:
        stats = db.get_stats()
        print(f"\n[통계]")
        print(f"  - Experiences: {stats.get('experiences_count', 0)}개")
        print(f"  - Concepts: {stats.get('concepts_count', 0)}개")
        print(f"  - Patterns: {stats.get('patterns_count', 0)}개")
    except Exception as e:
        print(f"[WARN] 통계 조회 실패: {e}")


if __name__ == "__main__":
    main()
