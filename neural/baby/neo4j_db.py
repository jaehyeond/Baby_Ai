"""
Neo4j Database Client for Baby Brain
Phase 2: Supabase db.py → Neo4j 완전 대체

연결 패턴: 2-step writer lookup (검증된 패턴, import_to_neo4j.py와 동일)
  1. entry URI → system DB에서 writer 노드 주소 조회
  2. writer bolt+s:// 직접 연결 (AsyncGraphDatabase)

모든 메서드는 db.py BrainDatabase와 동일한 시그니처를 유지합니다.
"""

import os
import json
import asyncio
import logging
from typing import Optional, Any
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from neo4j import GraphDatabase
from neo4j import AsyncGraphDatabase
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ── 환경변수 ────────────────────────────────────────────────────────────────
_ENTRY_URI = os.getenv("NEO4J_URI")       # bolt+s://b76cbc85.databases.neo4j.io
_USERNAME  = os.getenv("NEO4J_USERNAME")
_PASSWORD  = os.getenv("NEO4J_PASSWORD")
_DB_NAME   = os.getenv("NEO4J_DATABASE")
_AUTH      = (_USERNAME, _PASSWORD)

# ── 싱글톤 ──────────────────────────────────────────────────────────────────
_writer_uri: Optional[str] = None
_async_driver = None


def _resolve_writer_uri_sync() -> str:
    """system DB에서 writer 노드 주소를 동기적으로 조회 (앱 시작 시 1회)"""
    with GraphDatabase.driver(_ENTRY_URI, auth=_AUTH) as d:
        res = d.execute_query(
            f'SHOW DATABASES YIELD name, address, writer '
            f'WHERE name = "{_DB_NAME}" AND writer = true',
            database_="system",
        )
    if not res.records:
        raise RuntimeError(f"Neo4j writer not found for database: {_DB_NAME}")
    writer_host = res.records[0]["address"].split(":")[0]
    return f"bolt+s://{writer_host}"


async def init_driver() -> None:
    """앱 lifespan 시작 시 호출: writer URI 확인 + Async driver 초기화"""
    global _writer_uri, _async_driver
    _writer_uri = _resolve_writer_uri_sync()
    _async_driver = AsyncGraphDatabase.driver(_writer_uri, auth=_AUTH)
    logger.info(f"Neo4j async driver initialized: {_writer_uri}")


async def close_driver() -> None:
    """앱 lifespan 종료 시 호출"""
    global _async_driver
    if _async_driver:
        await _async_driver.close()
        _async_driver = None


def get_driver():
    """현재 async driver 반환 (초기화 이후에만 호출)"""
    if _async_driver is None:
        raise RuntimeError("Neo4j driver not initialized. Call init_driver() first.")
    return _async_driver


# ── 헬퍼 ────────────────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _record_to_dict(record, key: str) -> dict:
    """Neo4j Record의 노드/관계를 dict로 변환"""
    node = record[key]
    return dict(node) if node is not None else {}


# ────────────────────────────────────────────────────────────────────────────
# BrainDatabase (Neo4j 버전)
# ────────────────────────────────────────────────────────────────────────────

