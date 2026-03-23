"""
Phase 1: JSON → Neo4j 임포트

실행: python scripts/migration/phase1_schema/import_to_neo4j.py

전제조건:
  1. export_supabase.py 실행 완료 (migration_data/*.json 존재)
  2. neo4j_schema.cypher의 제약조건+일반 인덱스 적용 완료
  3. 벡터 인덱스는 이 스크립트 마지막에 자동 생성

설계 원칙:
  - MERGE 사용 (CREATE 아님) → 재실행 가능
  - 배치 크기 100 (embedding 1536-float × 100 ≈ 600KB/배치)
  - 관계 생성은 양 끝 노드 임포트 완료 후 Phase B에서 실행
  - embedding: JSON 문자열 → json.loads() 파싱 필수
  - 고아 관계: 로그 기록 후 계속 진행 (abort 안 함)
"""

import os
import json
import sys
import ast
from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

# ── 연결 설정 (검증된 2-step writer lookup 패턴) ──────────────────────────
ENTRY_URI = os.getenv("NEO4J_URI")   # bolt+s://b76cbc85.databases.neo4j.io
USERNAME  = os.getenv("NEO4J_USERNAME")
PASSWORD  = os.getenv("NEO4J_PASSWORD")
DB_NAME   = os.getenv("NEO4J_DATABASE")
AUTH      = (USERNAME, PASSWORD)

DATA_DIR  = Path(__file__).parent.parent / "migration_data"
BATCH_SIZE = 100

ORPHAN_LOG = DATA_DIR / "_orphan_relations.json"


def get_writer_driver():
    """검증된 2-step writer 연결 패턴"""
    print("[Connect] Resolving writer address via system DB...")
    with GraphDatabase.driver(ENTRY_URI, auth=AUTH) as d:
        res = d.execute_query(
            f'SHOW DATABASES YIELD name, address, writer '
            f'WHERE name = "{DB_NAME}" AND writer = true',
            database_="system",
        )
        if not res.records:
            raise RuntimeError(f"No writer found for database '{DB_NAME}'")
        writer_host = res.records[0]["address"].split(":")[0]

    writer_uri = f"bolt+s://{writer_host}"
    print(f"[Connect] Writer URI: {writer_uri}")
    return GraphDatabase.driver(writer_uri, auth=AUTH)


def normalize_embedding(value) -> list[float] | None:
    """embedding 값 정규화: string → list[float]"""
    if value is None:
        return None
    if isinstance(value, list):
        return [float(x) for x in value]
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return [float(x) for x in parsed]
        except (json.JSONDecodeError, ValueError):
            return None
    return None


def normalize_array(value) -> list:
    """Python string으로 된 list → 실제 list (source_experiences 등)"""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            result = ast.literal_eval(value)
            return result if isinstance(result, list) else []
        except (ValueError, SyntaxError):
            return []
    return []


def run_batch(driver, query: str, batch: list[dict], label: str):
    """배치 UNWIND 실행"""
    with driver.session() as session:
        result = session.run(query, batch=batch)
        summary = result.consume()
        return summary.counters


def load_json(table: str) -> list[dict]:
    path = DATA_DIR / f"{table}.json"
    if not path.exists():
        print(f"  [WARN] {path} not found — skipping")
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    print(f"  Loaded {len(data)} rows from {table}.json")
    return data


# ── Phase A: 노드 임포트 ───────────────────────────────────────────────────

def import_brain_regions(driver):
    print("\n[Phase A-1] BrainRegion nodes")
    rows = load_json("brain_regions")
    if not rows:
        return

    query = """
    UNWIND $batch AS row
    MERGE (n:BrainRegion {name: row.name})
    SET n += {
      id: row.id,
      description: row.description,
      color: row.color,
      position_x: row.position_x,
      position_y: row.position_y,
      position_z: row.position_z,
      functions: row.functions,
      extras: row.extras,
      created_at: row.created_at
    }
    """
    batch = [{k: (v if not isinstance(v, dict) else json.dumps(v)) for k, v in r.items()} for r in rows]
    stats = run_batch(driver, query, batch, "BrainRegion")
    print(f"  [OK] merged={stats.nodes_created + stats.properties_set}")


