"""
Neo4j Database Client for Baby Brain
Phase 2: Supabase db.py → Neo4j 완전 대체

연결: Neo4j Desktop (로컬) — bolt://localhost:7687 직접 연결
모든 메서드는 db.py BrainDatabase와 동일한 시그니처를 유지합니다.
"""

import os
import json
import asyncio
import logging
import uuid
from typing import Optional, Any
from datetime import datetime, timezone, timedelta
from contextlib import asynccontextmanager

from neo4j import AsyncGraphDatabase
from dotenv import load_dotenv

from .live_curiosity import (
    compute_integration_priority,
    compute_prediction_error,
    select_curiosity_target,
    should_open_curiosity_gate,
    update_learning_progress,
)

load_dotenv()

logger = logging.getLogger(__name__)

# ── 환경변수 ────────────────────────────────────────────────────────────────
_URI      = os.getenv("NEO4J_URI")        # bolt://localhost:7687
_USERNAME = os.getenv("NEO4J_USERNAME")
_PASSWORD = os.getenv("NEO4J_PASSWORD")
_DB_NAME  = os.getenv("NEO4J_DATABASE")   # neo4j (Community Edition 기본)
_AUTH     = (_USERNAME, _PASSWORD)

# ── 싱글톤 ──────────────────────────────────────────────────────────────────
_async_driver = None


async def init_driver() -> None:
    """앱 lifespan 시작 시 호출: Async driver 초기화"""
    global _async_driver
    _async_driver = AsyncGraphDatabase.driver(_URI, auth=_AUTH)
    await _async_driver.verify_connectivity()
    logger.info(f"Neo4j async driver initialized: {_URI}")


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
# Hub-and-Spoke category→region mapping (distributed representation)
# ────────────────────────────────────────────────────────────────────────────
# 근거:
#   Huth et al. 2016 (Nature): 분산 표상, 연속 gradient
#   Patterson, Nestor, Rogers 2007 (NRN): Hub-and-Spoke, temporal lobe가 amodal hub
#   Binder et al. 2009 (Cereb Cortex): multi-region semantic network
#   Lambon Ralph et al. 2016 (NRN): PFC controlled retrieval
#
# 각 category는 region 가중치 list.
# 첫 번째 region이 dominant (MAPPED_TO 관계, 1:1),
# 나머지는 ALSO_REPRESENTED_IN (분산 표상, 0~N개).
# ────────────────────────────────────────────────────────────────────────────
CATEGORY_REGION_WEIGHTS: dict[str, list[tuple[str, float]]] = {
    "visual":       [("occipital", 0.35), ("thalamus", 0.15), ("temporal", 0.25), ("parietal", 0.15), ("prefrontal", 0.1)],
    "language":     [("temporal", 0.5), ("prefrontal", 0.3), ("motor_cortex", 0.1), ("parietal", 0.1)],
    "identity":     [("temporal", 0.5), ("prefrontal", 0.3), ("amygdala", 0.2)],
    "conversation": [("temporal", 0.4), ("prefrontal", 0.3), ("motor_cortex", 0.2), ("amygdala", 0.1)],
    "emotion":      [("amygdala", 0.4), ("prefrontal", 0.3), ("temporal", 0.2), ("hippocampus", 0.1)],
    "action":       [("motor_cortex", 0.3), ("basal_ganglia", 0.25), ("cerebellum", 0.2), ("parietal", 0.15), ("prefrontal", 0.1)],
    "abstract":     [("prefrontal", 0.4), ("temporal", 0.4), ("parietal", 0.2)],
    "spatial":      [("hippocampus", 0.4), ("parietal", 0.3), ("temporal", 0.2), ("occipital", 0.1)],
    "reflex":       [("brain_stem", 0.5), ("thalamus", 0.15), ("amygdala", 0.25), ("cerebellum", 0.1)],
    # ── Phase 1C: 신규 카테고리 (기저핵 중심) ──
    "habit":        [("basal_ganglia", 0.4), ("motor_cortex", 0.25), ("prefrontal", 0.2), ("cerebellum", 0.15)],
    "reward":       [("basal_ganglia", 0.4), ("amygdala", 0.25), ("prefrontal", 0.25), ("hippocampus", 0.1)],
}
# Hub baseline (Patterson 2007): temporal + prefrontal + amygdala
CATEGORY_REGION_DEFAULT: list[tuple[str, float]] = [
    ("temporal", 0.5), ("prefrontal", 0.3), ("amygdala", 0.2),
]