class BrainDatabase:
    """
    Neo4j 기반 Baby Brain Database Operations

    db.py BrainDatabase와 동일한 public 인터페이스 유지.
    내부 구현만 Supabase REST → Cypher로 교체.
    """

    def __init__(self):
        pass

    @property
    def driver(self):
        return get_driver()

    # ==================== indexes (E2) ====================

    async def ensure_indexes(self) -> None:
        """E2 필요 인덱스 생성 (IF NOT EXISTS — 멱등)"""
        queries = [
            "CREATE INDEX exp_hour IF NOT EXISTS FOR (e:Experience) ON (e.hour_of_day)",
            "CREATE INDEX exp_speaker IF NOT EXISTS FOR (e:Experience) ON (e.speaker_id)",
            "CREATE INDEX exp_created IF NOT EXISTS FOR (e:Experience) ON (e.created_at)",
            "CREATE INDEX um_speaker IF NOT EXISTS FOR (um:UserModel) ON (um.speaker_id)",
            "CREATE INDEX tp_time_slot IF NOT EXISTS FOR (tp:TemporalPattern) ON (tp.time_slot)",
        ]
        async with self.driver.session(database=_DB_NAME) as s:
            for q in queries:
                await s.run(q)
        logger.info("E2 indexes ensured")

    # ==================== baby_state (싱글톤) ====================

    async def get_baby_state(self) -> Optional[dict]:
        """현재 baby_state 조회 (싱글톤)"""
        async with self.driver.session(database=_DB_NAME) as s:
            result = await s.run("MATCH (bs:BabyState) RETURN bs LIMIT 1")
            record = await result.single()
            if record:
                return dict(record["bs"])
            return None

    async def update_baby_state(self, **kwargs) -> dict:
        """baby_state 업데이트 (없으면 생성)"""
        state = await self.get_baby_state()
        props = {k: v for k, v in kwargs.items() if v is not None}
        props["updated_at"] = _now_iso()

        async with self.driver.session(database=_DB_NAME) as s:
            if state is None:
                # 초기 생성
                props.setdefault("id", "singleton")
                props.setdefault("created_at", _now_iso())
                result = await s.run(
                    "CREATE (bs:BabyState $props) RETURN bs",
                    props=props,
                )
            else:
                # 업데이트
                set_clause = ", ".join(f"bs.{k} = ${k}" for k in props)
                result = await s.run(
                    f"MATCH (bs:BabyState) SET {set_clause} RETURN bs",
                    **props,
                )
            record = await result.single()
            return dict(record["bs"]) if record else {}

    # ==================== experiences ====================

    async def insert_experience(
        self,
        task: str,
        task_type: str,
        output: str,
        success: bool,
        emotional_salience: float = 0.5,
        dominant_emotion: str = None,
        embedding: list[float] = None,
        emotion_snapshot: dict = None,
        development_stage: int = 0,
        tags: list[str] = None,
        extras: dict = None,
    ) -> dict:
        """경험 저장"""
        props = {
            "task": task,
            "task_type": task_type,
            "output": output,
            "success": success,
            "emotional_salience": emotional_salience,
            "development_stage": development_stage,
            "created_at": _now_iso(),
            "strength": emotional_salience,  # 초기 강도 = 감정 현저성
        }
        if dominant_emotion:
            props["dominant_emotion"] = dominant_emotion
        if embedding:
            props["embedding"] = embedding
        if emotion_snapshot:
            props["emotion_snapshot"] = json.dumps(emotion_snapshot)
        if tags:
            props["tags"] = tags
        if extras:
            props["extras"] = json.dumps(extras)

        async with self.driver.session(database=_DB_NAME) as s:
            result = await s.run(
                "CREATE (e:Experience {id: randomUUID()}) SET e += $props RETURN e",
                props=props,
            )
            record = await result.single()
            return dict(record["e"]) if record else {}

    async def search_similar_experiences(
        self,
        embedding: list[float],
        threshold: float = 0.7,
        limit: int = 5,
    ) -> list[dict]:
        """벡터 유사도로 경험 검색"""
        async with self.driver.session(database=_DB_NAME) as s:
            result = await s.run(
                "CALL db.index.vector.queryNodes('experience_embeddings', $limit, $emb) "
                "YIELD node, score "
                "WHERE score >= $threshold "
                "RETURN node, score",
                emb=embedding,
                limit=limit * 2,  # threshold 필터 후 limit 맞추기 위해 여유분
                threshold=threshold,
            )
            records = await result.fetch(limit)
            return [
                {**dict(r["node"]), "similarity": r["score"]}
                for r in records
            ]

    async def get_recent_experiences(self, limit: int = 10) -> list[dict]:
        """최근 경험 조회"""
        async with self.driver.session(database=_DB_NAME) as s:
            result = await s.run(
                "MATCH (e:Experience) "
                "RETURN e ORDER BY e.created_at DESC LIMIT $limit",
                limit=limit,
            )
            records = await result.fetch(limit)
            return [dict(r["e"]) for r in records]

    async def get_successful_experiences(
        self,
        task_type: str = None,
        limit: int = 5,
    ) -> list[dict]:
        """성공한 경험 조회"""
        if task_type:
            cypher = (
                "MATCH (e:Experience) WHERE e.success = true AND e.task_type = $task_type "
                "RETURN e ORDER BY e.emotional_salience DESC LIMIT $limit"
            )
        else:
            cypher = (
                "MATCH (e:Experience) WHERE e.success = true "
                "RETURN e ORDER BY e.emotional_salience DESC LIMIT $limit"
            )
        async with self.driver.session(database=_DB_NAME) as s:
            result = await s.run(cypher, task_type=task_type, limit=limit)
            records = await result.fetch(limit)
            return [dict(r["e"]) for r in records]

    async def reinforce_memory(self, experience_id: str) -> None:
        """기억 강화 (+0.1, 최대 1.0)"""
        async with self.driver.session(database=_DB_NAME) as s:
            await s.run(
                "MATCH (e:Experience {id: $id}) "
                "SET e.strength = CASE WHEN coalesce(e.strength, 0.5) + 0.1 > 1.0 THEN 1.0 "
                "                      ELSE coalesce(e.strength, 0.5) + 0.1 END, "
                "    e.last_accessed = $now",
                id=experience_id,
                now=_now_iso(),
            )

    async def boost_memory_by_emotion(
        self,
        experience_id: str,
        emotion_intensity: float,
    ) -> None:
        """감정 강도로 기억 강화"""
        boost = emotion_intensity * 0.1
        async with self.driver.session(database=_DB_NAME) as s:
            await s.run(
                "MATCH (e:Experience {id: $id}) "
                "SET e.strength = CASE WHEN coalesce(e.strength, 0.5) + $boost > 1.0 THEN 1.0 "
                "                      ELSE coalesce(e.strength, 0.5) + $boost END, "
                "    e.emotional_salience = CASE WHEN coalesce(e.emotional_salience, 0.5) + $boost * 0.5 > 1.0 THEN 1.0 "
                "                               ELSE coalesce(e.emotional_salience, 0.5) + $boost * 0.5 END",
                id=experience_id,
                boost=boost,
            )

    # ==================== semantic_concepts ====================

    async def insert_concept(
        self,
        name: str,
        category: str = None,
        description: str = None,
        embedding: list[float] = None,
        acquired_at_stage: int = 0,
    ) -> dict:
        """개념 저장 (MERGE - 이미 존재하면 업데이트)"""
        on_create_props = {
            "acquired_at_stage": acquired_at_stage,
            "strength": 0.5,
            "usage_count": 0,
            "created_at": _now_iso(),
        }
        if category:
            on_create_props["category"] = category
        if description:
            on_create_props["description"] = description
        if embedding:
            on_create_props["embedding"] = embedding

        async with self.driver.session(database=_DB_NAME) as s:
            result = await s.run(
                # ON CREATE: id를 randomUUID()로 설정 (props에는 없으므로 별도 SET)
                "MERGE (c:Concept {name: $name}) "
                "ON CREATE SET c += $props, c.id = randomUUID() "
                "ON MATCH SET c.usage_count = coalesce(c.usage_count, 0) + 1 "
                "RETURN c",
                name=name,
                props=on_create_props,
            )
            record = await result.single()
            return dict(record["c"]) if record else {}

    async def get_concept_by_name(self, name: str) -> Optional[dict]:
        """이름으로 개념 조회"""
        async with self.driver.session(database=_DB_NAME) as s:
            result = await s.run(
                "MATCH (c:Concept {name: $name}) RETURN c LIMIT 1",
                name=name,
            )
            record = await result.single()
            return dict(record["c"]) if record else None

    async def update_concept_strength(self, concept_id: str, delta: float = 0.1) -> None:
        """개념 강도 업데이트"""
        async with self.driver.session(database=_DB_NAME) as s:
            await s.run(
                "MATCH (c:Concept {id: $id}) "
                "SET c.strength = CASE WHEN coalesce(c.strength, 0.5) + $delta > 1.0 THEN 1.0 "
                "                      ELSE coalesce(c.strength, 0.5) + $delta END, "
                "    c.usage_count = coalesce(c.usage_count, 0) + 1",
                id=concept_id,
                delta=delta,
            )

    async def link_experience_concept(
        self,
        experience_id: str,
        concept_id: str,
        confidence: float = 0.5,
    ) -> None:
        """경험-개념 연결 (Hebb's Law: INVOLVES 관계 강도 증가)"""
        boost = confidence * 0.2
        async with self.driver.session(database=_DB_NAME) as s:
            await s.run(
                "MATCH (e:Experience {id: $exp_id}), (c:Concept {id: $con_id}) "
                "MERGE (e)-[r:INVOLVES]->(c) "
                "ON CREATE SET r.relevance = $conf, r.created_at = $now "
                "ON MATCH SET r.relevance = CASE WHEN r.relevance + $boost > 1.0 THEN 1.0 "
                "                                ELSE r.relevance + $boost END",
                exp_id=experience_id,
                con_id=concept_id,
                conf=confidence,
                boost=boost,
                now=_now_iso(),
            )

    async def get_associated_concepts(
        self,
        experience_id: str,
        min_confidence: float = 0.3,
        limit: int = 10,
    ) -> list[dict]:
        """경험에 연관된 개념 조회"""
        async with self.driver.session(database=_DB_NAME) as s:
            result = await s.run(
                "MATCH (e:Experience {id: $id})-[r:INVOLVES]->(c:Concept) "
                "WHERE r.relevance >= $min_conf "
                "RETURN c, r.relevance AS relevance "
                "ORDER BY relevance DESC LIMIT $limit",
                id=experience_id,
                min_conf=min_confidence,
                limit=limit,
            )
            records = await result.fetch(limit)
            return [{**dict(r["c"]), "relevance": r["relevance"]} for r in records]

    async def get_all_concepts(self) -> list[dict]:
        """모든 개념 조회 (strength 내림차순)"""
        async with self.driver.session(database=_DB_NAME) as s:
            result = await s.run(
                "MATCH (c:Concept) RETURN c ORDER BY c.strength DESC"
            )
            records = await result.fetch(10000)
            return [dict(r["c"]) for r in records]

    async def search_similar_concepts(
        self,
        embedding: list[float],
        limit: int = 10,
    ) -> list[dict]:
        """벡터 유사도로 개념 검색 (Memory Recall용)"""
        async with self.driver.session(database=_DB_NAME) as s:
            result = await s.run(
                "CALL db.index.vector.queryNodes('concept_embeddings', $limit, $emb) "
                "YIELD node, score "
                "RETURN node, score",
                emb=embedding,
                limit=limit,
            )
            records = await result.fetch(limit)
            return [
                {**dict(r["node"]), "similarity": r["score"]}
                for r in records
            ]

    async def get_experience_concept_links(self, limit: int = 100) -> list[dict]:
        """경험-개념 연결 조회 (시냅스 시각화용)"""
        async with self.driver.session(database=_DB_NAME) as s:
            result = await s.run(
                "MATCH (e:Experience)-[r:INVOLVES]->(c:Concept) "
                "RETURN e.id AS experience_id, c.id AS concept_id, r.relevance AS relevance "
                "ORDER BY r.relevance DESC LIMIT $limit",
                limit=limit,
            )
            records = await result.fetch(limit)
            return [dict(r) for r in records]

    # ==================== procedural_patterns ====================

    async def upsert_pattern(
        self,
        task_type: str,
        approach: str,
        success: bool,
    ) -> dict:
        """절차 패턴 저장/업데이트"""
        async with self.driver.session(database=_DB_NAME) as s:
            result = await s.run(
                "MERGE (p:Procedure {task_type: $task_type, approach: $approach}) "
                "ON CREATE SET "
                "  p.id = randomUUID(), "
                "  p.success_count = $sc, "
                "  p.failure_count = $fc, "
                "  p.total_uses = 1, "
                "  p.created_at = $now, "
                "  p.last_used = $now "
                "ON MATCH SET "
                "  p.total_uses = p.total_uses + 1, "
                "  p.success_count = p.success_count + $sc, "
                "  p.failure_count = p.failure_count + $fc, "
                "  p.last_used = $now "
                "RETURN p",
                task_type=task_type,
                approach=approach,
                sc=1 if success else 0,
                fc=0 if success else 1,
                now=_now_iso(),
            )
            record = await result.single()
            return dict(record["p"]) if record else {}

    async def get_best_patterns(
        self,
        task_type: str,
        min_uses: int = 3,
        limit: int = 5,
    ) -> list[dict]:
        """최고 성공률 패턴 조회"""
        async with self.driver.session(database=_DB_NAME) as s:
            result = await s.run(
                "MATCH (p:Procedure {task_type: $task_type}) "
                "WHERE p.total_uses >= $min_uses "
                "WITH p, toFloat(p.success_count) / p.total_uses AS success_rate "
                "RETURN p, success_rate "
                "ORDER BY success_rate DESC LIMIT $limit",
                task_type=task_type,
                min_uses=min_uses,
                limit=limit,
            )
            records = await result.fetch(limit)
            return [{**dict(r["p"]), "success_rate": r["success_rate"]} for r in records]

    async def record_learning_event(
        self,
        pattern_id: str,
        experience_id: str,
        outcome: str,
        reward_signal: float = 0.0,
        prediction_error: float = 0.0,
    ) -> None:
        """학습 이벤트 기록 (Neo4j에는 별도 노드 없음, 로그만)"""
        logger.info(
            f"[LearningEvent] pattern={pattern_id} exp={experience_id} "
            f"outcome={outcome} reward={reward_signal:.3f} pe={prediction_error:.3f}"
        )

    # ==================== emotion_logs ====================

    async def log_emotion(
        self,
        curiosity: float,
        joy: float,
        fear: float,
        surprise: float,
        frustration: float,
        boredom: float,
        dominant_emotion: str,
        trigger_task: str = None,
        trigger_type: str = None,
        experience_id: str = None,
        development_stage: int = 0,
    ) -> dict:
        """감정 로그 저장"""
        props = {
            "curiosity": curiosity,
            "joy": joy,
            "fear": fear,
            "surprise": surprise,
            "frustration": frustration,
            "boredom": boredom,
            "dominant_emotion": dominant_emotion,
            "development_stage": development_stage,
            "created_at": _now_iso(),
        }
        if trigger_task:
            props["trigger_task"] = trigger_task
        if trigger_type:
            props["trigger_type"] = trigger_type
        if experience_id:
            props["experience_id"] = experience_id

        async with self.driver.session(database=_DB_NAME) as s:
            result = await s.run(
                "CREATE (el:EmotionLog {id: randomUUID()}) SET el += $props RETURN el",
                props=props,
            )
            record = await result.single()
            return dict(record["el"]) if record else {}

    # ==================== predictions ====================

    async def insert_prediction(
        self,
        scenario: str,
        prediction: str,
        confidence: float = 0.5,
        reasoning: str = None,
        based_on_concepts: list[str] = None,
        based_on_experiences: list[str] = None,
        prediction_type: str = "outcome",
        domain: str = None,
        development_stage: int = 0,
    ) -> dict:
        """예측 저장"""
        props = {
            "scenario": scenario,
            "prediction": prediction,
            "confidence": confidence,
            "prediction_type": prediction_type,
            "development_stage": development_stage,
            "created_at": _now_iso(),
        }
        if reasoning:
            props["reasoning"] = reasoning
        if domain:
            props["domain"] = domain
        # UUID 배열은 문자열로 직렬화
        if based_on_concepts:
            valid = [c for c in based_on_concepts if len(c) == 36 and c.count("-") == 4]
            if valid:
                props["based_on_concepts"] = valid
        if based_on_experiences:
            valid = [e for e in based_on_experiences if len(e) == 36 and e.count("-") == 4]
            if valid:
                props["based_on_experiences"] = valid

        async with self.driver.session(database=_DB_NAME) as s:
            result = await s.run(
                "CREATE (p:Prediction {id: randomUUID()}) SET p += $props RETURN p",
                props=props,
            )
            record = await result.single()
            return dict(record["p"]) if record else {}

    async def verify_prediction(
        self,
        prediction_id: str,
        actual_outcome: str,
        was_correct: bool,
        prediction_error: float = 0.0,
        insight_gained: str = None,
    ) -> dict:
        """예측 검증 결과 업데이트"""
        props: dict[str, Any] = {
            "actual_outcome": actual_outcome,
            "was_correct": was_correct,
            "prediction_error": prediction_error,
            "verified_at": _now_iso(),
        }
        if insight_gained:
            props["insight_gained"] = insight_gained

        set_clause = ", ".join(f"p.{k} = ${k}" for k in props)
        async with self.driver.session(database=_DB_NAME) as s:
            result = await s.run(
                f"MATCH (p:Prediction {{id: $id}}) SET {set_clause} RETURN p",
                id=prediction_id,
                **props,
            )
            record = await result.single()
            return dict(record["p"]) if record else {}

    async def get_recent_predictions(self, limit: int = 10) -> list[dict]:
        """최근 예측 조회"""
        async with self.driver.session(database=_DB_NAME) as s:
            result = await s.run(
                "MATCH (p:Prediction) RETURN p ORDER BY p.created_at DESC LIMIT $limit",
                limit=limit,
            )
            records = await result.fetch(limit)
            return [dict(r["p"]) for r in records]

    async def get_unverified_predictions(self, limit: int = 10) -> list[dict]:
        """미검증 예측 조회"""
        async with self.driver.session(database=_DB_NAME) as s:
            result = await s.run(
                "MATCH (p:Prediction) WHERE p.verified_at IS NULL "
                "RETURN p ORDER BY p.created_at DESC LIMIT $limit",
                limit=limit,
            )
            records = await result.fetch(limit)
            return [dict(r["p"]) for r in records]

    # ==================== imagination_sessions (+ simulations 통합) ====================

    async def start_imagination_session(
        self,
        topic: str,
        trigger: str = None,
        imagination_type: str = "exploration",
        curiosity_level: float = 0.5,
        emotional_state: dict = None,
        development_stage: int = 0,
    ) -> dict:
        """상상 세션 시작"""
        props = {
            "topic": topic,
            "imagination_type": imagination_type,
            "curiosity_level": curiosity_level,
            "development_stage": development_stage,
            "started_at": _now_iso(),
            "thoughts": "[]",
            "visualizations": "[]",
            "insights": "[]",
        }
        if trigger:
            props["trigger"] = trigger
        if emotional_state:
            props["emotional_state"] = json.dumps(emotional_state)

        async with self.driver.session(database=_DB_NAME) as s:
            result = await s.run(
                "CREATE (im:Imagination {id: randomUUID()}) SET im += $props RETURN im",
                props=props,
            )
            record = await result.single()
            return dict(record["im"]) if record else {}

    async def insert_simulation(
        self,
        initial_state: dict,
        target_goal: str = None,
        simulation_type: str = "planning",
        steps: list[dict] = None,
        predicted_outcome: dict = None,
        success_probability: float = 0.5,
        complexity_level: int = 1,
        triggered_by_experience: str = None,
        development_stage: int = 0,
    ) -> dict:
        """시뮬레이션 저장 → Imagination 노드로 통합"""
        return await self.start_imagination_session(
            topic=target_goal or "simulation",
            imagination_type=simulation_type,
            curiosity_level=success_probability,
            emotional_state={"initial_state": initial_state, "steps": steps or []},
            development_stage=development_stage,
        )

    async def add_imagination_thought(
        self,
        session_id: str,
        thought: dict,
    ) -> dict:
        """상상 세션에 생각 추가"""
        async with self.driver.session(database=_DB_NAME) as s:
            # 현재 thoughts 조회
            result = await s.run(
                "MATCH (im:Imagination {id: $id}) RETURN im.thoughts AS thoughts",
                id=session_id,
            )
            record = await result.single()
            if not record:
                return {}

            thoughts_raw = record["thoughts"] or "[]"
            thoughts = json.loads(thoughts_raw) if isinstance(thoughts_raw, str) else list(thoughts_raw)
            thoughts.append(thought)

            result2 = await s.run(
                "MATCH (im:Imagination {id: $id}) SET im.thoughts = $thoughts RETURN im",
                id=session_id,
                thoughts=json.dumps(thoughts),
            )
            record2 = await result2.single()
            return dict(record2["im"]) if record2 else {}

    async def end_imagination_session(
        self,
        session_id: str,
        insights: list[str] = None,
        predictions_made: list[str] = None,
        simulations_run: list[str] = None,
        duration_ms: int = None,
    ) -> dict:
        """상상 세션 종료"""
        props: dict[str, Any] = {"ended_at": _now_iso()}
        if insights:
            props["insights"] = json.dumps(insights)
        if predictions_made:
            props["predictions_made"] = json.dumps(predictions_made)
        if simulations_run:
            props["simulations_run"] = json.dumps(simulations_run)
        if duration_ms is not None:
            props["duration_ms"] = duration_ms

        set_clause = ", ".join(f"im.{k} = ${k}" for k in props)
        async with self.driver.session(database=_DB_NAME) as s:
            result = await s.run(
                f"MATCH (im:Imagination {{id: $id}}) SET {set_clause} RETURN im",
                id=session_id,
                **props,
            )
            record = await result.single()
            return dict(record["im"]) if record else {}

    async def complete_simulation(
        self,
        simulation_id: str,
        actual_outcome: dict = None,
        was_validated: bool = False,
        accuracy_score: float = None,
    ) -> dict:
        """시뮬레이션 완료 → Imagination 세션 종료로 통합"""
        return await self.end_imagination_session(
            session_id=simulation_id,
            insights=[json.dumps(actual_outcome)] if actual_outcome else None,
        )

    async def get_active_imagination_session(self) -> Optional[dict]:
        """활성 상상 세션 조회"""
        async with self.driver.session(database=_DB_NAME) as s:
            result = await s.run(
                "MATCH (im:Imagination) WHERE im.ended_at IS NULL "
                "RETURN im ORDER BY im.started_at DESC LIMIT 1"
            )
            record = await result.single()
            return dict(record["im"]) if record else None

    async def get_recent_imagination_sessions(self, limit: int = 10) -> list[dict]:
        """최근 상상 세션 조회"""
        async with self.driver.session(database=_DB_NAME) as s:
            result = await s.run(
                "MATCH (im:Imagination) RETURN im ORDER BY im.started_at DESC LIMIT $limit",
                limit=limit,
            )
            records = await result.fetch(limit)
            return [dict(r["im"]) for r in records]

    async def get_recent_simulations(self, limit: int = 10) -> list[dict]:
        """최근 시뮬레이션 조회 → Imagination과 통합"""
        return await self.get_recent_imagination_sessions(limit=limit)

    # ==================== causal_models ====================

    async def upsert_causal_model(
        self,
        cause_concept_id: str,
        effect_concept_id: str,
        relationship_type: str = "causes",
        causal_strength: float = 0.5,
        confidence: float = 0.5,
        domain: str = None,
        discovered_at_stage: int = 0,
    ) -> dict:
        """인과 모델 저장/업데이트 (CAUSES 관계 강도 증가)"""
        async with self.driver.session(database=_DB_NAME) as s:
            result = await s.run(
                "MATCH (cause:Concept {id: $cause_id}), (effect:Concept {id: $effect_id}) "
                "MERGE (cause)-[r:CAUSES]->(effect) "
                "ON CREATE SET "
                "  r.causal_strength = $strength, "
                "  r.confidence = $conf, "
                "  r.evidence_count = 1, "
                "  r.relationship_type = $rel_type, "
                "  r.discovered_at_stage = $stage, "
                "  r.created_at = $now "
                "ON MATCH SET "
                "  r.causal_strength = CASE WHEN r.causal_strength + 0.05 > 1.0 THEN 1.0 ELSE r.causal_strength + 0.05 END, "
                "  r.confidence = CASE WHEN r.confidence + 0.02 > 1.0 THEN 1.0 ELSE r.confidence + 0.02 END, "
                "  r.evidence_count = r.evidence_count + 1, "
                "  r.validation_count = coalesce(r.validation_count, 0) + 1 "
                "RETURN cause, r, effect",
                cause_id=cause_concept_id,
                effect_id=effect_concept_id,
                strength=causal_strength,
                conf=confidence,
                rel_type=relationship_type,
                stage=discovered_at_stage,
                now=_now_iso(),
            )
            record = await result.single()
            if not record:
                return {}
            return {
                "cause_concept_id": cause_concept_id,
                "effect_concept_id": effect_concept_id,
                **dict(record["r"]),
            }

    async def get_causal_models(self, min_confidence: float = 0.3, limit: int = 50) -> list[dict]:
        """인과 모델 조회"""
        async with self.driver.session(database=_DB_NAME) as s:
            result = await s.run(
                "MATCH (cause:Concept)-[r:CAUSES]->(effect:Concept) "
                "WHERE r.confidence >= $min_conf "
                "RETURN cause.id AS cause_id, cause.name AS cause_name, "
                "       effect.id AS effect_id, effect.name AS effect_name, "
                "       r.causal_strength AS causal_strength, r.confidence AS confidence "
                "ORDER BY r.causal_strength DESC LIMIT $limit",
                min_conf=min_confidence,
                limit=limit,
            )
            records = await result.fetch(limit)
            return [dict(r) for r in records]

    # ==================== Utility ====================

    async def decay_connections(self, decay_rate: float = 0.01) -> None:
        """모든 RELATES_TO 관계 강도 감쇠 (시간 기반 망각)"""
        async with self.driver.session(database=_DB_NAME) as s:
            await s.run(
                "MATCH ()-[r:RELATES_TO]->() "
                "SET r.strength = r.strength * (1.0 - $rate)",
                rate=decay_rate,
            )
            # Experience 강도도 감쇠
            await s.run(
                "MATCH (e:Experience) "
                "WHERE e.last_accessed < $cutoff OR e.last_accessed IS NULL "
                "SET e.strength = CASE WHEN coalesce(e.strength, 0.5) - $rate < 0.0 THEN 0.0 "
                "                      ELSE coalesce(e.strength, 0.5) - $rate END",
                rate=decay_rate,
                cutoff=_now_iso(),  # 실제 운영 시 cutoff 계산 필요
            )

    async def get_stats(self) -> dict:
        """전체 DB 통계"""
        async with self.driver.session(database=_DB_NAME) as s:
            result = await s.run(
                "MATCH (e:Experience) WITH count(e) AS exp_count "
                "MATCH (c:Concept) WITH exp_count, count(c) AS con_count "
                "MATCH (p:Procedure) WITH exp_count, con_count, count(p) AS pat_count "
                "RETURN exp_count, con_count, pat_count"
            )
            record = await result.single()
            if record:
                return {
                    "experiences_count": record["exp_count"],
                    "concepts_count": record["con_count"],
                    "patterns_count": record["pat_count"],
                }
            return {"experiences_count": 0, "concepts_count": 0, "patterns_count": 0}

    # ==================== 확장: Memory Recall (Phase 2 신규) ====================

    async def search_similar_concepts_with_regions(
        self,
        embedding: list[float],
        limit: int = 10,
    ) -> list[dict]:
        """벡터 검색 + 뇌 영역 조인 (Memory Recall Pipeline용)"""
        async with self.driver.session(database=_DB_NAME) as s:
            result = await s.run(
                "CALL db.index.vector.queryNodes('concept_embeddings', $limit, $emb) "
                "YIELD node AS concept, score "
                "OPTIONAL MATCH (concept)-[:MAPPED_TO]->(br:BrainRegion) "
                "RETURN concept, score, br.name AS region "
                "ORDER BY score DESC",
                emb=embedding,
                limit=limit,
            )
            records = await result.fetch(limit)
            return [
                {**dict(r["concept"]), "similarity": r["score"], "brain_region": r["region"]}
                for r in records
            ]

    async def get_spreading_activation(
        self,
        concept_ids: list[str],
        depth: int = 2,
        limit: int = 20,
    ) -> list[dict]:
        """Spreading Activation: 개념 ID 목록에서 RELATES_TO*1..depth 탐색

        MAPPED_TO 조인으로 brain_region_id 포함 반환.
        LIMIT 이후 OPTIONAL MATCH로 Cartesian product 방지.
        """
        # depth를 Cypher 리터럴로 삽입 (Neo4j는 가변 길이 경로 상한을 파라미터로 받을 수 없음)
        safe_depth = max(1, min(int(depth), 5))  # 1~5 범위 제한
        async with self.driver.session(database=_DB_NAME) as s:
            result = await s.run(
                "UNWIND $ids AS start_id "
                f"MATCH (start:Concept {{id: start_id}})-[r:RELATES_TO*1..{safe_depth}]->(related:Concept) "
                "WHERE NOT related.id IN $ids "
                "WITH related, reduce(s = 0.0, rel IN r | s + coalesce(rel.strength, 0.5)) / size(r) AS avg_strength "
                "ORDER BY avg_strength DESC LIMIT $limit "
                "OPTIONAL MATCH (related)-[:MAPPED_TO]->(br:BrainRegion) "
                "RETURN related, avg_strength, br.id AS brain_region_id",
                ids=concept_ids,
                limit=limit,
            )
            records = await result.fetch(limit)
            return [
                {
                    **dict(r["related"]),
                    "activation_strength": r["avg_strength"],
                    "brain_region_id": r["brain_region_id"],
                }
                for r in records
            ]

    # ==================== Hebbian Learning ====================

    async def hebbian_update(
        self,
        concept_pairs: list[tuple[str, str]],
        strength_delta: float = 0.05,
    ) -> int:
        """Hebbian Learning: 함께 활성화된 개념 쌍의 RELATES_TO 강화/생성

        - ON CREATE: strength=delta, hebb_strength=delta (새 시냅스)
        - ON MATCH: strength += delta (cap 1.0), hebb_strength += delta (cap 1.0)
        - canonical ordering (min,max) 으로 방향성 중복 방지
        """
        if not concept_pairs:
            return 0
        unique_pairs = list({
            (min(a, b), max(a, b)) for a, b in concept_pairs if a != b
        })
        if not unique_pairs:
            return 0
        pairs_list = [list(p) for p in unique_pairs]
        async with self.driver.session(database=_DB_NAME) as s:
            result = await s.run(
                "UNWIND $pairs AS pair "
                "MATCH (a:Concept {id: pair[0]}), (b:Concept {id: pair[1]}) "
                "MERGE (a)-[r:RELATES_TO]->(b) "
                "ON CREATE SET r.strength = $delta, r.hebb_strength = $delta, "
                "  r.source = 'hebbian', r.created_at = $now "
                "ON MATCH SET "
                "  r.strength = CASE WHEN coalesce(r.strength, 0.5) + $delta > 1.0 "
                "    THEN 1.0 ELSE coalesce(r.strength, 0.5) + $delta END, "
                "  r.hebb_strength = CASE WHEN coalesce(r.hebb_strength, 0) + $delta > 1.0 "
                "    THEN 1.0 ELSE coalesce(r.hebb_strength, 0) + $delta END "
                "RETURN count(r) AS updated",
                pairs=pairs_list,
                delta=strength_delta,
                now=_now_iso(),
            )
            record = await result.single()
            return record["updated"] if record else 0

    async def get_hebb_stats(self) -> dict:
        """Hebbian 학습 통계"""
        async with self.driver.session(database=_DB_NAME) as s:
            result = await s.run(
                "MATCH ()-[r:RELATES_TO]->() "
                "WHERE r.hebb_strength IS NOT NULL AND r.hebb_strength > 0 "
                "RETURN count(r) AS hebb_count, "
                "  avg(r.hebb_strength) AS avg_hebb, "
                "  max(r.hebb_strength) AS max_hebb"
            )
            record = await result.single()
            result2 = await s.run(
                "MATCH ()-[r:RELATES_TO]->() RETURN count(r) AS total"
            )
            rec2 = await result2.single()
        return {
            "total_relates_to": rec2["total"] if rec2 else 0,
            "hebbian_count": record["hebb_count"] if record else 0,
            "avg_hebb_strength": round(float(record["avg_hebb"] or 0), 4) if record else 0,
            "max_hebb_strength": round(float(record["max_hebb"] or 0), 4) if record else 0,
        }

    async def get_brain_regions(self) -> list[dict]:
        """뇌 영역 목록 조회"""
        async with self.driver.session(database=_DB_NAME) as s:
            result = await s.run("MATCH (br:BrainRegion) RETURN br ORDER BY br.name")
            records = await result.fetch(100)
            return [dict(r["br"]) for r in records]

    async def cleanup_old_activations(self, max_age_seconds: int = 30) -> int:
        """오래된 Activation 노드 정리 (AuraDB Free TTL 미지원 대체)"""
        async with self.driver.session(database=_DB_NAME) as s:
            result = await s.run(
                "MATCH (a:Activation) "
                "WHERE a.created_at < datetime() - duration({seconds: $age}) "
                "WITH a, count(a) AS n "
                "DELETE a "
                "RETURN n",
                age=max_age_seconds,
            )
            record = await result.single()
            return record["n"] if record else 0

    # ==================== User Model (E2-3: Theory of Mind) ====================

    async def get_or_create_user_model(
        self,
        speaker_id: str,
        speaker_name: str = None,
        relationship: str = "unknown",
    ) -> dict:
        """UserModel MERGE — 없으면 생성, 있으면 interaction_count 증가"""
        async with self.driver.session(database=_DB_NAME) as s:
            result = await s.run(
                "MERGE (u:UserModel {speaker_id: $sid}) "
                "ON CREATE SET "
                "  u.id = randomUUID(), "
                "  u.name = $name, "
                "  u.relationship = $rel, "
                "  u.inferred_communication_style = 'neutral', "
                "  u.avg_emotion_toward_baby = 'neutral', "
                "  u.recent_emotion = 'neutral', "
                "  u.interaction_count = 1, "
                "  u.first_interaction = $now, "
                "  u.last_interaction = $now, "
                "  u.created_at = $now, "
                "  u.development_stage = $stage "
                "ON MATCH SET "
                "  u.interaction_count = u.interaction_count + 1, "
                "  u.last_interaction = $now, "
                "  u.name = CASE WHEN $name IS NOT NULL THEN $name ELSE u.name END "
                "RETURN u",
                sid=speaker_id,
                name=speaker_name,
                rel=relationship,
                now=_now_iso(),
                stage=0,
            )
            record = await result.single()
            return dict(record["u"]) if record else {}

    async def link_experience_user(
        self,
        experience_id: str,
        user_model_id: str,
        inferred_emotion: str = "neutral",
        inferred_intent: str = "neutral",
    ) -> None:
        """Experience -[:INTERACTED_WITH]-> UserModel 관계 MERGE (중복 방지)"""
        async with self.driver.session(database=_DB_NAME) as s:
            await s.run(
                "MATCH (e:Experience {id: $eid}), (u:UserModel {id: $uid}) "
                "MERGE (e)-[r:INTERACTED_WITH]->(u) "
                "ON CREATE SET "
                "  r.inferred_user_emotion = $emotion, "
                "  r.inferred_user_intent = $intent, "
                "  r.created_at = $now "
                "ON MATCH SET "
                "  r.inferred_user_emotion = $emotion, "
                "  r.inferred_user_intent = $intent",
                eid=experience_id,
                uid=user_model_id,
                emotion=inferred_emotion,
                intent=inferred_intent,
                now=_now_iso(),
            )

    async def update_user_interests(
        self,
        user_model_id: str,
        concept_ids: list[str],
    ) -> int:
        """UserModel -[:INTERESTED_IN]-> Concept 관계 MERGE (mention_count 증가)"""
        if not concept_ids:
            return 0
        async with self.driver.session(database=_DB_NAME) as s:
            result = await s.run(
                "UNWIND $cids AS cid "
                "MATCH (u:UserModel {id: $uid}), (c:Concept {id: cid}) "
                "MERGE (u)-[r:INTERESTED_IN]->(c) "
                "ON CREATE SET r.mention_count = 1, r.strength = 0.3, r.last_mentioned = $now "
                "ON MATCH SET "
                "  r.mention_count = r.mention_count + 1, "
                "  r.strength = CASE WHEN r.strength + 0.1 > 1.0 THEN 1.0 "
                "    ELSE r.strength + 0.1 END, "
                "  r.last_mentioned = $now "
                "RETURN count(r) AS updated",
                uid=user_model_id,
                cids=concept_ids,
                now=_now_iso(),
            )
            record = await result.single()
            return record["updated"] if record else 0

    async def get_user_context(
        self,
        speaker_id: str,
    ) -> Optional[dict]:
        """UserModel + 최근 관심사 + 통계 조회 (system prompt 구성용)"""
        async with self.driver.session(database=_DB_NAME) as s:
            result = await s.run(
                "MATCH (u:UserModel {speaker_id: $sid}) "
                "OPTIONAL MATCH (u)-[r:INTERESTED_IN]->(c:Concept) "
                "WITH u, c, r ORDER BY r.strength DESC LIMIT 10 "
                "RETURN u, collect(CASE WHEN c IS NOT NULL "
                "  THEN {name: c.name, strength: r.strength} ELSE null END) AS interests",
                sid=speaker_id,
            )
            record = await result.single()
            if not record:
                return None
            u = dict(record["u"])
            interests = [i for i in record["interests"] if i is not None]
            return {
                "id": u.get("id"),
                "name": u.get("name"),
                "speaker_id": u.get("speaker_id"),
                "relationship": u.get("relationship", "unknown"),
                "recent_emotion": u.get("recent_emotion", "neutral"),
                "interaction_count": u.get("interaction_count", 0),
                "interests": interests,
            }

    # ==================== Temporal Pattern (E2-2) ====================

    async def detect_temporal_patterns(
        self,
        development_stage: int = 0,
    ) -> list[dict]:
        """시간대별 반복 개념 조합 탐지. 수면 모드에서 배치 실행.

        조건: 같은 time_slot에서 같은 개념이 3회+ 등장, 2일+ 분포
        """
        async with self.driver.session(database=_DB_NAME) as s:
            # 1) 시간대별 반복 개념 탐지
            result = await s.run(
                "MATCH (e:Experience)-[:INVOLVES]->(c:Concept) "
                "WHERE e.task_type = 'conversation' "
                "  AND e.extras IS NOT NULL "
                "WITH e, c, "
                "  CASE "
                "    WHEN e.extras.hour_of_day >= 6 AND e.extras.hour_of_day < 12 THEN 'morning' "
                "    WHEN e.extras.hour_of_day >= 12 AND e.extras.hour_of_day < 17 THEN 'afternoon' "
                "    WHEN e.extras.hour_of_day >= 17 AND e.extras.hour_of_day < 21 THEN 'evening' "
                "    ELSE 'night' "
                "  END AS time_slot "
                "WITH time_slot, c.name AS concept_name, c.id AS concept_id, "
                "  count(DISTINCT e) AS occurrence_count, "
                "  collect(DISTINCT date(datetime(e.created_at))) AS dates "
                "WHERE occurrence_count >= 3 AND size(dates) >= 2 "
                "RETURN time_slot, concept_name, concept_id, occurrence_count, "
                "  size(dates) AS unique_days "
                "ORDER BY occurrence_count DESC "
                "LIMIT 20"
            )
            rows = await result.fetch(20)

            # 2) 각 결과에 대해 TemporalPattern MERGE + PATTERN_INVOLVES
            patterns = []
            for row in rows:
                slot = row["time_slot"]
                cname = row["concept_name"]
                cid = row["concept_id"]
                count_val = row["occurrence_count"]
                days = row["unique_days"]
                confidence = round(min(1.0, count_val / 10.0), 3)
                pattern_name = f"{slot}_{cname}"

                r2 = await s.run(
                    "MERGE (tp:TemporalPattern {name: $name, time_slot: $slot}) "
                    "ON CREATE SET "
                    "  tp.id = randomUUID(), "
                    "  tp.pattern_type = 'routine', "
                    "  tp.occurrence_count = $count, "
                    "  tp.confidence = $conf, "
                    "  tp.created_at = datetime(), "
                    "  tp.development_stage = $stage "
                    "ON MATCH SET "
                    "  tp.occurrence_count = $count, "
                    "  tp.confidence = $conf, "
                    "  tp.last_occurred = datetime() "
                    "WITH tp "
                    "MATCH (c:Concept {id: $cid}) "
                    "MERGE (tp)-[r:PATTERN_INVOLVES]->(c) "
                    "SET r.frequency = $freq "
                    "RETURN tp",
                    name=pattern_name,
                    slot=slot,
                    count=count_val,
                    conf=confidence,
                    stage=development_stage,
                    cid=cid,
                    freq=round(count_val / max(days, 1), 2),
                )
                rec = await r2.single()
                if rec:
                    tp_data = dict(rec["tp"])
                    patterns.append(tp_data)
                    # EXHIBITS_PATTERN: 관련 Experience → TemporalPattern
                    await s.run(
                        "MATCH (tp:TemporalPattern {name: $name, time_slot: $slot}) "
                        "MATCH (e:Experience)-[:INVOLVES]->(c:Concept {id: $cid}) "
                        "WHERE e.task_type = 'conversation' AND e.extras IS NOT NULL "
                        "  AND CASE "
                        "    WHEN e.extras.hour_of_day >= 6 AND e.extras.hour_of_day < 12 THEN 'morning' "
                        "    WHEN e.extras.hour_of_day >= 12 AND e.extras.hour_of_day < 17 THEN 'afternoon' "
                        "    WHEN e.extras.hour_of_day >= 17 AND e.extras.hour_of_day < 21 THEN 'evening' "
                        "    ELSE 'night' "
                        "  END = $slot "
                        "MERGE (e)-[r:EXHIBITS_PATTERN]->(tp) "
                        "ON CREATE SET r.created_at = datetime()",
                        name=pattern_name,
                        slot=slot,
                        cid=cid,
                    )

            logger.info(f"Temporal patterns detected: {len(patterns)}")
            return patterns

    async def check_temporal_expectations(
        self,
        current_hour: int,
    ) -> list[dict]:
        """현재 시간대 예상 패턴 조회"""
        time_slot = (
            "morning" if 6 <= current_hour < 12 else
            "afternoon" if 12 <= current_hour < 17 else
            "evening" if 17 <= current_hour < 21 else
            "night"
        )
        async with self.driver.session(database=_DB_NAME) as s:
            result = await s.run(
                "MATCH (tp:TemporalPattern {time_slot: $slot}) "
                "WHERE tp.confidence > 0.3 "
                "RETURN tp ORDER BY tp.confidence DESC LIMIT 5",
                slot=time_slot,
            )
            records = await result.fetch(5)
            return [dict(r["tp"]) for r in records]

    async def compute_transition_probabilities(self) -> int:
        """같은 날 연속 대화의 패턴 전이 확률 계산 → FOLLOWED_BY 관계 MERGE"""
        async with self.driver.session(database=_DB_NAME) as s:
            result = await s.run(
                "MATCH (tp1:TemporalPattern)-[:PATTERN_INVOLVES]->(c1:Concept) "
                "  <-[:INVOLVES]-(e1:Experience) "
                "MATCH (e2:Experience)-[:INVOLVES]->(c2:Concept) "
                "  <-[:PATTERN_INVOLVES]-(tp2:TemporalPattern) "
                "WHERE tp1.id <> tp2.id "
                "  AND date(datetime(e1.created_at)) = date(datetime(e2.created_at)) "
                "  AND datetime(e2.created_at) > datetime(e1.created_at) "
                "  AND duration.between(datetime(e1.created_at), datetime(e2.created_at)).minutes <= 60 "
                "WITH tp1, tp2, count(*) AS pair_count "
                "MATCH (e:Experience)-[:INVOLVES]->(:Concept)<-[:PATTERN_INVOLVES]-(tp1) "
                "WITH tp1, tp2, pair_count, count(DISTINCT e) AS tp1_total "
                "MERGE (tp1)-[r:FOLLOWED_BY]->(tp2) "
                "SET r.transition_count = pair_count, "
                "  r.transition_probability = toFloat(pair_count) / tp1_total, "
                "  r.created_at = datetime() "
                "RETURN count(r) AS updated"
            )
            record = await result.single()
            updated = record["updated"] if record else 0
            logger.info(f"Transition probabilities updated: {updated}")
            return updated

    # ==================== pending_questions ====================

    async def insert_pending_question(
        self,
        question: str,
        source: str = "conversation",
        curiosity_log_id: str = None,
    ) -> dict:
        """PendingQuestion 노드 생성 (+ 선택적 CuriosityLog GENERATED 관계)"""
        props = {
            "question": question,
            "source": source,
            "status": "pending",
            "asked_at": _now_iso(),
        }
        async with self.driver.session(database=_DB_NAME) as s:
            if curiosity_log_id:
                result = await s.run(
                    "MATCH (cl:CuriosityLog {id: $cl_id}) "
                    "CREATE (pq:PendingQuestion {id: randomUUID()}) SET pq += $props "
                    "CREATE (cl)-[:GENERATED]->(pq) "
                    "RETURN pq",
                    cl_id=curiosity_log_id,
                    props=props,
                )
            else:
                result = await s.run(
                    "CREATE (pq:PendingQuestion {id: randomUUID()}) SET pq += $props RETURN pq",
                    props=props,
                )
            record = await result.single()
            return dict(record["pq"]) if record else {}

    async def get_pending_questions(
        self,
        status: str = None,
        limit: int = 20,
    ) -> list[dict]:
        """PendingQuestion 목록 조회"""
        async with self.driver.session(database=_DB_NAME) as s:
            if status:
                result = await s.run(
                    "MATCH (pq:PendingQuestion {status: $status}) "
                    "RETURN pq ORDER BY pq.asked_at DESC LIMIT $limit",
                    status=status, limit=limit,
                )
            else:
                result = await s.run(
                    "MATCH (pq:PendingQuestion) "
                    "RETURN pq ORDER BY pq.asked_at DESC LIMIT $limit",
                    limit=limit,
                )
            records = await result.fetch(limit)
            return [dict(r["pq"]) for r in records]

    async def update_question_status(
        self,
        question_id: str,
        status: str,
    ) -> dict:
        """PendingQuestion 상태 변경 (pending → dismissed 등)"""
        async with self.driver.session(database=_DB_NAME) as s:
            result = await s.run(
                "MATCH (pq:PendingQuestion {id: $id}) "
                "SET pq.status = $status "
                "RETURN pq",
                id=question_id, status=status,
            )
            record = await result.single()
            return dict(record["pq"]) if record else {}

    async def submit_question_answer(
        self,
        question_id: str,
        answer: str,
        answer_confidence: float = 0.5,
    ) -> dict:
        """PendingQuestion 답변 제출"""
        async with self.driver.session(database=_DB_NAME) as s:
            result = await s.run(
                "MATCH (pq:PendingQuestion {id: $id}) "
                "SET pq.answer = $answer, "
                "  pq.answer_confidence = $conf, "
                "  pq.answered_at = $now, "
                "  pq.status = 'answered' "
                "RETURN pq",
                id=question_id,
                answer=answer,
                conf=answer_confidence,
                now=_now_iso(),
            )
            record = await result.single()
            return dict(record["pq"]) if record else {}

    # ==================== sleep / memory replay (Phase C3) ====================

    async def replay_recent_memories(
        self,
        salience_threshold: float = 0.4,
        max_experiences: int = 10,
        hebb_delta: float = 0.02,
    ) -> dict:
        """수면 중 기억 재생: 고감정 경험의 개념 네트워크를 재활성화 + offline Hebbian

        Returns:
            {
                "reactivated_count": int,
                "hebbian_updates": int,
                "activation_events": list[dict],  # SSE 전송용
                "experiences_replayed": int,
            }
        """
        from itertools import combinations

        async with self.driver.session(database=_DB_NAME) as s:
            # 1. 고감정 경험 조회 (emotional_salience 높은 순)
            result = await s.run(
                "MATCH (e:Experience) "
                "WHERE e.emotional_salience > $threshold "
                "RETURN e.id AS exp_id, e.emotional_salience AS salience "
                "ORDER BY e.emotional_salience DESC LIMIT $limit",
                threshold=salience_threshold,
                limit=max_experiences,
            )
            experiences = await result.fetch(max_experiences)

        if not experiences:
            return {
                "reactivated_count": 0,
                "hebbian_updates": 0,
                "activation_events": [],
                "experiences_replayed": 0,
            }

        # 2. 각 경험의 INVOLVES → Concept IDs 수집
        all_concept_ids: list[str] = []
        activation_events: list[dict] = []

        async with self.driver.session(database=_DB_NAME) as s:
            for exp in experiences:
                result = await s.run(
                    "MATCH (e:Experience {id: $exp_id})-[inv:INVOLVES]->(c:Concept) "
                    "OPTIONAL MATCH (c)-[:MAPPED_TO]->(br:BrainRegion) "
                    "RETURN c.id AS concept_id, br.id AS brain_region_id, "
                    "  inv.relevance AS relevance",
                    exp_id=exp["exp_id"],
                )
                records = await result.fetch(50)
                for r in records:
                    cid = r["concept_id"]
                    if cid and cid not in all_concept_ids:
                        all_concept_ids.append(cid)
                    if cid:
                        activation_events.append({
                            "concept_id": cid,
                            "brain_region_id": r["brain_region_id"],
                            "intensity": round(float(r["relevance"] or 0.5) * 0.7, 3),
                            "trigger_type": "sleep_replay",
                        })

        # 3. Spreading activation으로 추가 개념 활성화
        spread_ids: list[str] = []
        if all_concept_ids:
            spread_results = await self.get_spreading_activation(
                concept_ids=all_concept_ids[:10],  # 상위 10개만
                depth=1,  # 수면 중은 얕은 전파
                limit=15,
            )
            for sr in spread_results:
                sid = sr.get("id")
                if sid and sid not in all_concept_ids:
                    spread_ids.append(sid)
                    activation_events.append({
                        "concept_id": sid,
                        "brain_region_id": sr.get("brain_region_id"),
                        "intensity": round(float(sr.get("activation_strength") or 0.3) * 0.5, 3),
                        "trigger_type": "sleep_replay",
                    })

        # 4. Hebbian update: 재활성화된 모든 개념 쌍
        total_hebb = 0
        combined_ids = all_concept_ids + spread_ids
        if len(combined_ids) >= 2:
            pairs = list(combinations(combined_ids, 2))
            total_hebb = await self.hebbian_update(pairs, strength_delta=hebb_delta)

        return {
            "reactivated_count": len(combined_ids),
            "hebbian_updates": total_hebb,
            "activation_events": activation_events,
            "experiences_replayed": len(experiences),
        }

    async def create_sleep_log(
        self,
        trigger_type: str = "idle",
        reinforced_count: int = 0,
        decayed_count: int = 0,
        patterns_promoted: int = 0,
        replay_count: int = 0,
        duration_ms: int = 0,
        development_stage: int = 0,
    ) -> dict:
        """SleepLog 노드 생성 (기억 통합/재생 기록)"""
        props = {
            "trigger_type": trigger_type,
            "reinforced_count": reinforced_count,
            "decayed_count": decayed_count,
            "patterns_promoted": patterns_promoted,
            "replay_count": replay_count,
            "duration_ms": duration_ms,
            "development_stage": development_stage,
            "success": True,
            "created_at": _now_iso(),
        }
        async with self.driver.session(database=_DB_NAME) as s:
            result = await s.run(
                "CREATE (sl:SleepLog {id: randomUUID()}) SET sl += $props RETURN sl",
                props=props,
            )
            record = await result.single()
            return dict(record["sl"]) if record else {}


# ── 싱글톤 팩토리 ────────────────────────────────────────────────────────────

_db_instance: Optional[BrainDatabase] = None


def get_brain_db() -> BrainDatabase:
    """BrainDatabase 싱글톤 (init_driver() 이후에 사용)"""
    global _db_instance
    if _db_instance is None:
        _db_instance = BrainDatabase()
    return _db_instance