def import_concepts(driver):
    print("\n[Phase A-2] Concept nodes (820 rows, embedding 1536-dim)")
    rows = load_json("semantic_concepts")
    if not rows:
        return

    query = """
    UNWIND $batch AS row
    MERGE (n:Concept {id: row.id})
    SET n.name = row.name,
        n.category = row.category,
        n.description = row.description,
        n.strength = row.strength,
        n.usage_count = row.usage_count,
        n.definition_text = row.definition_text,
        n.definition_strength = row.definition_strength,
        n.acquired_at_stage = row.acquired_at_stage,
        n.exploration_count = row.exploration_count,
        n.last_explored_at = row.last_explored_at,
        n.created_at = row.created_at,
        n.updated_at = row.updated_at,
        n.ablation_run_id = row.ablation_run_id
    WITH n, row
    WHERE row.embedding IS NOT NULL
    SET n.embedding = row.embedding
    """

    processed = 0
    for i in range(0, len(rows), BATCH_SIZE):
        batch_raw = rows[i:i+BATCH_SIZE]
        batch = []
        for r in batch_raw:
            row = dict(r)
            row["embedding"] = normalize_embedding(row.get("embedding"))
            # list/dict 컬럼 직렬화
            row["relations"] = json.dumps(row.get("relations") or [])
            row["examples"] = json.dumps(row.get("examples") or [])
            row["extras"] = json.dumps(row.get("extras") or {})
            batch.append(row)
        run_batch(driver, query, batch, "Concept")
        processed += len(batch)
        print(f"  Concept: {processed}/{len(rows)}")

    print(f"  [OK] Concept import complete")


def import_experiences(driver):
    print("\n[Phase A-3] Experience nodes (3,039 rows)")
    rows = load_json("experiences")
    if not rows:
        return

    query = """
    UNWIND $batch AS row
    MERGE (n:Experience {id: row.id})
    SET n.task = row.task,
        n.task_type = row.task_type,
        n.output = row.output,
        n.success = row.success,
        n.emotional_salience = row.emotional_salience,
        n.dominant_emotion = row.dominant_emotion,
        n.memory_strength = row.memory_strength,
        n.access_count = row.access_count,
        n.development_stage = row.development_stage,
        n.media_type = row.media_type,
        n.feedback_count = row.feedback_count,
        n.created_at = row.created_at,
        n.ablation_run_id = row.ablation_run_id
    WITH n, row
    WHERE row.embedding IS NOT NULL
    SET n.embedding = row.embedding
    """

    processed = 0
    for i in range(0, len(rows), BATCH_SIZE):
        batch_raw = rows[i:i+BATCH_SIZE]
        batch = []
        for r in batch_raw:
            row = dict(r)
            row["embedding"] = normalize_embedding(row.get("embedding"))
            row["related_experiences"] = json.dumps(row.get("related_experiences") or [])
            row["tags"] = json.dumps(row.get("tags") or [])
            row["extras"] = json.dumps(row.get("extras") or {})
            row["emotion_snapshot"] = json.dumps(row.get("emotion_snapshot") or {})
            batch.append(row)
        run_batch(driver, query, batch, "Experience")
        processed += len(batch)
        if processed % 500 == 0 or processed == len(rows):
            print(f"  Experience: {processed}/{len(rows)}")

    print(f"  [OK] Experience import complete")


def import_emotion_logs(driver):
    print("\n[Phase A-4] EmotionLog nodes (1,503 rows)")
    rows = load_json("emotion_logs")
    if not rows:
        return

    query = """
    UNWIND $batch AS row
    MERGE (n:EmotionLog {id: row.id})
    SET n += {
      emotion_type: row.emotion_type,
      intensity: row.intensity,
      trigger: row.trigger,
      context: row.context,
      outcome: row.outcome,
      created_at: row.created_at
    }
    """
    processed = 0
    for i in range(0, len(rows), BATCH_SIZE):
        batch = [{k: (json.dumps(v) if isinstance(v, (dict, list)) else v)
                  for k, v in r.items()} for r in rows[i:i+BATCH_SIZE]]
        run_batch(driver, query, batch, "EmotionLog")
        processed += len(batch)
    print(f"  [OK] EmotionLog: {processed} rows")


def import_baby_state(driver):
    print("\n[Phase A-5] BabyState node (singleton)")
    rows = load_json("baby_state")
    if not rows:
        return

    row = rows[0]
    query = """
    MERGE (n:BabyState {id: 'singleton'})
    SET n += $props
    """
    props = {k: (json.dumps(v) if isinstance(v, (dict, list)) else v) for k, v in row.items()}
    with driver.session() as session:
        session.run(query, props=props)
    print(f"  [OK] BabyState: stage={row.get('development_stage')}, xp={row.get('experience_count')}")


