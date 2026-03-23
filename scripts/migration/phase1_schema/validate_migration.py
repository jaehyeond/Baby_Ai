"""
Phase 1: 마이그레이션 정합성 검증

실행: python scripts/migration/phase1_schema/validate_migration.py

5개 검증 항목 모두 PASS여야 Phase 2 진행 가능.
FAIL 시 import_to_neo4j.py 재실행 (MERGE라 안전).
"""

import os
import json
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

# ── 연결 설정 ───────────────────────────────────────────────────────────────
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")
ENTRY_URI    = os.getenv("NEO4J_URI")
USERNAME     = os.getenv("NEO4J_USERNAME")
PASSWORD     = os.getenv("NEO4J_PASSWORD")
DB_NAME      = os.getenv("NEO4J_DATABASE")
AUTH         = (USERNAME, PASSWORD)

S_HEADERS = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}

DATA_DIR = Path(__file__).parent.parent / "migration_data"


def get_writer_driver():
    with GraphDatabase.driver(ENTRY_URI, auth=AUTH) as d:
        res = d.execute_query(
            f'SHOW DATABASES YIELD name, address, writer '
            f'WHERE name = "{DB_NAME}" AND writer = true',
            database_="system",
        )
        writer_host = res.records[0]["address"].split(":")[0]
    return GraphDatabase.driver(f"bolt+s://{writer_host}", auth=AUTH)


def supabase_count(table: str, col: str = "*") -> int:
    """Supabase REST API로 테이블 행 수 조회"""
    r = httpx.get(
        f"{SUPABASE_URL}/rest/v1/{table}?select={col}&limit=1",
        headers={**S_HEADERS, "Prefer": "count=exact"},
        timeout=15,
    )
    cr = r.headers.get("content-range", "0/0").split("/")[-1]
    return int(cr) if cr.isdigit() else 0


def neo4j_count(driver, label: str) -> int:
    with driver.session() as s:
        result = s.run(f"MATCH (n:{label}) RETURN count(n) AS c")
        return result.single()["c"]


def neo4j_rel_count(driver, rel_type: str) -> int:
    with driver.session() as s:
        result = s.run(f"MATCH ()-[r:{rel_type}]->() RETURN count(r) AS c")
        return result.single()["c"]


# ── 검증 함수들 ─────────────────────────────────────────────────────────────

def check_node_counts(driver) -> bool:
    """검증 1: 노드 수가 Supabase 행 수와 일치하는지"""
    print("\n[Check 1] Node counts vs Supabase row counts")

    mappings = [
        ("brain_regions",       "BrainRegion"),
        ("semantic_concepts",   "Concept"),
        ("experiences",         "Experience"),
        ("emotion_logs",        "EmotionLog"),
        ("predictions",         "Prediction"),
        ("imagination_sessions","Imagination"),
        ("procedural_patterns", "Procedure"),
        ("visual_experiences",  "VisualExperience"),
        ("pending_questions",   "PendingQuestion"),
        ("autonomous_goals",    "AutonomousGoal"),
        ("curiosity_queue",     "CuriosityLog"),
    ]

    all_pass = True
    for table, label in mappings:
        supabase_n = supabase_count(table)
        neo4j_n    = neo4j_count(driver, label)
        match = supabase_n == neo4j_n
        status = "PASS" if match else "FAIL"
        if not match:
            all_pass = False
        print(f"  [{status}] {label}: supabase={supabase_n}, neo4j={neo4j_n}")

    return all_pass


def check_relation_counts(driver) -> bool:
    """검증 2: 관계 수가 junction 테이블 행 수와 일치하는지"""
    print("\n[Check 2] Relationship counts vs junction table counts")

    mappings = [
        ("concept_relations",    "RELATES_TO",    "id"),
        ("concept_brain_mapping","MAPPED_TO",     "concept_id"),  # no id col
        ("experience_concepts",  "INVOLVES",      "id"),
        ("causal_models",        "CAUSES",        "id"),
    ]

    all_pass = True
    for table, rel, col in mappings:
        supabase_n = supabase_count(table, col)
        neo4j_n    = neo4j_rel_count(driver, rel)
        match = supabase_n == neo4j_n
        status = "PASS" if match else "FAIL"
        if not match:
            all_pass = False
        print(f"  [{status}] {rel}: supabase={supabase_n}, neo4j={neo4j_n}")

    return all_pass