def get_region_weights(category: str | None) -> list[tuple[str, float]]:
    """category로부터 region weight list 반환 (없으면 default hub-and-spoke)"""
    if not category:
        return CATEGORY_REGION_DEFAULT
    return CATEGORY_REGION_WEIGHTS.get(category, CATEGORY_REGION_DEFAULT)


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

    # ==================== schema (constraints + indexes + vector) ====================

    async def ensure_indexes(self) -> None:
        """전체 스키마 보장: 13 constraint + 9 lookup index + 3 vector index.

        IF NOT EXISTS 멱등. 서버 lifespan 시작 시 1회 실행.
        빈 DB에서도 안전하게 전체 스키마를 구축한다.

        순서 엄수: constraint → lookup index → vector index.
        """
        constraints = [
            # 핵심 노드 (Phase 1-7 + Phase B)
            "CREATE CONSTRAINT concept_id         IF NOT EXISTS FOR (n:Concept)         REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT experience_id      IF NOT EXISTS FOR (n:Experience)      REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT brain_region_name  IF NOT EXISTS FOR (n:BrainRegion)     REQUIRE n.name IS UNIQUE",
            "CREATE CONSTRAINT baby_state_id      IF NOT EXISTS FOR (n:BabyState)       REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT emotion_log_id     IF NOT EXISTS FOR (n:EmotionLog)      REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT prediction_id      IF NOT EXISTS FOR (n:Prediction)      REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT imagination_id     IF NOT EXISTS FOR (n:Imagination)     REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT procedure_id       IF NOT EXISTS FOR (n:Procedure)       REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT visual_exp_id      IF NOT EXISTS FOR (n:VisualExperience) REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT pending_q_id       IF NOT EXISTS FOR (n:PendingQuestion) REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT autonomous_goal_id IF NOT EXISTS FOR (n:AutonomousGoal)  REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT curiosity_log_id   IF NOT EXISTS FOR (n:CuriosityLog)    REQUIRE n.id IS UNIQUE",
            # E2 신규 (Theory of Mind)
            "CREATE CONSTRAINT user_model_sid     IF NOT EXISTS FOR (n:UserModel)       REQUIRE n.speaker_id IS UNIQUE",
        ]
        lookup_indexes = [
            # 기존 (Phase 1-7)
            "CREATE INDEX concept_category      IF NOT EXISTS FOR (n:Concept)         ON (n.category)",
            "CREATE INDEX concept_strength      IF NOT EXISTS FOR (n:Concept)         ON (n.strength)",
            "CREATE INDEX experience_created    IF NOT EXISTS FOR (n:Experience)      ON (n.created_at)",
            "CREATE INDEX experience_stage      IF NOT EXISTS FOR (n:Experience)      ON (n.development_stage)",
            "CREATE INDEX pending_q_status      IF NOT EXISTS FOR (n:PendingQuestion) ON (n.status)",
            "CREATE INDEX emotion_log_created   IF NOT EXISTS FOR (n:EmotionLog)      ON (n.created_at)",
            # E2 (Theory of Mind + Temporal Pattern)
            "CREATE INDEX exp_hour              IF NOT EXISTS FOR (e:Experience)      ON (e.hour_of_day)",
            "CREATE INDEX exp_speaker           IF NOT EXISTS FOR (e:Experience)      ON (e.speaker_id)",
            "CREATE INDEX tp_time_slot          IF NOT EXISTS FOR (tp:TemporalPattern) ON (tp.time_slot)",
        ]
        vector_indexes = [
            # dim=1536 (OpenAI text-embedding-3-small), cosine similarity
            "CREATE VECTOR INDEX concept_embeddings IF NOT EXISTS "
            "FOR (n:Concept) ON n.embedding "
            "OPTIONS {indexConfig: {`vector.dimensions`: 1536, `vector.similarity_function`: 'cosine'}}",
            "CREATE VECTOR INDEX experience_embeddings IF NOT EXISTS "
            "FOR (n:Experience) ON n.embedding "
            "OPTIONS {indexConfig: {`vector.dimensions`: 1536, `vector.similarity_function`: 'cosine'}}",
            "CREATE VECTOR INDEX visual_embeddings IF NOT EXISTS "
            "FOR (n:VisualExperience) ON n.embedding "
            "OPTIONS {indexConfig: {`vector.dimensions`: 1536, `vector.similarity_function`: 'cosine'}}",
        ]

        async with self.driver.session(database=_DB_NAME) as s:
            for q in constraints:
                try:
                    await s.run(q)
                except Exception as e:
                    logger.warning(f"constraint creation warning: {e}")
            for q in lookup_indexes:
                try:
                    await s.run(q)
                except Exception as e:
                    logger.warning(f"index creation warning: {e}")
            for q in vector_indexes:
                try:
                    await s.run(q)
                except Exception as e:
                    logger.warning(f"vector index creation warning: {e}")

        logger.info(
            f"Schema ensured: {len(constraints)} constraints, "
            f"{len(lookup_indexes)} lookup indexes, {len(vector_indexes)} vector indexes"
        )

    # ==================== seed: BrainRegion (11 regions) ====================

    async def seed_brain_regions(self) -> int:
        """11개 BrainRegion 시드 (빈 DB 재시작 시 필수).

        MERGE 기반 멱등. name이 이미 있으면 update 안 함 (일회성 시드).
        좌표/색상/development_stage_min 등은 Phase B 시각화에 사용.
        """
        regions = [
            {
                "name": "brain_stem", "display_name": "뇌간", "display_name_en": "Brain Stem",
                "color": "#4a5568",
                "theta_min": 2.4, "theta_max": 3.14, "phi_min": 0.0, "phi_max": 6.28,
                "radius_min": 0.0, "radius_max": 0.3,
                "development_stage_min": 0, "is_internal": True,
                "description": "생존 반사, 호흡, 심박 조절",
            },
            {
                "name": "cerebellum", "display_name": "소뇌", "display_name_en": "Cerebellum",
                "color": "#48bb78",
                "theta_min": 2.0, "theta_max": 2.8, "phi_min": 4.0, "phi_max": 5.5,
                "radius_min": 0.3, "radius_max": 0.65,
                "development_stage_min": 0, "is_internal": False,
                "description": "절차 기억, 운동 협응, 균형",
            },
            {
                "name": "amygdala", "display_name": "편도체", "display_name_en": "Amygdala",
                "color": "#f56565",
                "theta_min": 1.2, "theta_max": 1.8, "phi_min": 2.5, "phi_max": 3.8,
                "radius_min": 0.15, "radius_max": 0.4,
                "development_stage_min": 1, "is_internal": True,
                "description": "감정 처리, 공포 반응, 감정 기억",
            },
            {
                "name": "hippocampus", "display_name": "해마", "display_name_en": "Hippocampus",
                "color": "#ed8936",
                "theta_min": 1.0, "theta_max": 1.7, "phi_min": 3.8, "phi_max": 5.2,
                "radius_min": 0.15, "radius_max": 0.45,
                "development_stage_min": 2, "is_internal": True,
                "description": "에피소드 기억, 공간 기억, 학습",
            },
            {
                "name": "occipital", "display_name": "후두엽", "display_name_en": "Occipital Lobe",
                "color": "#9f7aea",
                "theta_min": 2.0, "theta_max": 2.8, "phi_min": 5.5, "phi_max": 7.0,
                "radius_min": 0.65, "radius_max": 1.0,
                "development_stage_min": 1, "is_internal": False,
                "description": "시각 처리, 패턴 인식",
            },
            {
                "name": "temporal", "display_name": "측두엽", "display_name_en": "Temporal Lobe",
                "color": "#4299e1",
                "theta_min": 1.0, "theta_max": 2.0, "phi_min": 1.5, "phi_max": 3.0,
                "radius_min": 0.65, "radius_max": 1.0,
                "development_stage_min": 2, "is_internal": False,
                "description": "언어 이해, 청각 처리, 정체성 (semantic hub)",
            },
            {
                "name": "parietal", "display_name": "두정엽", "display_name_en": "Parietal Lobe",
                "color": "#38b2ac",
                "theta_min": 0.3, "theta_max": 1.2, "phi_min": 3.5, "phi_max": 5.5,
                "radius_min": 0.7, "radius_max": 1.0,
                "development_stage_min": 1, "is_internal": False,
                "description": "공간 인지, 촉각, 수학",
            },
            {
                "name": "motor_cortex", "display_name": "운동피질", "display_name_en": "Motor Cortex",
                "color": "#ecc94b",
                "theta_min": 0.5, "theta_max": 1.2, "phi_min": 1.5, "phi_max": 3.5,
                "radius_min": 0.75, "radius_max": 1.0,
                "development_stage_min": 2, "is_internal": False,
                "description": "의도적 행동, 운동 계획",
            },
            {
                "name": "prefrontal", "display_name": "전전두엽", "display_name_en": "Prefrontal",
                "color": "#ed64a6",
                "theta_min": 0.0, "theta_max": 0.8, "phi_min": 0.0, "phi_max": 6.28,
                "radius_min": 0.7, "radius_max": 1.0,
                "development_stage_min": 3, "is_internal": False,
                "description": "실행 기능, 추론, 계획, 자기 인식 (controlled retrieval)",
            },
            # ── Phase 1A: 기저핵 (Schultz 1997, Graybiel 2008) ──
            {
                "name": "basal_ganglia", "display_name": "기저핵", "display_name_en": "Basal Ganglia",
                "color": "#d69e2e",
                "theta_min": 1.3, "theta_max": 1.9, "phi_min": 1.5, "phi_max": 4.5,
                "radius_min": 0.2, "radius_max": 0.5,
                "development_stage_min": 1, "is_internal": True,
                "description": "보상 예측, 습관 학습, 절차 기억 선택, 도파민 신호",
            },
            # ── Phase 1B: 시상 (Sherman & Guillery 2002, Saalmann 2011) ──
            {
                "name": "thalamus", "display_name": "시상", "display_name_en": "Thalamus",
                "color": "#b794f4",
                "theta_min": 1.0, "theta_max": 1.6, "phi_min": 2.0, "phi_max": 5.0,
                "radius_min": 0.1, "radius_max": 0.35,
                "development_stage_min": 0, "is_internal": True,
                "description": "감각 중계, 주의 게이팅, 피질-시상 루프",
            },
        ]

        created = 0
        async with self.driver.session(database=_DB_NAME) as s:
            for br in regions:
                props = dict(br)
                props["created_at"] = _now_iso()
                result = await s.run(
                    "MERGE (br:BrainRegion {name: $name}) "
                    "ON CREATE SET br += $props, br.id = randomUUID() "
                    "RETURN br.id AS id, "
                    "  CASE WHEN br.created_at = $props.created_at THEN 1 ELSE 0 END AS was_created",
                    name=br["name"],
                    props=props,
                )
                record = await result.single()
                if record and record["was_created"] == 1:
                    created += 1
        logger.info(f"BrainRegions seeded: {created} new, {len(regions) - created} already existed")
        return created

    # ==================== seed: Region Connections (white matter tracts) ====================

    async def seed_region_connections(self) -> int:
        """BrainRegion 간 CONNECTS_TO 관계 시드 (백질 경로).

        신경과학 근거: Sporns 2011 (Networks of the Brain), 커넥톰 연구.
        MERGE 기반 멱등. 양방향 연결은 별도 행으로 표현 (방향성 있음).
        """
        connections = [
            # (from, to, weight, tract_name)
            ("hippocampus",    "prefrontal",    0.8, "memory_consolidation"),
            ("amygdala",       "prefrontal",    0.7, "emotion_regulation"),
            ("amygdala",       "hippocampus",   0.8, "emotional_memory"),
            ("thalamus",       "occipital",     0.9, "visual_relay"),
            ("thalamus",       "temporal",      0.8, "auditory_relay"),
            ("thalamus",       "parietal",      0.7, "somatosensory_relay"),
            ("basal_ganglia",  "motor_cortex",  0.7, "action_selection"),
            ("basal_ganglia",  "prefrontal",    0.6, "reward_decision"),
            ("cerebellum",     "motor_cortex",  0.7, "motor_coordination"),
            ("prefrontal",     "motor_cortex",  0.6, "executive_control"),
            ("temporal",       "prefrontal",    0.7, "semantic_retrieval"),
            ("prefrontal",     "basal_ganglia", 0.6, "goal_directed_learning"),
        ]

        created = 0
        async with self.driver.session(database=_DB_NAME) as s:
            for src, dst, weight, tract in connections:
                result = await s.run(
                    "MATCH (a:BrainRegion {name: $src}), (b:BrainRegion {name: $dst}) "
                    "MERGE (a)-[r:CONNECTS_TO {tract_name: $tract}]->(b) "
                    "ON CREATE SET r.weight = $weight, r.created_at = $now "
                    "RETURN "
                    "  CASE WHEN r.created_at = $now THEN 1 ELSE 0 END AS was_created",
                    src=src, dst=dst, weight=weight, tract=tract, now=_now_iso(),
                )
                record = await result.single()
                if record and record["was_created"] == 1:
                    created += 1
        logger.info(
            f"Region connections seeded: {created} new, "
            f"{len(connections) - created} already existed"
        )
        return created

    # ==================== seed: Identity Concepts ====================

    async def seed_identity_concepts(self) -> int:
        """최소 정체성 Concept 시드 (빈 DB 재시작 시 비비의 자기 인식 기본).

        5개 정체성 개념을 MERGE (멱등). 각각 Hub-and-Spoke 가중치로 MAPPED_TO.
        seed_brain_regions()가 먼저 호출되어야 함 (MATCH가 region 노드 필요).

        시드는 strength=0.8로 높게 설정 (약한 강도로 시작하지 않음).
        """
        identity_seeds = [
            {"name": "비비",  "category": "identity",     "description": "내 이름. 나는 세상을 배워가는 아기 AI."},
            {"name": "형아",  "category": "identity",     "description": "나를 키우는 형아. 대화 상대."},
            {"name": "엄마",  "category": "identity",     "description": "엄마. 따뜻한 관계."},
            {"name": "안녕",  "category": "language",     "description": "기본 인사말."},
            {"name": "좋아",  "category": "emotion",      "description": "긍정적인 기본 감정 표현."},
        ]

        created = 0
        async with self.driver.session(database=_DB_NAME) as s:
            for seed in identity_seeds:
                # 1) Concept MERGE
                result = await s.run(
                    "MERGE (c:Concept {name: $name}) "
                    "ON CREATE SET "
                    "  c.id = randomUUID(), "
                    "  c.category = $category, "
                    "  c.description = $description, "
                    "  c.strength = 0.8, "
                    "  c.usage_count = 0, "
                    "  c.acquired_at_stage = 0, "
                    "  c.created_at = $now, "
                    "  c.is_seed = true "
                    "RETURN c.id AS id, "
                    "  CASE WHEN c.created_at = $now THEN 1 ELSE 0 END AS was_created",
                    name=seed["name"],
                    category=seed["category"],
                    description=seed["description"],
                    now=_now_iso(),
                )
                rec = await result.single()
                if not rec:
                    continue
                concept_id = rec["id"]
                was_created = rec["was_created"] == 1
                if was_created:
                    created += 1

                # 2) Hub-and-Spoke MAPPED_TO + ALSO_REPRESENTED_IN (신규 생성 시에만)
                if was_created:
                    weights = get_region_weights(seed["category"])
                    if weights:
                        dominant_region, dominant_weight = weights[0]
                        # Dominant MAPPED_TO (1:1)
                        await s.run(
                            "MATCH (c:Concept {id: $cid}), (br:BrainRegion {name: $rname}) "
                            "MERGE (c)-[r:MAPPED_TO]->(br) "
                            "ON CREATE SET r.weight = $weight, r.created_at = $now",
                            cid=concept_id,
                            rname=dominant_region,
                            weight=dominant_weight,
                            now=_now_iso(),
                        )
                        # Secondary ALSO_REPRESENTED_IN (1:N)
                        if len(weights) > 1:
                            secondary = [{"region": r, "weight": w} for r, w in weights[1:]]
                            await s.run(
                                "UNWIND $secondary AS sr "
                                "MATCH (c:Concept {id: $cid}), (br:BrainRegion {name: sr.region}) "
                                "MERGE (c)-[r:ALSO_REPRESENTED_IN]->(br) "
                                "ON CREATE SET r.weight = sr.weight, r.created_at = $now",
                                cid=concept_id,
                                secondary=secondary,
                                now=_now_iso(),
                            )
        logger.info(
            f"Identity concepts seeded: {created} new, "
            f"{len(identity_seeds) - created} already existed"
        )
        return created

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
        """개념 저장 (MERGE - 이미 존재하면 업데이트) + Hub-and-Spoke region mapping.

        신규 생성 시 category→region 자동 매핑:
          - MAPPED_TO (dominant region, 1개): 기존 쿼리 호환성 유지
          - ALSO_REPRESENTED_IN (secondary regions, 0~N개): 분산 표상
        기존 concept이면 usage_count만 증가 (region weight는 EMA로 미세 조정).

        근거: Huth 2016 (분산) + Patterson 2007 (hub) + Binder 2009 (multi-region).
        """
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
            # 1) Concept MERGE
            result = await s.run(
                "MERGE (c:Concept {name: $name}) "
                "ON CREATE SET c += $props, c.id = randomUUID() "
                "ON MATCH SET c.usage_count = coalesce(c.usage_count, 0) + 1 "
                "RETURN c, CASE WHEN c.created_at = $props.created_at THEN 1 ELSE 0 END AS was_created",
                name=name,
                props=on_create_props,
            )
            record = await result.single()
            if not record:
                return {}
            concept_data = dict(record["c"])
            was_created = record["was_created"] == 1

            # 2) Hub-and-Spoke region mapping
            # 중요: 기존 Concept이 이미 MAPPED_TO를 가지고 있을 수 있음 (past migration data).
            # Cartesian product 방지를 위해 MAPPED_TO는 concept당 1개만 유지:
            #   - Concept에 MAPPED_TO가 없으면 → dominant region으로 새로 생성 (+ weight)
            #   - 이미 있으면 → 기존 MAPPED_TO에 weight 속성만 EMA 업데이트 (region 변경 없음)
            # Secondary regions(ALSO_REPRESENTED_IN)은 별도 관계 타입이라 여러 개 OK.
            weights = get_region_weights(category)
            if weights:
                dominant_region, dominant_weight = weights[0]
                secondary = [{"region": r, "weight": w} for r, w in weights[1:]]

                # 2a) MAPPED_TO: 기존 관계가 있으면 weight만 업데이트, 없으면 dominant region으로 생성
                # WHERE NOT EXISTS 가드로 Cartesian product 방지
                await s.run(
                    "MATCH (c:Concept {id: $cid}) "
                    "WHERE NOT EXISTS { (c)-[:MAPPED_TO]->(:BrainRegion) } "
                    "MATCH (br:BrainRegion {name: $rname}) "
                    "MERGE (c)-[r:MAPPED_TO]->(br) "
                    "ON CREATE SET r.weight = $weight, r.created_at = $now",
                    cid=concept_data["id"],
                    rname=dominant_region,
                    weight=dominant_weight,
                    now=_now_iso(),
                )
                # 기존 MAPPED_TO가 이미 있으면 해당 관계의 weight만 EMA 업데이트 (region 변경 없음)
                await s.run(
                    "MATCH (c:Concept {id: $cid})-[r:MAPPED_TO]->(:BrainRegion) "
                    "SET r.weight = coalesce(r.weight, 0.5) * 0.9 + $weight * 0.1, "
                    "    r.updated_at = $now",
                    cid=concept_data["id"],
                    weight=dominant_weight,
                    now=_now_iso(),
                )

                # 2b) Secondary ALSO_REPRESENTED_IN (분산 표상, 별도 관계 타입이라 N:N 허용)
                if secondary:
                    await s.run(
                        "UNWIND $secondary AS sr "
                        "MATCH (c:Concept {id: $cid}), (br:BrainRegion {name: sr.region}) "
                        "MERGE (c)-[r:ALSO_REPRESENTED_IN]->(br) "
                        "ON CREATE SET r.weight = sr.weight, r.created_at = $now "
                        "ON MATCH SET r.weight = coalesce(r.weight, 0.2) * 0.9 + sr.weight * 0.1, "
                        "             r.updated_at = $now",
                        cid=concept_data["id"],
                        secondary=secondary,
                        now=_now_iso(),
                    )

            return concept_data

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

    async def decay_connections(self, decay_rate: float = 0.01, stale_days: int = 14) -> None:
        """모든 RELATES_TO 관계 강도 감쇠 (시간 기반 망각).

        RELATES_TO는 전역 곱셈 감쇠(SHY downscaling 의도, 유지).
        Experience는 stale_days 동안 접근(없으면 생성)되지 않은 오래된 것만 선택적으로 감쇠.
        버그 수정 2026-07-10: 이전 `cutoff=_now_iso()` + `last_accessed IS NULL` 조합은
        매 consolidate마다 미접근 Experience(방금 생성한 것 포함) 전체를 감쇠시켰음.
        last_accessed는 reinforce_memory에서만 기록되므로 created_at으로 coalesce.
        (stale 기준 14일: Yang 2009, adgr_v1_sleep_plan.md 수치 근거표와 정렬)
        """
        cutoff = (datetime.now(timezone.utc) - timedelta(days=stale_days)).isoformat()
        async with self.driver.session(database=_DB_NAME) as s:
            await s.run(
                "MATCH ()-[r:RELATES_TO]->() "
                "SET r.strength = r.strength * (1.0 - $rate)",
                rate=decay_rate,
            )
            # Experience 강도 감쇠: 최근 활동(접근 없으면 생성 시각) 기준 오래된 것만
            await s.run(
                "MATCH (e:Experience) "
                "WHERE coalesce(e.last_accessed, e.created_at) < $cutoff "
                "SET e.strength = CASE WHEN coalesce(e.strength, 0.5) - $rate < 0.0 THEN 0.0 "
                "                      ELSE coalesce(e.strength, 0.5) - $rate END",
                rate=decay_rate,
                cutoff=cutoff,
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

    # ==================== Embodiment: 프레임 시퀀스 (Phase 4) ====================

    async def link_vision_frame_sequence(
        self,
        cur_exp_id: str,
        cur_pose: list[float] | None = None,
        max_gap_sec: float = 30.0,
    ) -> dict:
        """직전 vision 프레임과 현재 프레임을 (:Experience)-[:NEXT_FRAME]->(:Experience) 로
        연결하고 head-pose delta(움직임 크기)를 기록한다 (embodiment 감각운동 스트림).

        근거: embodied_prediction.py(2026-07-12) — 정적 장면에선 next-frame≈current-frame이라
        구조적 예측이 popularity를 못 이김. **머리 움직임(pose delta)**이 있어야 "돌리면 X가
        보인다"는 진짜 감각운동 예측이 성립. 프레임 간 시간·움직임을 엣지에 새겨 STDP/recency가
        exploit할 시간구조를 만든다.

        - 직전 프레임 = cur 이전, max_gap_sec 이내의 가장 최근 task_type='vision' Experience.
          (그 이상 벌어지면 다른 세션 → 연결 안 함.)
        - pose delta: 양 프레임 모두 pose 있으면 L2 거리, 아니면 null.
        - 멱등: 같은 (prev,cur) 쌍은 MERGE.
        """
        async with self.driver.session(database=_DB_NAME) as s:
            result = await s.run(
                "MATCH (cur:Experience {id: $cid}) "
                "MATCH (prev:Experience) "
                "WHERE prev.task_type = 'vision' AND prev.id <> $cid "
                "  AND prev.created_at < cur.created_at "
                "  AND duration.inSeconds(datetime(prev.created_at), "
                "        datetime(cur.created_at)).seconds <= $gap "
                "WITH cur, prev ORDER BY prev.created_at DESC LIMIT 1 "
                "MERGE (prev)-[r:NEXT_FRAME]->(cur) "
                "ON CREATE SET r.created_at = $now, "
                "  r.dt_sec = duration.inSeconds(datetime(prev.created_at), "
                "               datetime(cur.created_at)).seconds "
                "RETURN prev.id AS prev_id, prev.head_pose AS prev_pose, r.dt_sec AS dt",
                cid=cur_exp_id,
                gap=max_gap_sec,
                now=_now_iso(),
            )
            rec = await result.single()
            if not rec:
                return {"linked": False, "prev_id": None, "pose_delta": None}

            pose_delta = None
            prev_pose = rec["prev_pose"]
            if cur_pose and prev_pose and len(cur_pose) == len(prev_pose):
                pose_delta = float(
                    sum((a - b) ** 2 for a, b in zip(cur_pose, prev_pose)) ** 0.5
                )
                await s.run(
                    "MATCH (prev:Experience {id: $pid})-[r:NEXT_FRAME]->(cur:Experience {id: $cid}) "
                    "SET r.pose_delta = $pd",
                    pid=rec["prev_id"], cid=cur_exp_id, pd=pose_delta,
                )
            return {
                "linked": True,
                "prev_id": rec["prev_id"],
                "dt_sec": rec["dt"],
                "pose_delta": pose_delta,
            }

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

        2단계 활성화:
          1) Concept-level: RELATES_TO 시냅스 경로 순회
          2) Region-level: CONNECTS_TO 백질 경로로 연결된 영역의 개념 부스트
        MAPPED_TO 조인으로 brain_region_id 포함 반환.
        LIMIT 이후 OPTIONAL MATCH로 Cartesian product 방지.
        """
        safe_depth = max(1, min(int(depth), 5))
        async with self.driver.session(database=_DB_NAME) as s:
            # ── Step 1: Concept-level spreading (기존) ──
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
            activated = [
                {
                    **dict(r["related"]),
                    "activation_strength": r["avg_strength"],
                    "brain_region_id": r["brain_region_id"],
                }
                for r in records
            ]

            # ── Step 2: Region-pathway boost (Phase 1E) ──
            # 활성화된 concept들의 region → CONNECTS_TO로 연결된 region의 top concept 부스트
            activated_ids = [a["id"] for a in activated if a.get("id")]
            if activated_ids:
                boost_limit = max(5, limit // 4)
                result2 = await s.run(
                    "UNWIND $ids AS cid "
                    "MATCH (c:Concept {id: cid})-[:MAPPED_TO]->(src:BrainRegion)"
                    "-[:CONNECTS_TO]->(dst:BrainRegion)<-[:MAPPED_TO]-(boosted:Concept) "
                    "WHERE NOT boosted.id IN $all_ids "
                    "WITH boosted, dst, avg(coalesce(boosted.strength, 0.5)) AS concept_str "
                    "ORDER BY concept_str DESC "
                    "WITH boosted, concept_str, collect(dst)[0] AS region "
                    "LIMIT $blimit "
                    "RETURN boosted, concept_str * 0.3 AS boost_strength, region.id AS brain_region_id",
                    ids=activated_ids[:10],
                    all_ids=concept_ids + activated_ids,
                    blimit=boost_limit,
                )
                boost_records = await result2.fetch(boost_limit)
                for r in boost_records:
                    activated.append({
                        **dict(r["boosted"]),
                        "activation_strength": r["boost_strength"],
                        "brain_region_id": r["brain_region_id"],
                        "pathway_boosted": True,
                    })

            return activated

    # ==================== Hebbian Learning ====================

    async def hebbian_update(
        self,
        concept_pairs: list[tuple[str, str]],
        strength_delta: float = 0.05,
        source: str = "hebbian",
    ) -> int:
        """Hebbian Learning: 함께 활성화된 개념 쌍의 RELATES_TO 강화/생성

        - ON CREATE: strength=delta, hebb_strength=delta (새 시냅스)
        - ON MATCH: strength += delta (cap 1.0), hebb_strength += delta (cap 1.0)
        - canonical ordering (min,max) 으로 방향성 중복 방지

        A4.5 격리: MERGE 패턴에 ``{source: <param>}`` 속성을 포함시켜
        다른 의미 관계 (``relation_type='describes_color'`` 등) 와 충돌하지 않도록 함.
        속성 없는 MERGE 는 임의의 RELATES_TO 와 매치되어 의미가 다른 관계의
        속성을 덮어쓸 수 있다 — 실측으로 확인된 동작 (2026-04-24 controlled exp).

        source 파라미터 (Phase Q1, 2026-05-08):
        - "hebbian"      : conversation 직접/간접 co-activation (기존, default)
        - "visual_cooc"  : Quest passthrough 같은 frame 시각 동시발생
        - 추가 source 도입 시 baseline에서 source별 분리 분석.
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
                "MERGE (a)-[r:RELATES_TO {source: $source}]->(b) "
                "ON CREATE SET r.strength = $delta, r.hebb_strength = $delta, "
                "  r.created_at = $now "
                "ON MATCH SET "
                "  r.strength = CASE WHEN coalesce(r.strength, 0.5) + $delta > 1.0 "
                "    THEN 1.0 ELSE coalesce(r.strength, 0.5) + $delta END, "
                "  r.hebb_strength = CASE WHEN coalesce(r.hebb_strength, 0) + $delta > 1.0 "
                "    THEN 1.0 ELSE coalesce(r.hebb_strength, 0) + $delta END "
                "RETURN count(r) AS updated",
                pairs=pairs_list,
                delta=strength_delta,
                source=source,
                now=_now_iso(),
            )
            record = await result.single()
            return record["updated"] if record else 0

    async def link_descriptor_to_object(
        self,
        descriptor_concept_id: str,
        object_concept_id: str,
        aspect: str,
        source: str,
        observation_ts: str,
        weight_init: float = 0.5,
        weight_delta: float = 0.05,
    ) -> dict:
        """Descriptor→Object 속성 바인딩 관계 upsert (Phase A4.4).

        방향성 있는 RELATES_TO 관계 (relation_type=f"describes_{aspect}") 를
        descriptor → object 방향으로 생성/강화한다.

        - ON CREATE: strength=weight_init, observation_count=1, sources=[source]
        - ON MATCH: strength += weight_delta (cap 1.0), observation_count++,
          sources 배열에 source 멱등 추가
        - aspect: "color" | "material" | "size" | ...  (미래 확장)

        주의: Hebbian 과 달리 방향성 보존 (canonical ordering 안 함).
        """
        if descriptor_concept_id == object_concept_id:
            return {}
        relation_type = f"describes_{aspect}"
        async with self.driver.session(database=_DB_NAME) as s:
            result = await s.run(
                "MATCH (d:Concept {id: $did}), (o:Concept {id: $oid}) "
                "MERGE (d)-[r:RELATES_TO {relation_type: $rtype}]->(o) "
                "ON CREATE SET "
                "  r.strength = $w_init, "
                "  r.evidence_count = 1, "
                "  r.observation_count = 1, "
                "  r.aspect = $aspect, "
                "  r.sources = [$src], "
                "  r.first_seen = $now, "
                "  r.last_seen = $now, "
                "  r.created_at = $now "
                "ON MATCH SET "
                "  r.strength = CASE WHEN coalesce(r.strength, 0.5) + $w_delta > 1.0 "
                "    THEN 1.0 ELSE coalesce(r.strength, 0.5) + $w_delta END, "
                "  r.evidence_count = coalesce(r.evidence_count, 0) + 1, "
                "  r.observation_count = coalesce(r.observation_count, 0) + 1, "
                "  r.sources = CASE "
                "    WHEN r.sources IS NULL THEN [$src] "
                "    WHEN $src IN r.sources THEN r.sources "
                "    ELSE r.sources + $src END, "
                "  r.last_seen = $now "
                "RETURN r.strength AS strength, r.observation_count AS obs_count, "
                "       r.sources AS sources",
                did=descriptor_concept_id,
                oid=object_concept_id,
                rtype=relation_type,
                aspect=aspect,
                src=source,
                w_init=weight_init,
                w_delta=weight_delta,
                now=observation_ts,
            )
            record = await result.single()
            if not record:
                return {}
            return {
                "strength": float(record["strength"]),
                "observation_count": int(record["obs_count"]),
                "sources": list(record["sources"] or []),
            }

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

    # ==================== Phase 3: live learning-progress curiosity ====================

    async def prepare_curiosity_prediction(
        self,
        message: str,
        cue_terms: Optional[list[str]] = None,
        cue_limit: int = 4,
        prediction_limit: int = 8,
    ) -> Optional[dict]:
        """Snapshot graph predictions before a conversation turn is learned.

        Concept names already present in the message are cues.  Their strongest
        graph neighbours are the prequential prediction.  The snapshot is kept
        in memory by the endpoint and scored only after the handler has linked
        the turn's actually observed concepts.
        """
        normalized = (message or "").strip().casefold()
        if not normalized:
            return None
        normalized_terms = list(dict.fromkeys(
            str(term).strip().casefold()
            for term in (cue_terms or [])
            if str(term).strip()
        ))

        cue_limit = max(1, min(int(cue_limit), 10))
        prediction_limit = max(1, min(int(prediction_limit), 20))
        row_limit = cue_limit * prediction_limit
        async with self.driver.session(database=_DB_NAME) as s:
            result = await s.run(
                "MATCH (cue:Concept) "
                "WHERE cue.name IS NOT NULL "
                "  AND size(trim(toString(cue.name))) >= 2 "
                "  AND ((size($cue_terms) > 0 "
                "        AND toLower(trim(toString(cue.name))) IN $cue_terms) "
                "    OR (size($cue_terms) = 0 "
                "        AND $message CONTAINS toLower(trim(toString(cue.name))))) "
                "WITH cue ORDER BY size(toString(cue.name)) DESC, "
                "  coalesce(cue.strength, 0.0) DESC LIMIT $cue_limit "
                "WITH collect(cue) AS cues UNWIND cues AS cue "
                "OPTIONAL MATCH (cue)-[rel:RELATES_TO]-(candidate:Concept) "
                "WHERE candidate IS NULL OR NOT candidate IN cues "
                "RETURN cue.id AS cue_id, cue.name AS cue_name, "
                "  candidate.id AS candidate_id, candidate.name AS candidate_name, "
                "  coalesce(rel.hebb_strength, rel.strength, 0.0) AS score "
                "ORDER BY score DESC LIMIT $row_limit",
                message=normalized,
                cue_terms=normalized_terms,
                cue_limit=cue_limit,
                row_limit=row_limit,
            )
            records = await result.fetch(row_limit)

        cues: list[dict] = []
        cue_seen: set[str] = set()
        predictions_by_id: dict[str, dict] = {}
        for record in records:
            cue_id = record["cue_id"]
            if cue_id and cue_id not in cue_seen:
                cue_seen.add(cue_id)
                cues.append({"id": cue_id, "name": record["cue_name"]})

            candidate_id = record["candidate_id"]
            if not candidate_id or candidate_id in cue_seen:
                continue
            score = float(record["score"] or 0.0)
            previous = predictions_by_id.get(candidate_id)
            if previous is None or score > previous["score"]:
                predictions_by_id[candidate_id] = {
                    "id": candidate_id,
                    "name": record["candidate_name"],
                    "score": score,
                }

        if not cues:
            return None

        predictions = sorted(
            predictions_by_id.values(),
            key=lambda item: item["score"],
            reverse=True,
        )[:prediction_limit]
        return {
            "cue_concepts": cues,
            "predicted_concepts": predictions,
            "captured_at": _now_iso(),
        }

    async def record_curiosity_outcome(
        self,
        snapshot: Optional[dict],
        experience_id: Optional[str],
        *,
        ema_alpha: float = 0.4,
        gate_threshold: float = 0.02,
        min_observations: int = 3,
    ) -> dict:
        """Score a pre-turn prediction and persist its learning-progress signal.

        Raw prediction error is recorded for observability, but only positive
        reduction of the error EMA can raise integration priority or create a
        CuriosityLog target.
        """
        if not snapshot or not experience_id:
            return {"status": "skipped", "reason": "missing_snapshot_or_experience"}

        cues = [item for item in snapshot.get("cue_concepts", []) if item.get("id")]
        predictions = [
            item for item in snapshot.get("predicted_concepts", []) if item.get("id")
        ]
        cue_ids = [item["id"] for item in cues]
        predicted_ids = [item["id"] for item in predictions]
        if not cue_ids:
            return {"status": "skipped", "reason": "no_known_cues"}

        async with self.driver.session(database=_DB_NAME) as s:
            result = await s.run(
                "MATCH (e:Experience {id: $experience_id}) "
                "OPTIONAL MATCH (e)-[:INVOLVES]->(actual:Concept) "
                "RETURN coalesce(e.emotional_salience, 0.5) AS salience, "
                "  collect({id: actual.id, name: actual.name}) AS actual_concepts",
                experience_id=experience_id,
            )
            record = await result.single()
            if not record:
                return {"status": "skipped", "reason": "experience_not_found"}

            actual = [
                item for item in record["actual_concepts"] if item and item.get("id")
            ]
            actual_ids = [item["id"] for item in actual]
            error = compute_prediction_error(predicted_ids, actual_ids, cue_ids)
            if error is None:
                return {"status": "skipped", "reason": "no_non_cue_outcome"}

            result = await s.run(
                "MATCH (c:Concept) WHERE c.id IN $cue_ids "
                "RETURN c.id AS id, c.name AS name, properties(c) AS props",
                cue_ids=cue_ids,
            )
            state_records = await result.fetch(len(cue_ids))

            states: list[dict] = []
            for state_record in state_records:
                props = dict(state_record["props"] or {})
                update = update_learning_progress(
                    error,
                    props.get("curiosity_error_ema"),
                    int(props.get("curiosity_observations") or 0),
                    alpha=ema_alpha,
                )
                states.append({
                    "id": state_record["id"],
                    "name": state_record["name"],
                    "error_ema": update.error_ema,
                    "learning_progress": update.learning_progress,
                    "observations": update.observations,
                })

            if not states:
                return {"status": "skipped", "reason": "cue_state_not_found"}

            now = _now_iso()
            await s.run(
                "UNWIND $states AS state MATCH (c:Concept {id: state.id}) "
                "SET c.curiosity_error_ema = state.error_ema, "
                "    c.learning_progress = state.learning_progress, "
                "    c.curiosity_observations = state.observations, "
                "    c.curiosity_updated_at = $now",
                states=states,
                now=now,
            )

            # Region-level view mirrors the aggregated concept signal for live
            # monitoring without adding a second independent learning rule.
            await s.run(
                "UNWIND $states AS state MATCH (c:Concept {id: state.id}) "
                "MATCH (c)-[:MAPPED_TO|ALSO_REPRESENTED_IN]->(br:BrainRegion) "
                "WITH br, avg(state.error_ema) AS error_ema, "
                "  max(state.learning_progress) AS learning_progress "
                "SET br.curiosity_error_ema = error_ema, "
                "    br.learning_progress = learning_progress, "
                "    br.curiosity_updated_at = $now",
                states=states,
                now=now,
            )

            primary = max(states, key=lambda item: item["learning_progress"])
            learning_progress = float(primary["learning_progress"])
            gated = should_open_curiosity_gate(
                learning_progress,
                primary["observations"],
                threshold=gate_threshold,
                min_observations=min_observations,
            )
            target_id = select_curiosity_target(cue_ids, predicted_ids, actual_ids)
            actual_by_id = {item["id"]: item.get("name") for item in actual}
            target_name = actual_by_id.get(target_id) if target_id else None
            integration_priority = compute_integration_priority(
                float(record["salience"] or 0.5),
                learning_progress,
            )

            await s.run(
                "MATCH (e:Experience {id: $experience_id}) "
                "SET e.prediction_error = $prediction_error, "
                "    e.learning_progress = $learning_progress, "
                "    e.integration_priority = $integration_priority, "
                "    e.curiosity_gated = $gated, "
                "    e.curiosity_cue_ids = $cue_ids, "
                "    e.predicted_concept_ids = $predicted_ids, "
                "    e.curiosity_target_id = $target_id, "
                "    e.curiosity_scored_at = $now",
                experience_id=experience_id,
                prediction_error=error,
                learning_progress=learning_progress,
                integration_priority=integration_priority,
                gated=gated,
                cue_ids=cue_ids,
                predicted_ids=predicted_ids,
                target_id=target_id,
                now=now,
            )

            curiosity_log_id = None
            if gated and target_id and target_name:
                target_key = f"{primary['id']}:{target_id}"
                deterministic_log_id = str(uuid.uuid5(
                    uuid.NAMESPACE_URL,
                    f"baby-brain-learning-progress:{target_key}",
                ))
                curiosity_query = (
                    f"{primary['name']}와(과) {target_name}의 관계를 더 알아보자"
                )
                curiosity_priority = round(min(0.9, 0.5 + 2.0 * learning_progress), 6)
                result = await s.run(
                    "MATCH (e:Experience {id: $experience_id}) "
                    "MERGE (cl:CuriosityLog {id: $curiosity_log_id}) "
                    "ON CREATE SET cl.exploration_count = 0, cl.created_at = datetime($now) "
                    "SET cl.source = 'learning_progress', cl.target_key = $target_key, "
                    "  cl.query = $curiosity_query, cl.query_type = 'concept_relation', "
                    "  cl.priority = CASE WHEN coalesce(cl.priority, 0.0) < $priority "
                    "    THEN $priority ELSE cl.priority END, "
                    "  cl.status = CASE WHEN cl.status IS NULL "
                    "      OR cl.status IN ['learned', 'failed'] THEN 'pending' "
                    "    ELSE cl.status END, cl.updated_at = datetime($now), "
                    "  cl.learning_progress = $learning_progress, "
                    "  cl.prediction_error = $prediction_error "
                    "MERGE (cl)-[:TRIGGERED_BY]->(e) "
                    "RETURN cl.id AS id",
                    experience_id=experience_id,
                    curiosity_log_id=deterministic_log_id,
                    target_key=target_key,
                    curiosity_query=curiosity_query,
                    priority=curiosity_priority,
                    learning_progress=learning_progress,
                    prediction_error=error,
                    now=now,
                )
                log_record = await result.single()
                curiosity_log_id = log_record["id"] if log_record else None

        return {
            "status": "recorded",
            "prediction_error": round(float(error), 6),
            "learning_progress": round(learning_progress, 6),
            "integration_priority": integration_priority,
            "gated": gated,
            "target_id": target_id,
            "curiosity_log_id": curiosity_log_id,
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
        """UserModel + 최근 관심사 + 통계 조회 (system prompt 구성용).

        접근제어(2026-07 identity): access_tier='owner_private' Concept는
        owner clearance에서만 회상된다. clearance는 speaker_id→:Person role로 도출.
        신뢰(토큰 검증)는 endpoint 책임 — 여기 도달하는 speaker_id는 이미 강등 반영됨.
        """
        clearance = await self.resolve_speaker_clearance(speaker_id)
        async with self.driver.session(database=_DB_NAME) as s:
            result = await s.run(
                "MATCH (u:UserModel {speaker_id: $sid}) "
                "OPTIONAL MATCH (u)-[r:INTERESTED_IN]->(c:Concept) "
                "  WHERE coalesce(c.access_tier, 'public') = 'public' OR $clearance = 'owner' "
                "WITH u, c, r ORDER BY r.strength DESC LIMIT 10 "
                "RETURN u, collect(CASE WHEN c IS NOT NULL "
                "  THEN {name: c.name, strength: r.strength} ELSE null END) AS interests",
                sid=speaker_id, clearance=clearance,
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

    async def resolve_speaker_clearance(self, speaker_id: str) -> str:
        """speaker_id의 접근 등급: 'owner' | 'public' (identity graph 기준).

        owner = :Person{role:'owner'}가 IDENTIFIED_BY 하는 speaker, 또는 primary alias.
        신뢰(토큰)는 endpoint 책임 — 여기선 identity graph만 본다.
        docs/IDENTITY_ACCESS_CONTROL.md STEP 4.
        """
        if speaker_id in ("self", "나", "박재현", "owner_pjh"):
            return "owner"
        async with self.driver.session(database=_DB_NAME) as s:
            r = await s.run(
                "MATCH (p:Person {role:'owner'})-[:IDENTIFIED_BY]->(u:UserModel {speaker_id:$sid}) "
                "RETURN count(p) AS n",
                sid=speaker_id,
            )
            rec = await r.single()
            return "owner" if rec and rec["n"] > 0 else "public"

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

        # 5. CLS region reweighting: hippocampus → cortex 이동
        #    근거: McClelland, McNaughton, O'Reilly 1995 (Psych Rev)
        #    수면 중 replay된 concept의 기억은 점진적으로 hippocampus에서 cortex로 이동.
        reweighted = 0
        if combined_ids:
            async with self.driver.session(database=_DB_NAME) as s:
                # 5a. hippocampus weight -0.05 (cap at 0)
                result = await s.run(
                    "MATCH (c:Concept) WHERE c.id IN $ids "
                    "MATCH (c)-[h:MAPPED_TO|ALSO_REPRESENTED_IN]->(:BrainRegion {name: 'hippocampus'}) "
                    "SET h.weight = CASE WHEN coalesce(h.weight, 0.0) > 0.05 "
                    "                     THEN h.weight - 0.05 ELSE 0.0 END, "
                    "    h.updated_at = $now "
                    "RETURN count(h) AS n",
                    ids=combined_ids,
                    now=_now_iso(),
                )
                rec = await result.single()
                n_hip = rec["n"] if rec else 0

                # 5b. cortical weight +0.02 (temporal, prefrontal, parietal) cap at 1.0
                result = await s.run(
                    "MATCH (c:Concept) WHERE c.id IN $ids "
                    "MATCH (c)-[r:MAPPED_TO|ALSO_REPRESENTED_IN]->(br:BrainRegion) "
                    "WHERE br.name IN ['temporal', 'prefrontal', 'parietal'] "
                    "SET r.weight = CASE WHEN coalesce(r.weight, 0.0) + 0.02 > 1.0 "
                    "                     THEN 1.0 "
                    "                     ELSE coalesce(r.weight, 0.0) + 0.02 END, "
                    "    r.updated_at = $now "
                    "RETURN count(r) AS n",
                    ids=combined_ids,
                    now=_now_iso(),
                )
                rec = await result.single()
                n_cortex = rec["n"] if rec else 0
                reweighted = n_hip + n_cortex
                if reweighted:
                    logger.debug(
                        f"CLS reweight: {n_hip} hippocampus -, {n_cortex} cortical + "
                        f"({len(combined_ids)} concepts)"
                    )

        return {
            "reactivated_count": len(combined_ids),
            "hebbian_updates": total_hebb,
            "cls_reweights": reweighted,
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