def import_simple_nodes(driver, table: str, label: str):
    """소규모 테이블 임포트 (공통 패턴)"""
    print(f"\n[Phase A] {label} nodes")
    rows = load_json(table)
    if not rows:
        return

    query = f"""
    UNWIND $batch AS row
    MERGE (n:{label} {{id: row.id}})
    SET n += row
    """
    processed = 0
    for i in range(0, len(rows), BATCH_SIZE):
        batch = [{k: (json.dumps(v) if isinstance(v, (dict, list)) else v)
                  for k, v in r.items()} for r in rows[i:i+BATCH_SIZE]]
        run_batch(driver, query, batch, label)
        processed += len(batch)
    print(f"  [OK] {label}: {processed} rows")


# ── Phase B: 관계 임포트 ───────────────────────────────────────────────────

def import_concept_relations(driver):
    print("\n[Phase B-1] (:Concept)-[:RELATES_TO]->(:Concept)")
    rows = load_json("concept_relations")
    if not rows:
        return

    query = """
    UNWIND $batch AS row
    MATCH (src:Concept {id: row.from_concept_id})
    MATCH (tgt:Concept {id: row.to_concept_id})
    MERGE (src)-[r:RELATES_TO {id: row.id}]->(tgt)
    SET r.relation_type = row.relation_type,
        r.strength = toFloat(row.strength),
        r.evidence_count = toInteger(row.evidence_count),
        r.bidirectional = row.bidirectional,
        r.confidence = toFloat(row.confidence),
        r.created_at = row.created_at,
        r.ablation_run_id = row.ablation_run_id
    """
    orphans = []
    processed = 0

    for i in range(0, len(rows), BATCH_SIZE):
        batch_raw = rows[i:i+BATCH_SIZE]
        batch = []
        for r in batch_raw:
            row = dict(r)
            row["source_experiences"] = json.dumps(normalize_array(row.get("source_experiences")))
            row["extras"] = json.dumps(row.get("extras") or {})
            row["bidirectional"] = bool(row.get("bidirectional", False))
            batch.append(row)

        try:
            run_batch(driver, query, batch, "RELATES_TO")
        except Exception as e:
            print(f"  [WARN] batch {i//BATCH_SIZE} error: {e}")
            orphans.extend([r["id"] for r in batch_raw])

        processed += len(batch)
        if processed % 200 == 0 or processed == len(rows):
            print(f"  RELATES_TO: {processed}/{len(rows)}")

    if orphans:
        print(f"  [WARN] {len(orphans)} orphan relations logged")
        _log_orphans("RELATES_TO", orphans)
    print(f"  [OK] concept_relations import complete")


def import_concept_brain_mapping(driver):
    print("\n[Phase B-2] (:Concept)-[:MAPPED_TO]->(:BrainRegion)")
    rows = load_json("concept_brain_mapping")
    if not rows:
        return

    query = """
    UNWIND $batch AS row
    MATCH (c:Concept {id: row.concept_id})
    MATCH (br:BrainRegion {id: row.brain_region_id})
    MERGE (c)-[r:MAPPED_TO]->(br)
    SET r.activation_weight = row.activation_weight,
        r.mapping_type = row.mapping_type,
        r.created_at = row.created_at
    """
    processed = 0
    for i in range(0, len(rows), BATCH_SIZE):
        batch = [dict(r) for r in rows[i:i+BATCH_SIZE]]
        try:
            run_batch(driver, query, batch, "MAPPED_TO")
        except Exception as e:
            print(f"  [WARN] batch error: {e}")
        processed += len(batch)
    print(f"  [OK] MAPPED_TO: {processed} relations")


def import_experience_concepts(driver):
    print("\n[Phase B-3] (:Experience)-[:INVOLVES]->(:Concept)")
    rows = load_json("experience_concepts")
    if not rows:
        return

    query = """
    UNWIND $batch AS row
    MATCH (e:Experience {id: row.experience_id})
    MATCH (c:Concept {id: row.concept_id})
    MERGE (e)-[r:INVOLVES]->(c)
    SET r.extraction_type = row.extraction_type,
        r.confidence = row.confidence,
        r.relevance = row.relevance,
        r.co_activation_count = row.co_activation_count,
        r.created_at = row.created_at,
        r.last_activated_at = row.last_activated_at
    """
    processed = 0
    for i in range(0, len(rows), BATCH_SIZE):
        batch = [dict(r) for r in rows[i:i+BATCH_SIZE]]
        try:
            run_batch(driver, query, batch, "INVOLVES")
        except Exception as e:
            print(f"  [WARN] batch error: {e}")
        processed += len(batch)
        if processed % 300 == 0 or processed == len(rows):
            print(f"  INVOLVES: {processed}/{len(rows)}")
    print(f"  [OK] INVOLVES import complete")