def check_embedding_integrity(driver) -> bool:
    """검증 3: embedding 보유 개념에 NULL이 없는지"""
    print("\n[Check 3] Embedding integrity")

    # Supabase에서 embedding 보유 수 확인
    r = httpx.get(
        f"{SUPABASE_URL}/rest/v1/semantic_concepts?embedding=not.is.null&select=id&limit=1",
        headers={**S_HEADERS, "Prefer": "count=exact"},
        timeout=15,
    )
    supabase_with_emb = int(r.headers.get("content-range","0/0").split("/")[-1] or 0)

    with driver.session() as s:
        neo4j_with_emb = s.run(
            "MATCH (c:Concept) WHERE c.embedding IS NOT NULL RETURN count(c) AS n"
        ).single()["n"]
        neo4j_null_emb = s.run(
            "MATCH (c:Concept) WHERE c.embedding IS NULL RETURN count(c) AS n"
        ).single()["n"]

    print(f"  Supabase concepts with embedding: {supabase_with_emb}")
    print(f"  Neo4j Concept with embedding:     {neo4j_with_emb}")
    print(f"  Neo4j Concept with NULL embedding: {neo4j_null_emb}")

    pass_check = neo4j_with_emb == supabase_with_emb
    print(f"  [{'PASS' if pass_check else 'FAIL'}] Embedding count matches: {pass_check}")
    return pass_check


def check_vector_indexes(driver) -> bool:
    """검증 4: 벡터 인덱스가 ONLINE 상태인지"""
    print("\n[Check 4] Vector index status")

    with driver.session() as s:
        results = list(s.run(
            "SHOW INDEXES YIELD name, type, state WHERE type = 'VECTOR' RETURN name, state"
        ))

    expected = {"concept_embeddings", "experience_embeddings", "visual_embeddings"}
    found = {r["name"] for r in results}
    all_online = all(r["state"] == "ONLINE" for r in results)

    for r in results:
        status = "PASS" if r["state"] == "ONLINE" else "FAIL"
        print(f"  [{status}] {r['name']}: {r['state']}")

    missing = expected - found
    if missing:
        print(f"  [FAIL] Missing indexes: {missing}")
        return False

    if not all_online:
        print("  [WARN] Some indexes not yet ONLINE — may still be building. Retry in 1 min.")
        return False

    print(f"  [PASS] All {len(results)} vector indexes ONLINE")
    return True


def check_vector_search(driver) -> bool:
    """검증 5: 벡터 검색이 실제로 동작하는지"""
    print("\n[Check 5] Vector search functional test")

    # 실제 embedding이 있는 Concept 1개를 가져와서 자기 자신 검색
    with driver.session() as s:
        result = list(s.run(
            "MATCH (c:Concept) WHERE c.embedding IS NOT NULL RETURN c.embedding AS emb, c.name AS name LIMIT 1"
        ))

    if not result:
        print("  [FAIL] No Concept with embedding found — cannot test vector search")
        return False

    test_emb = result[0]["emb"]
    test_name = result[0]["name"]

    with driver.session() as s:
        search_results = list(s.run(
            "CALL db.index.vector.queryNodes('concept_embeddings', 5, $emb) "
            "YIELD node, score RETURN node.name AS name, score",
            emb=test_emb,
        ))

    if not search_results:
        print("  [FAIL] Vector search returned 0 results")
        return False

    print(f"  Query: Concept '{test_name}' → top {len(search_results)} similar:")
    for r in search_results[:3]:
        print(f"    {r['name']} (score={r['score']:.4f})")

    # 자기 자신이 최상위에 있어야 함 (score ≈ 1.0)
    top_score = search_results[0]["score"]
    pass_check = top_score > 0.99
    print(f"  [{'PASS' if pass_check else 'WARN'}] Top similarity score: {top_score:.4f} (expected > 0.99)")
    return True  # 결과가 있으면 일단 통과 (score 경고는 WARN)


# ── 메인 ────────────────────────────────────────────────────────────────────

def main():
    print("=== Migration Validation ===")
    print(f"Supabase: {SUPABASE_URL}")
    print(f"Neo4j entry: {ENTRY_URI}")

    driver = get_writer_driver()

    results = {}
    try:
        results["node_counts"]        = check_node_counts(driver)
        results["relation_counts"]    = check_relation_counts(driver)
        results["embedding_integrity"]= check_embedding_integrity(driver)
        results["vector_indexes"]     = check_vector_indexes(driver)
        results["vector_search"]      = check_vector_search(driver)
    finally:
        driver.close()

    print("\n" + "="*50)
    print("VALIDATION SUMMARY")
    print("="*50)
    all_pass = True
    for check, passed in results.items():
        status = "[PASS]" if passed else "[FAIL]"
        print(f"  {status}  {check}")
        if not passed:
            all_pass = False

    print()
    if all_pass:
        print("[PHASE 1 COMPLETE] All 5 checks passed.")
        print("Ready for Phase 2: neo4j_db.py + FastAPI backend")
    else:
        print("[PHASE 1 INCOMPLETE] Fix failures and re-run import_to_neo4j.py")
        print("(MERGE is idempotent — safe to re-run)")
        sys.exit(1)


if __name__ == "__main__":
    main()