def import_causal_models(driver):
    print("\n[Phase B-4] (:Concept)-[:CAUSES]->(:Concept)")
    rows = load_json("causal_models")
    if not rows:
        return

    query = """
    UNWIND $batch AS row
    MATCH (c1:Concept {id: row.cause_concept_id})
    MATCH (c2:Concept {id: row.effect_concept_id})
    MERGE (c1)-[r:CAUSES]->(c2)
    SET r.id = row.id,
        r.strength = row.strength,
        r.confidence = row.confidence,
        r.evidence_count = row.evidence_count,
        r.created_at = row.created_at
    """
    batch = [dict(r) for r in rows]
    try:
        run_batch(driver, query, batch, "CAUSES")
    except Exception as e:
        print(f"  [WARN] causal_models error: {e}")
    print(f"  [OK] CAUSES: {len(rows)} relations")


def _log_orphans(rel_type: str, ids: list):
    """고아 관계 로그 저장"""
    existing = {}
    if ORPHAN_LOG.exists():
        existing = json.loads(ORPHAN_LOG.read_text(encoding="utf-8"))
    existing[rel_type] = ids
    ORPHAN_LOG.write_text(json.dumps(existing, indent=2), encoding="utf-8")


# ── 벡터 인덱스 생성 ───────────────────────────────────────────────────────

def create_vector_indexes(driver):
    print("\n[Vector Indexes] Creating 1536-dim cosine indexes...")
    ddl_statements = [
        """CREATE VECTOR INDEX concept_embeddings IF NOT EXISTS
           FOR (n:Concept) ON n.embedding
           OPTIONS { indexConfig: { `vector.dimensions`: 1536, `vector.similarity_function`: 'cosine' }}""",
        """CREATE VECTOR INDEX experience_embeddings IF NOT EXISTS
           FOR (n:Experience) ON n.embedding
           OPTIONS { indexConfig: { `vector.dimensions`: 1536, `vector.similarity_function`: 'cosine' }}""",
        """CREATE VECTOR INDEX visual_embeddings IF NOT EXISTS
           FOR (n:VisualExperience) ON n.embedding
           OPTIONS { indexConfig: { `vector.dimensions`: 1536, `vector.similarity_function`: 'cosine' }}""",
    ]
    with driver.session() as session:
        for ddl in ddl_statements:
            session.run(ddl)
    print("  [OK] Vector indexes created (building in background...)")


# ── 메인 ────────────────────────────────────────────────────────────────────

def main():
    print("=== Neo4j Import Start ===")
    print(f"Source: {DATA_DIR}")
    print()

    driver = get_writer_driver()

    try:
        # Phase A: 노드
        import_brain_regions(driver)
        import_concepts(driver)
        import_experiences(driver)
        import_emotion_logs(driver)
        import_baby_state(driver)

        for table, label in [
            ("predictions",          "Prediction"),
            ("imagination_sessions", "Imagination"),
            ("procedural_patterns",  "Procedure"),
            ("memory_consolidation_logs", "SleepLog"),
            ("visual_experiences",   "VisualExperience"),
            ("pending_questions",    "PendingQuestion"),
            ("curiosity_queue",      "CuriosityLog"),
            ("autonomous_goals",     "AutonomousGoal"),
            ("ablation_runs",        "AblationRun"),
        ]:
            import_simple_nodes(driver, table, label)

        # Phase B: 관계
        import_concept_relations(driver)
        import_concept_brain_mapping(driver)
        import_experience_concepts(driver)
        import_causal_models(driver)

        # 벡터 인덱스 (데이터 임포트 후)
        create_vector_indexes(driver)

        print("\n=== Import Complete ===")
        print("Run validate_migration.py to verify data integrity")

    except Exception as e:
        print(f"\n[FAIL] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        driver.close()


if __name__ == "__main__":
    if not all([ENTRY_URI, USERNAME, PASSWORD, DB_NAME]):
        print("[FAIL] NEO4J_* env vars not set")
        sys.exit(1)
    main()
