"""
Baby AI API Server
Phase 2: Neo4j + Redis lifespan + 기본 엔드포인트

엔드포인트:
  GET  /health                  - 서버 상태
  GET  /api/state               - BabyState (Neo4j)
  GET  /api/brain/regions           - 뇌 영역 목록
  GET  /api/brain/concepts          - Concept 목록 (페이지네이션)
  GET  /api/brain/concept-relations - Concept 간 관계 목록 (brain 시각화용)
  GET  /api/brain/activation-summary - 뇌 활성화 heatmap + replay
  POST /api/conversation            - 대화 처리 (Neo4j Experience 저장)
  GET  /api/memory/consolidate      - 기억 통합 통계
  POST /api/memory/consolidate      - 기억 강화/약화 (수면 모드)
  GET  /api/events                  - SSE 스트림 (Redis Pub/Sub)

기존 엔드포인트 유지:
  POST /api/vision/process      - 이미지 처리
  GET  /api/vision/stats        - 시각 통계
  POST /api/process             - 일반 처리
"""

import asyncio
import json
import logging
import time
from contextlib import asynccontextmanager
from typing import Optional, AsyncGenerator

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import base64
import uvicorn

from .neo4j_db import init_driver, close_driver, get_brain_db, get_driver, _DB_NAME
from .concept_binding import extract_color_bindings, select_visual_cooc_concepts
from .redis_client import (
    init_redis, close_redis, get_redis,
    CHANNEL_BABY_STATE, CHANNEL_NEURON_ACTIVATION,
    CHANNEL_PENDING_QUESTION, CHANNEL_IMAGINATION,
    CHANNEL_EXPERIENCE,
    publish_pending_question,
    publish_neuron_activation,
)

logger = logging.getLogger(__name__)


# ── Lifespan ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 시작/종료 시 Neo4j + Redis 초기화/정리"""
    # 시작
    logger.info("Starting up: initializing Neo4j and Redis...")
    await init_driver()
    init_redis()
    # 스키마 + 시드 (멱등, 빈 DB 재시작 시 전체 재구축)
    try:
        _db = get_brain_db()
        await _db.ensure_indexes()
        await _db.seed_brain_regions()
        await _db.seed_region_connections()
        await _db.seed_identity_concepts()
    except Exception as e:
        logger.warning(f"schema/seed warning: {e}")
    logger.info("Neo4j + Redis ready")

    yield

    # 종료
    logger.info("Shutting down: closing Neo4j and Redis...")
    await close_driver()
    await close_redis()
    logger.info("Shutdown complete")


# ── FastAPI 앱 ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="Baby AI API",
    description="Baby AI Backend API - Neo4j + Redis",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request/Response Models ───────────────────────────────────────────────────

class ConversationRequest(BaseModel):
    message: str
    context: Optional[dict] = None


class ConversationResponse(BaseModel):
    output: str
    success: bool
    emotional_state: dict
    development_stage: int
    experience_id: Optional[str] = None


class StateResponse(BaseModel):
    emotional_state: dict
    development_stage: int
    experience_count: int
    capabilities: list[str]


class ConsolidateRequest(BaseModel):
    mode: str = "full"          # "full" | "reinforce_only" | "decay_only"
    decay_rate: float = 0.01


class ReplayRequest(BaseModel):
    salience_threshold: float = 0.4
    max_experiences: int = 10
    hebb_delta: float = 0.02
    trigger_type: str = "idle"  # "idle" | "manual" | "sleep"


class VisionProcessRequest(BaseModel):
    image_data: str
    mime_type: str = "image/jpeg"
    prompt: Optional[str] = None


class VisionProcessResponse(BaseModel):
    visual_experience: dict
    emotional_changes: dict
    success: bool
    message: Optional[str] = None


# ── A4.3: Quest 3S Passthrough → Concept 직접 수신 ─────────────────────────────
class QuestImageMeta(BaseModel):
    width: int
    height: int
    camera: Optional[str] = None


class QuestConceptsRequest(BaseModel):
    timestamp: str
    source: str = "quest_passthrough"
    model: str = "SmolVLM-500M-Q8"
    image_meta: Optional[QuestImageMeta] = None
    vlm_response: str
    concepts_raw: list[str]
    inference_ms: Optional[int] = None
    jpeg_path: Optional[str] = None


class QuestConceptsResponse(BaseModel):
    experience_id: Optional[str]
    concepts_inserted: int
    concepts_existing: int
    total_unique_in_db: int
    bindings_created: int = 0
    bindings_reinforced: int = 0
    bindings_skipped: int = 0
    success: bool
    message: Optional[str] = None


class ProcessRequest(BaseModel):
    task: str
    context: Optional[dict] = None


class ProcessResponse(BaseModel):
    output: str
    success: bool
    emotional_state: dict
    development_stage: int


class MetacognitionRequest(BaseModel):
    action: str = "get_stats"   # get_stats | get_strategies | get_evaluations | evaluate
    limit: int = 10
    context: Optional[dict] = None


class GoalsRequest(BaseModel):
    action: str = "generate"    # generate | get_goals | complete | update
    development_stage: Optional[int] = None
    current_emotions: Optional[dict] = None
    goal_id: Optional[str] = None
    outcome: Optional[str] = None
    insight: Optional[str] = None
    experience_id: Optional[str] = None
    limit: int = 10


class FeedbackRequest(BaseModel):
    experience_id: str
    rating: int                   # 1~5
    feedback_text: Optional[str] = None
    is_helpful: Optional[bool] = None
    is_accurate: Optional[bool] = None
    is_appropriate: Optional[bool] = None


class PendingQuestionCreate(BaseModel):
    question: str
    source: str = "conversation"
    curiosity_log_id: Optional[str] = None


class PendingQuestionAnswer(BaseModel):
    answer: str
    answer_confidence: float = 0.5


# ── Health Check ──────────────────────────────────────────────────────────────

@app.get("/health")
async def health_check():
    """서버 상태 확인"""
    return {"status": "healthy", "version": "2.0.0", "backend": "neo4j+redis"}


# ── State ─────────────────────────────────────────────────────────────────────

@app.get("/api/state", response_model=StateResponse)
async def get_state():
    """BabyState 조회"""
    try:
        db = get_brain_db()
        state = await db.get_baby_state()
        if not state:
            return StateResponse(
                emotional_state={},
                development_stage=0,
                experience_count=0,
                capabilities=[],
            )

        # emotion_snapshot에서 감정 상태 추출
        emotion_state = {}
        snap = state.get("emotion_snapshot")
        if snap:
            try:
                emotion_state = json.loads(snap) if isinstance(snap, str) else snap
            except (json.JSONDecodeError, TypeError):
                pass

        stage = state.get("development_stage", 0)
        capabilities = _get_capabilities(stage)

        return StateResponse(
            emotional_state=emotion_state or {
                "curiosity": state.get("curiosity", 0.5),
                "joy": state.get("joy", 0.5),
                "fear": state.get("fear", 0.1),
                "surprise": state.get("surprise", 0.3),
                "frustration": state.get("frustration", 0.1),
                "boredom": state.get("boredom", 0.1),
            },
            development_stage=stage,
            experience_count=state.get("experience_count", 0),
            capabilities=capabilities,
        )
    except Exception as e:
        logger.error(f"get_state error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _get_capabilities(stage: int) -> list[str]:
    caps = ["observe", "respond"]
    if stage >= 2:
        caps.append("predict")
    if stage >= 3:
        caps.extend(["simulate", "imagine"])
    if stage >= 4:
        caps.append("causal_reason")
    if stage >= 5:
        caps.extend(["meta_cognition", "autonomous_goal"])
    return caps


# ── Brain ─────────────────────────────────────────────────────────────────────

@app.get("/api/brain/regions")
async def get_brain_regions():
    """뇌 영역 목록"""
    try:
        db = get_brain_db()
        regions = await db.get_brain_regions()
        return {"regions": regions, "count": len(regions)}
    except Exception as e:
        logger.error(f"get_brain_regions error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/brain/concepts")
async def get_concepts(limit: int = 100, category: Optional[str] = None):
    """Concept 목록 (strength 내림차순)"""
    try:
        db = get_brain_db()
        concepts = await db.get_all_concepts()
        if category:
            concepts = [c for c in concepts if c.get("category") == category]
        # embedding은 큰 배열이므로 제거 후 반환
        for c in concepts:
            c.pop("embedding", None)
        return {"concepts": concepts[:limit], "total": len(concepts)}
    except Exception as e:
        logger.error(f"get_concepts error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/brain/concept-relations")
async def get_concept_relations(limit: int = 200):
    """Concept 간 RELATES_TO 관계 목록 (brain 시각화용).

    Frontend (useBrainData.ts RawConceptRelation)가 기대하는 필드:
      - id, from_concept_id, to_concept_id, strength, relation_type, evidence_count
    evidence_count가 누락되면 synapseMap에 NaN이 전파되어 THREE.js BufferGeometry가 깨진다.
    """
    try:
        async with get_driver().session(database=_DB_NAME) as s:
            result = await s.run(
                "MATCH (src:Concept)-[r:RELATES_TO]->(tgt:Concept) "
                "RETURN "
                "  coalesce(r.id, toString(elementId(r))) AS id, "
                "  src.id AS from_concept_id, "
                "  tgt.id AS to_concept_id, "
                "  coalesce(r.strength, 0.5) AS strength, "
                "  coalesce(r.relation_type, 'related') AS relation_type, "
                "  coalesce(r.evidence_count, 1) AS evidence_count "
                "ORDER BY r.strength DESC LIMIT $limit",
                limit=limit,
            )
            records = await result.fetch(limit)
            relations = [
                {
                    "id": rec["id"],
                    "from_concept_id": rec["from_concept_id"],
                    "to_concept_id": rec["to_concept_id"],
                    "strength": round(float(rec["strength"]), 3),
                    "relation_type": rec["relation_type"],
                    "evidence_count": int(rec["evidence_count"]),
                }
                for rec in records
            ]
        return {"relations": relations, "total": len(relations)}
    except Exception as e:
        logger.error(f"get_concept_relations error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/brain/hebb-stats")
async def get_hebb_stats():
    """Hebbian 학습 통계 (총 RELATES_TO 수, Hebbian 강화 수, 평균/최대 hebb_strength)"""
    try:
        db = get_brain_db()
        stats = await db.get_hebb_stats()
        return {"success": True, "stats": stats}
    except Exception as e:
        logger.error(f"get_hebb_stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/brain/activation-summary")
async def get_activation_summary():
    """
    뇌 활성화 요약 (useNeuronActivations 초기 heatmap + replay용)

    - heatmap: 최근 Experience에 INVOLVES된 Concept별 활성화 집계
    - replay: 최근 spreading activation 이벤트 (최대 50개)
    """
    try:
        drv = get_driver()

        async with drv.session(database=_DB_NAME) as s:
            # heatmap: 최근 100개 Experience → INVOLVES → Concept → MAPPED_TO → BrainRegion
            r = await s.run(
                "MATCH (e:Experience)-[inv:INVOLVES]->(c:Concept) "
                "WHERE e.created_at IS NOT NULL "
                "WITH c, count(inv) AS act_count, avg(coalesce(inv.relevance, 0.5)) AS avg_intensity "
                "OPTIONAL MATCH (c)-[:MAPPED_TO]->(br:BrainRegion) "
                "RETURN c.id AS concept_id, br.id AS brain_region_id, "
                "  act_count AS activation_count, avg_intensity "
                "ORDER BY act_count DESC LIMIT 100"
            )
            heatmap_records = await r.fetch(100)
            heatmap = [
                {
                    "concept_id": rec["concept_id"],
                    "brain_region_id": rec["brain_region_id"],
                    "activation_count": rec["activation_count"],
                    "avg_intensity": round(float(rec["avg_intensity"] or 0.5), 3),
                }
                for rec in heatmap_records
            ]

            # replay: 최근 Experience에 연결된 Concept (최대 50개, 활성화 재연용)
            r2 = await s.run(
                "MATCH (e:Experience)-[inv:INVOLVES]->(c:Concept) "
                "WHERE e.created_at IS NOT NULL "
                "OPTIONAL MATCH (c)-[:MAPPED_TO]->(br:BrainRegion) "
                "RETURN c.id AS concept_id, br.id AS brain_region_id, "
                "  coalesce(inv.relevance, 0.5) AS intensity, "
                "  'conversation' AS trigger_type, "
                "  e.created_at AS created_at "
                "ORDER BY e.created_at DESC LIMIT 50"
            )
            replay_records = await r2.fetch(50)
            replay = [
                {
                    "concept_id": rec["concept_id"],
                    "brain_region_id": rec["brain_region_id"],
                    "intensity": round(float(rec["intensity"] or 0.5), 3),
                    "trigger_type": rec["trigger_type"],
                    "created_at": str(rec["created_at"]) if rec["created_at"] else None,
                }
                for rec in replay_records
            ]

        return {"heatmap": heatmap, "replay": replay}
    except Exception as e:
        logger.error(f"get_activation_summary error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Conversation ──────────────────────────────────────────────────────────────

@app.post("/api/conversation", response_model=ConversationResponse)
async def conversation(request: ConversationRequest):
    """
    대화 처리 (Phase 2 기본 버전)

    1. BabyState 조회 → 감정 상태
    2. conversation_handler 호출
    3. Experience Neo4j 저장 확인
    """
    try:
        from .conversation_handler import handle_conversation
        result = await handle_conversation(
            message=request.message,
            context=request.context or {},
        )
        return ConversationResponse(**result)
    except ImportError:
        # conversation_handler 미구현 시 fallback
        db = get_brain_db()
        state = await db.get_baby_state() or {}
        stage = state.get("development_stage", 0)
        exp = await db.insert_experience(
            task=request.message,
            task_type="conversation",
            output="[conversation_handler not yet implemented]",
            success=True,
            emotional_salience=0.5,
            development_stage=stage,
        )
        return ConversationResponse(
            output="대화 처리 중 (conversation_handler 구현 전)",
            success=True,
            emotional_state={},
            development_stage=stage,
            experience_id=exp.get("id"),
        )
    except Exception as e:
        logger.error(f"conversation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Memory Consolidation ──────────────────────────────────────────────────────

@app.get("/api/memory/consolidate")
async def get_consolidate_stats():
    """
    기억 통합 통계 조회 (MemoryConsolidationCard overview 탭용)

    반환 필드:
      total_consolidations     - SleepLog 노드 수
      last_consolidation       - 가장 최근 SleepLog.created_at
      total_memories_strengthened - 전체 SleepLog reinforced_count 합계
      total_memories_decayed   - 전체 SleepLog decayed_count 합계
      total_patterns_promoted  - 전체 SleepLog patterns_promoted 합계
      procedural_memory_count  - Procedure 노드 수
      semantic_links_count     - RELATES_TO 관계 수
    """
    try:
        drv = get_driver()
        async with drv.session(database=_DB_NAME) as s:
            r = await s.run(
                "OPTIONAL MATCH (sl:SleepLog) "
                "WITH count(sl) AS sleep_count, "
                "  sum(coalesce(sl.reinforced_count, 0)) AS total_reinforced, "
                "  sum(coalesce(sl.decayed_count, 0)) AS total_decayed, "
                "  sum(coalesce(sl.patterns_promoted, 0)) AS total_promoted, "
                "  max(sl.created_at) AS last_sleep "
                "OPTIONAL MATCH (p:Procedure) "
                "WITH sleep_count, total_reinforced, total_decayed, total_promoted, last_sleep, "
                "  count(p) AS proc_count "
                "OPTIONAL MATCH ()-[rel:RELATES_TO]->() "
                "RETURN sleep_count, total_reinforced, total_decayed, total_promoted, "
                "  last_sleep, proc_count, count(rel) AS rel_count"
            )
            rec = await r.single()

        return {
            "success": True,
            "stats": {
                "total_consolidations": rec["sleep_count"] if rec else 0,
                "last_consolidation": str(rec["last_sleep"]) if rec and rec["last_sleep"] else None,
                "total_memories_strengthened": rec["total_reinforced"] if rec else 0,
                "total_memories_decayed": rec["total_decayed"] if rec else 0,
                "total_patterns_promoted": rec["total_promoted"] if rec else 0,
                "procedural_memory_count": rec["proc_count"] if rec else 0,
                "semantic_links_count": rec["rel_count"] if rec else 0,
            },
        }
    except Exception as e:
        logger.error(f"get_consolidate_stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/memory/consolidate")
async def consolidate_memory(request: ConsolidateRequest):
    """
    기억 강화/약화 (수면 모드 대체)

    - reinforce: emotional_salience > 0.3인 Experience 강화
    - decay: 모든 RELATES_TO 관계 강도 감쇠
    """
    try:
        db = get_brain_db()
        results = {}

        if request.mode in ("full", "reinforce_only"):
            # emotional_salience 높은 기억 강화
            async with get_driver().session(database=_DB_NAME) as s:
                r = await s.run(
                    "MATCH (e:Experience) WHERE e.emotional_salience > 0.3 "
                    "SET e.strength = CASE WHEN coalesce(e.strength, 0.5) + 0.05 > 1.0 THEN 1.0 "
                    "                      ELSE coalesce(e.strength, 0.5) + 0.05 END "
                    "RETURN count(e) AS n"
                )
                rec = await r.single()
                results["reinforced"] = rec["n"] if rec else 0

        if request.mode in ("full", "decay_only"):
            await db.decay_connections(decay_rate=request.decay_rate)
            results["decayed"] = True

        # E2-2: Temporal pattern detection (배치)
        if request.mode == "full":
            try:
                state = await db.get_baby_state() or {}
                patterns = await db.detect_temporal_patterns(
                    development_stage=state.get("development_stage", 0)
                )
                results["temporal_patterns_detected"] = len(patterns)
                transitions = await db.compute_transition_probabilities()
                results["transition_probabilities_updated"] = transitions
            except Exception as tp_err:
                logger.warning(f"temporal pattern detection error: {tp_err}")

        return {"status": "ok", "mode": request.mode, **results}
    except Exception as e:
        logger.error(f"consolidate error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/memory/replay")
async def memory_replay(request: ReplayRequest):
    """
    기억 재생 (Phase C3) — 수면 중 고감정 경험의 개념 네트워크를 재활성화

    1. 고감정 경험 조회 → INVOLVES된 개념 수집
    2. Spreading activation으로 관련 개념 전파
    3. Offline Hebbian learning (delta=0.02)
    4. 재활성화 이벤트를 SSE로 브라우저에 전송 (뇌가 반짝이는 효과)
    5. SleepLog 기록
    """
    import time as _time
    start_ms = int(_time.time() * 1000)

    try:
        db = get_brain_db()
        replay_result = await db.replay_recent_memories(
            salience_threshold=request.salience_threshold,
            max_experiences=request.max_experiences,
            hebb_delta=request.hebb_delta,
        )

        # SSE로 재활성화 이벤트 브로드캐스트 (뇌 시각화)
        if replay_result["activation_events"]:
            await publish_neuron_activation(replay_result["activation_events"])

        # SleepLog 기록
        duration_ms = int(_time.time() * 1000) - start_ms
        state = await db.get_baby_state() or {}
        sleep_log = await db.create_sleep_log(
            trigger_type=request.trigger_type,
            replay_count=replay_result["reactivated_count"],
            reinforced_count=replay_result["hebbian_updates"],
            duration_ms=duration_ms,
            development_stage=state.get("development_stage", 0),
        )

        return {
            "success": True,
            "experiences_replayed": replay_result["experiences_replayed"],
            "reactivated_count": replay_result["reactivated_count"],
            "hebbian_updates": replay_result["hebbian_updates"],
            "activation_events_sent": len(replay_result["activation_events"]),
            "sleep_log_id": sleep_log.get("id"),
            "duration_ms": duration_ms,
        }
    except Exception as e:
        logger.error(f"memory_replay error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── SSE Stream ────────────────────────────────────────────────────────────────

@app.get("/api/events")
async def event_stream(request: Request):
    """
    SSE 스트림 - Redis Pub/Sub 채널 구독

    구독 채널:
      baby-ai:baby_state, baby-ai:neuron_activation,
      baby-ai:pending_question, baby-ai:imagination, baby-ai:experience
    """
    async def generator() -> AsyncGenerator[str, None]:
        redis = get_redis()
        # SSE용 별도 연결 (Pub/Sub은 전용 연결 필요)
        pubsub_client = redis.pubsub()
        try:
            await pubsub_client.subscribe(
                CHANNEL_BABY_STATE,
                CHANNEL_NEURON_ACTIVATION,
                CHANNEL_PENDING_QUESTION,
                CHANNEL_IMAGINATION,
                CHANNEL_EXPERIENCE,
            )
            last_ping = time.time()

            async for msg in pubsub_client.listen():
                if await request.is_disconnected():
                    break

                if msg["type"] == "message":
                    yield f"data: {msg['data']}\n\n"

                # 30초마다 keep-alive 전송 (proxy timeout 방지)
                if time.time() - last_ping > 30:
                    yield ": ping\n\n"
                    last_ping = time.time()
        finally:
            await pubsub_client.unsubscribe()
            await pubsub_client.aclose()

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={
            "X-Accel-Buffering": "no",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


# ── Metacognition ─────────────────────────────────────────────────────────────

@app.post("/api/metacognition")
async def metacognition(request: MetacognitionRequest):
    """
    메타인지 처리 (Phase 4b 스텁 - Neo4j SelfEvaluationLog 조회)

    action:
      get_stats        - 전체 통계 반환
      get_strategies   - 전략 효과성 목록 (Neo4j 미구현 → 빈 배열)
      get_evaluations  - 최근 자기평가 로그
      evaluate         - 새 평가 실행 (향후 Phase 4c)
    """
    try:
        drv = get_driver()
        action = request.action

        if action == "get_stats":
            async with drv.session(database=_DB_NAME) as s:
                r = await s.run(
                    "MATCH (n:SelfEvaluationLog) "
                    "RETURN count(n) AS total, "
                    "  avg(coalesce(n.success_rate, 0.5)) AS avg_success, "
                    "  avg(coalesce(n.confidence, 0.5)) AS avg_confidence "
                )
                rec = await r.single()
            return {
                "action": "get_stats",
                "stats": {
                    "total_evaluations": rec["total"] if rec else 0,
                    "avg_success_rate": round(float(rec["avg_success"] or 0.5), 3) if rec else 0.5,
                    "avg_confidence": round(float(rec["avg_confidence"] or 0.5), 3) if rec else 0.5,
                },
            }

        elif action == "get_evaluations":
            async with drv.session(database=_DB_NAME) as s:
                r = await s.run(
                    "MATCH (n:SelfEvaluationLog) "
                    "RETURN n.id AS id, n.task_type AS task_type, "
                    "  n.success_rate AS success_rate, n.confidence AS confidence, "
                    "  n.created_at AS created_at "
                    "ORDER BY n.created_at DESC LIMIT $limit",
                    limit=request.limit,
                )
                records = await r.fetch(request.limit)
            evaluations = [
                {
                    "id": rec["id"],
                    "task_type": rec["task_type"],
                    "success_rate": round(float(rec["success_rate"] or 0.5), 3),
                    "confidence": round(float(rec["confidence"] or 0.5), 3),
                    "created_at": str(rec["created_at"]) if rec["created_at"] else None,
                }
                for rec in records
            ]
            return {"action": "get_evaluations", "evaluations": evaluations}

        elif action == "get_strategies":
            # strategy_effectiveness는 Neo4j 미구현 → 빈 목록 반환
            return {"action": "get_strategies", "strategies": []}

        else:
            # evaluate 등 향후 구현
            return {"action": action, "status": "not_implemented", "message": f"Action '{action}' not yet implemented in FastAPI"}

    except Exception as e:
        logger.error(f"metacognition error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/metacognition")
async def get_metacognition_stats():
    """메타인지 통계 조회 (GET 버전)"""
    try:
        drv = get_driver()
        async with drv.session(database=_DB_NAME) as s:
            r = await s.run(
                "MATCH (n:SelfEvaluationLog) "
                "RETURN count(n) AS total, "
                "  avg(coalesce(n.success_rate, 0.5)) AS avg_success "
            )
            rec = await r.single()
        return {
            "stats": {
                "total_evaluations": rec["total"] if rec else 0,
                "avg_success_rate": round(float(rec["avg_success"] or 0.5), 3) if rec else 0.5,
            }
        }
    except Exception as e:
        logger.error(f"get_metacognition_stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Autonomous Goals ───────────────────────────────────────────────────────────

@app.post("/api/goals")
async def goals(request: GoalsRequest):
    """
    자율 목표 처리 (Phase 4b 스텁 - Neo4j AutonomousGoal 노드 CRUD)

    action:
      generate    - 새 목표 생성 (현재 상태 기반 → 향후 LLM 연동)
      get_goals   - 활성 목표 목록
      complete    - 목표 완료 처리
      update      - 목표 업데이트
    """
    try:
        drv = get_driver()
        action = request.action

        if action == "get_goals":
            async with drv.session(database=_DB_NAME) as s:
                r = await s.run(
                    "MATCH (g:AutonomousGoal) "
                    "WHERE g.status = 'active' OR g.status IS NULL "
                    "RETURN g.id AS id, g.goal_type AS goal_type, "
                    "  g.description AS description, g.status AS status, "
                    "  g.combined_motivation AS combined_motivation, "
                    "  g.created_at AS created_at "
                    "ORDER BY coalesce(g.combined_motivation, 0.5) DESC LIMIT $limit",
                    limit=request.limit,
                )
                records = await r.fetch(request.limit)
            goals_list = [
                {
                    "id": rec["id"],
                    "goal_type": rec["goal_type"] or "epistemic",
                    "description": rec["description"] or "",
                    "status": rec["status"] or "active",
                    "combined_motivation": round(float(rec["combined_motivation"] or 0.5), 3),
                    "created_at": str(rec["created_at"]) if rec["created_at"] else None,
                }
                for rec in records
            ]
            return {"action": "get_goals", "goals": goals_list, "count": len(goals_list)}

        elif action == "generate":
            # 향후 LLM 연동 (Phase 4c) — 현재는 상태 조회 후 stub 반환
            db = get_brain_db()
            state = await db.get_baby_state() or {}
            stage = request.development_stage if request.development_stage is not None else state.get("development_stage", 0)
            return {
                "action": "generate",
                "status": "stub",
                "message": "Goal generation not yet implemented in FastAPI (Phase 4c)",
                "development_stage": stage,
            }

        elif action == "complete" and request.goal_id:
            async with drv.session(database=_DB_NAME) as s:
                await s.run(
                    "MATCH (g:AutonomousGoal {id: $goal_id}) "
                    "SET g.status = 'completed', g.completed_at = datetime()",
                    goal_id=request.goal_id,
                )
            return {"action": "complete", "goal_id": request.goal_id, "status": "completed"}

        else:
            return {"action": action, "status": "not_implemented"}

    except Exception as e:
        logger.error(f"goals error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/goals")
async def get_goals(limit: int = 10):
    """활성 목표 목록 조회 (GET 버전)"""
    try:
        drv = get_driver()
        async with drv.session(database=_DB_NAME) as s:
            r = await s.run(
                "MATCH (g:AutonomousGoal) "
                "WHERE g.status = 'active' OR g.status IS NULL "
                "RETURN g.id AS id, g.goal_type AS goal_type, "
                "  g.description AS description, g.status AS status, "
                "  g.combined_motivation AS combined_motivation "
                "ORDER BY coalesce(g.combined_motivation, 0.5) DESC LIMIT $limit",
                limit=limit,
            )
            records = await r.fetch(limit)
        goals_list = [
            {
                "id": rec["id"],
                "goal_type": rec["goal_type"] or "epistemic",
                "description": rec["description"] or "",
                "status": rec["status"] or "active",
                "combined_motivation": round(float(rec["combined_motivation"] or 0.5), 3),
            }
            for rec in records
        ]
        return {"goals": goals_list, "count": len(goals_list)}
    except Exception as e:
        logger.error(f"get_goals error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Conversation Feedback (Textual Backpropagation) ───────────────────────────

@app.post("/api/conversation/feedback")
async def submit_feedback(request: FeedbackRequest):
    """
    대화 피드백 제출 (Phase 4c - Neo4j 기반 textual backpropagation)

    1. experience_id로 Experience 노드 조회
    2. rating → 강화 방향 결정 (1-2: 약화, 4-5: 강화)
    3. Experience에 INVOLVES된 Concept의 strength 업데이트
    4. Feedback 메타데이터를 Experience 노드에 저장
    """
    if request.rating < 1 or request.rating > 5:
        raise HTTPException(status_code=400, detail="rating must be between 1 and 5")

    try:
        drv = get_driver()

        # rating → strength delta 매핑
        # 5점: +0.10, 4점: +0.05, 3점: 0, 2점: -0.05, 1점: -0.10
        rating_delta = {1: -0.10, 2: -0.05, 3: 0.0, 4: 0.05, 5: 0.10}
        delta = rating_delta.get(request.rating, 0.0)

        async with drv.session(database=_DB_NAME) as s:
            # 1. Experience 존재 확인
            r = await s.run(
                "MATCH (e:Experience {id: $exp_id}) RETURN e.id AS id",
                exp_id=request.experience_id,
            )
            rec = await r.single()
            if not rec:
                raise HTTPException(status_code=404, detail=f"Experience {request.experience_id} not found")

            # 2. 피드백 메타데이터를 Experience에 저장
            await s.run(
                "MATCH (e:Experience {id: $exp_id}) "
                "SET e.feedback_rating = $rating, "
                "    e.feedback_text = $text, "
                "    e.feedback_at = datetime()",
                exp_id=request.experience_id,
                rating=request.rating,
                text=request.feedback_text or "",
            )

            # 3. delta가 0이 아닐 때만 Concept strength 업데이트
            concepts_updated = 0
            if delta != 0.0:
                r2 = await s.run(
                    "MATCH (e:Experience {id: $exp_id})-[:INVOLVES]->(c:Concept) "
                    "SET c.strength = CASE "
                    "  WHEN coalesce(c.strength, 0.5) + $delta > 1.0 THEN 1.0 "
                    "  WHEN coalesce(c.strength, 0.5) + $delta < 0.0 THEN 0.0 "
                    "  ELSE coalesce(c.strength, 0.5) + $delta "
                    "END "
                    "RETURN count(c) AS n",
                    exp_id=request.experience_id,
                    delta=delta,
                )
                r2_rec = await r2.single()
                concepts_updated = r2_rec["n"] if r2_rec else 0

        logger.info(f"Feedback submitted: exp={request.experience_id}, rating={request.rating}, concepts_updated={concepts_updated}")

        return {
            "success": True,
            "experience_id": request.experience_id,
            "rating": request.rating,
            "delta": delta,
            "concepts_updated": concepts_updated,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"feedback error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/conversation/feedback")
async def get_feedback_data(action: str = "stats", limit: int = 20, feedback_id: Optional[str] = None):
    """
    피드백 히스토리/통계 조회

    action:
      stats   - 전체 피드백 통계
      history - 최근 피드백 목록
      impact  - 특정 피드백의 영향 (feedback_id 필요)
    """
    try:
        drv = get_driver()

        if action == "stats":
            async with drv.session(database=_DB_NAME) as s:
                r = await s.run(
                    "MATCH (e:Experience) WHERE e.feedback_rating IS NOT NULL "
                    "RETURN count(e) AS total, "
                    "  avg(e.feedback_rating) AS avg_rating, "
                    "  count(CASE WHEN e.feedback_rating >= 4 THEN 1 END) AS positive, "
                    "  count(CASE WHEN e.feedback_rating <= 2 THEN 1 END) AS negative"
                )
                rec = await r.single()
            return {
                "success": True,
                "stats": {
                    "total_feedback": rec["total"] if rec else 0,
                    "avg_rating": round(float(rec["avg_rating"] or 0), 2) if rec else 0,
                    "positive_count": rec["positive"] if rec else 0,
                    "negative_count": rec["negative"] if rec else 0,
                },
            }

        elif action == "history":
            async with drv.session(database=_DB_NAME) as s:
                r = await s.run(
                    "MATCH (e:Experience) WHERE e.feedback_rating IS NOT NULL "
                    "RETURN e.id AS id, e.task AS task, e.feedback_rating AS rating, "
                    "  e.feedback_text AS feedback_text, e.feedback_at AS feedback_at "
                    "ORDER BY e.feedback_at DESC LIMIT $limit",
                    limit=limit,
                )
                records = await r.fetch(limit)
            history = [
                {
                    "id": rec["id"],
                    "task": rec["task"],
                    "rating": rec["rating"],
                    "feedback_text": rec["feedback_text"],
                    "feedback_at": str(rec["feedback_at"]) if rec["feedback_at"] else None,
                }
                for rec in records
            ]
            return {"success": True, "history": history}

        elif action == "impact" and feedback_id:
            # feedback_id = experience_id로 취급
            async with drv.session(database=_DB_NAME) as s:
                r = await s.run(
                    "MATCH (e:Experience {id: $exp_id})-[:INVOLVES]->(c:Concept) "
                    "RETURN c.id AS concept_id, c.name AS name, c.strength AS strength",
                    exp_id=feedback_id,
                )
                records = await r.fetch(50)
            impacts = [
                {"concept_id": rec["concept_id"], "name": rec["name"], "strength": round(float(rec["strength"] or 0.5), 3)}
                for rec in records
            ]
            return {"success": True, "impacts": impacts}

        else:
            return {"success": True, "stats": {}, "message": f"Unknown action: {action}"}

    except Exception as e:
        logger.error(f"get_feedback_data error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Vision (기존 유지) ────────────────────────────────────────────────────────

@app.post("/api/vision/process", response_model=VisionProcessResponse)
async def process_vision(request: VisionProcessRequest):
    """이미지 처리 엔드포인트 (substrate → Gemini Vision 직접 호출)"""
    try:
        from .llm_client import get_llm_client
        image_data = base64.b64decode(request.image_data)
        prompt = request.prompt or "이 이미지에서 무엇이 보이는지 설명해줘."

        # Gemini Vision API 직접 호출
        llm = get_llm_client()
        google_client = llm._get_google_client()

        if hasattr(google_client, 'models'):
            from google.genai import types as genai_types
            image_part = genai_types.Part.from_bytes(data=image_data, mime_type=request.mime_type)
            text_part = genai_types.Part.from_text(prompt)
            response = google_client.models.generate_content(
                model="gemini-2.0-flash",
                contents=[image_part, text_part],
            )
            description = response.text.strip()
        else:
            description = "Vision processing requires google-genai SDK"

        # Neo4j에 VisualExperience 저장 (간단 버전)
        db = get_brain_db()
        exp = await db.insert_experience(
            task=prompt,
            task_type="vision",
            output=description,
            success=bool(description),
            emotional_salience=0.6,
            dominant_emotion="curiosity",
            development_stage=(await db.get_baby_state() or {}).get("development_stage", 0),
            tags=["vision"],
        )

        return VisionProcessResponse(
            visual_experience={"description": description, "experience_id": exp.get("id")},
            emotional_changes={"curiosity": 0.1},
            success=bool(description),
            message="Image processed via Gemini Vision",
        )
    except Exception as e:
        logger.error(f"process_vision error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/vision/stats")
async def get_vision_stats():
    """시각 처리 통계 (Neo4j VisualExperience 기반)"""
    try:
        drv = get_driver()
        async with drv.session(database=_DB_NAME) as s:
            r = await s.run(
                "MATCH (e:Experience {task_type: 'vision'}) "
                "RETURN count(e) AS total"
            )
            rec = await r.single()
        return {"total_visual_experiences": rec["total"] if rec else 0}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── A4.3: Quest Passthrough Concepts ──────────────────────────────────────────
# Quest 3S 온디바이스 SmolVLM이 추출한 Concept을 Baby AI Neo4j에 직접 수신.
# 대안 B: Concept 노드 통합 (별도 라벨 X), source 메타로 분리 추적.
#   - insert_concept(category="visual") → occipital region 자동 매핑
#   - 후처리 Cypher: c.sources 배열에 source 추가, c.quest_observation_count++,
#                     c.last_quest_seen
# Experience: task_type="vision", tags=["quest_passthrough"], extras=메타
@app.post("/api/vision/quest-concepts", response_model=QuestConceptsResponse)
async def post_quest_concepts(request: QuestConceptsRequest):
    """Quest 3S 온디바이스 VLM이 추출한 concept을 Neo4j에 저장."""
    try:
        db = get_brain_db()
        drv = get_driver()

        # 1) Experience 노드 생성 — task_type="vision"으로 기존 통계 호환
        baby_state = await db.get_baby_state() or {}
        dev_stage = baby_state.get("development_stage", 0)
        extras_meta = {
            "source": request.source,
            "model": request.model,
            "inference_ms": request.inference_ms,
            "image_meta": request.image_meta.model_dump() if request.image_meta else None,
            "jpeg_path": request.jpeg_path,
            "device_timestamp": request.timestamp,
        }
        exp = await db.insert_experience(
            task=f"quest_passthrough_observation@{request.timestamp}",
            task_type="vision",
            output=request.vlm_response,
            success=bool(request.concepts_raw),
            emotional_salience=0.4,  # 수동적 관찰 — 대화보다 낮게
            dominant_emotion="curiosity",
            development_stage=dev_stage,
            tags=["quest_passthrough", "vision"],
            extras=extras_meta,
        )
        exp_id = exp.get("id")
        if not exp_id:
            raise HTTPException(status_code=500, detail="Experience 생성 실패")

        # 2) Concept 루프 — insert_concept (멱등 MERGE) + Quest 메타 후처리
        concepts_inserted = 0
        concepts_existing = 0
        name_to_id: dict[str, str] = {}
        for raw_name in request.concepts_raw:
            name = raw_name.strip().lower()
            if not name:
                continue

            # 2a) 신규 여부를 미리 확인 (MERGE 후에는 구분 불가)
            existed = await db.get_concept_by_name(name)
            was_new = existed is None

            # 2b) MERGE Concept (visual category → occipital hub)
            concept = await db.insert_concept(
                name=name,
                category="visual",
                description=None,
                acquired_at_stage=dev_stage,
            )
            cid = concept.get("id")
            if not cid:
                continue
            name_to_id[name] = cid

            # 2c) Quest 메타 후처리 — sources 배열, quest_observation_count, last_quest_seen
            async with drv.session(database=_DB_NAME) as s:
                await s.run(
                    "MATCH (c:Concept {id: $cid}) "
                    "SET c.sources = CASE "
                    "      WHEN c.sources IS NULL THEN [$src] "
                    "      WHEN $src IN c.sources THEN c.sources "
                    "      ELSE c.sources + $src END, "
                    "    c.quest_observation_count = coalesce(c.quest_observation_count, 0) + 1, "
                    "    c.last_quest_seen = $now",
                    cid=cid,
                    src=request.source,
                    now=request.timestamp,
                )

            # 2d) Experience -[:INVOLVES]-> Concept
            await db.link_experience_concept(
                experience_id=exp_id,
                concept_id=cid,
                confidence=0.5,
            )

            if was_new:
                concepts_inserted += 1
            else:
                concepts_existing += 1

        # 2e) Phase A4.4 — descriptor→object binding (color 우선).
        # 규칙: COLOR 토큰 뒤 바로 다음 단어가 수식 대상(인접 규칙).
        # 양쪽 concept이 이번 라운드에 저장된 경우만 관계 생성 (skip 전략).
        bindings_created = 0
        bindings_reinforced = 0
        bindings_skipped = 0
        for desc_name, obj_name, aspect in extract_color_bindings(request.vlm_response):
            desc_id = name_to_id.get(desc_name)
            obj_id = name_to_id.get(obj_name)
            if not desc_id or not obj_id:
                bindings_skipped += 1
                continue
            result = await db.link_descriptor_to_object(
                descriptor_concept_id=desc_id,
                object_concept_id=obj_id,
                aspect=aspect,
                source=request.source,
                observation_ts=request.timestamp,
            )
            if not result:
                bindings_skipped += 1
                continue
            if result.get("observation_count") == 1:
                bindings_created += 1
            else:
                bindings_reinforced += 1

        # 2g) Phase Q1 — visual co-occurrence Hebbian (같은 frame 객체 쌍 강화).
        # 근거: Quest 42 Experience 진단(2026-05-08)에서 636 same-exp pair 중
        #       577개(91%)가 RELATES_TO 미생성. 시각 시냅스 누락이 고립 원인의 일부.
        # 격리: source='visual_cooc' (conversation 'hebbian'과 분리).
        # Filter: 색상/위치/메타 토큰 제외 (concept_binding.VISUAL_COOC_EXCLUDE).
        # delta=0.03 (conv 직접 0.05 vs 간접 0.02 사이).
        cooc_updated = 0
        try:
            cooc_ids = select_visual_cooc_concepts(name_to_id)
            if len(cooc_ids) >= 2:
                from itertools import combinations
                cooc_pairs = list(combinations(cooc_ids, 2))
                cooc_updated = await db.hebbian_update(
                    cooc_pairs,
                    strength_delta=0.03,
                    source="visual_cooc",
                )
                logger.debug(
                    f"visual_cooc Hebbian: {len(cooc_pairs)} pairs from "
                    f"{len(cooc_ids)} concepts → {cooc_updated} updated"
                )
        except Exception as e:
            logger.warning(f"visual_cooc Hebbian error: {e}")

        # 3) DB 전체 unique concept 수 (관측 통계용)
        async with drv.session(database=_DB_NAME) as s:
            r = await s.run("MATCH (c:Concept) RETURN count(c) AS total")
            rec = await r.single()
        total_unique = rec["total"] if rec else 0

        return QuestConceptsResponse(
            experience_id=exp_id,
            concepts_inserted=concepts_inserted,
            concepts_existing=concepts_existing,
            total_unique_in_db=total_unique,
            bindings_created=bindings_created,
            bindings_reinforced=bindings_reinforced,
            bindings_skipped=bindings_skipped,
            success=True,
            message=(
                f"Quest observation saved: {concepts_inserted} new + "
                f"{concepts_existing} existing concepts; "
                f"bindings: {bindings_created} new + {bindings_reinforced} reinforced "
                f"+ {bindings_skipped} skipped"
            ),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"post_quest_concepts error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/process", response_model=ProcessResponse)
async def process_task(request: ProcessRequest):
    """일반 작업 처리 (conversation_handler 위임)"""
    try:
        from .conversation_handler import handle_conversation
        result = await handle_conversation(message=request.task, context=request.context)
        return ProcessResponse(
            output=result["output"],
            success=result["success"],
            emotional_state=result["emotional_state"],
            development_stage=result["development_stage"],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Experiences ───────────────────────────────────────────────────────────────

@app.get("/api/experiences")
async def get_experiences(limit: int = 20, task_type: Optional[str] = None):
    """
    최근 Experience 조회 (page.tsx ActivityLog + EmotionTimeline용)
    Neo4j Experience 노드: task, task_type, output, success,
      emotional_salience, dominant_emotion, development_stage, created_at
    """
    try:
        drv = get_driver()
        if task_type:
            cypher = (
                "MATCH (e:Experience) WHERE e.task_type = $task_type "
                "RETURN e ORDER BY e.created_at DESC LIMIT $limit"
            )
            params = {"task_type": task_type, "limit": limit}
        else:
            cypher = "MATCH (e:Experience) RETURN e ORDER BY e.created_at DESC LIMIT $limit"
            params = {"limit": limit}

        async with drv.session(database=_DB_NAME) as s:
            r = await s.run(cypher, **params)
            records = await r.fetch(limit)

        experiences = []
        for rec in records:
            node = dict(rec["e"])
            node.pop("embedding", None)  # 큰 배열 제거
            experiences.append(node)

        return {"experiences": experiences, "total": len(experiences)}
    except Exception as e:
        logger.error(f"get_experiences error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Emotion Logs ───────────────────────────────────────────────────────────────

@app.get("/api/emotion-logs")
async def get_emotion_logs(limit: int = 50):
    """
    최근 EmotionLog 조회 (page.tsx EmotionTimeline용)
    Neo4j EmotionLog 노드: curiosity, joy, fear, surprise, frustration,
      boredom, dominant_emotion, trigger_task, development_stage, created_at
    """
    try:
        drv = get_driver()
        async with drv.session(database=_DB_NAME) as s:
            r = await s.run(
                "MATCH (el:EmotionLog) "
                "RETURN el ORDER BY el.created_at DESC LIMIT $limit",
                limit=limit,
            )
            records = await r.fetch(limit)

        logs = [dict(rec["el"]) for rec in records]
        return {"emotion_logs": logs, "total": len(logs)}
    except Exception as e:
        logger.error(f"get_emotion_logs error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Sleep Logs (Memory Consolidation History) ─────────────────────────────────

@app.get("/api/sleep-logs")
async def get_sleep_logs(limit: int = 10):
    """
    수면 로그 조회 (MemoryConsolidationCard history 탭용)
    Neo4j SleepLog 노드: trigger_type, reinforced_count, decayed_count,
      patterns_promoted, duration_ms, success, created_at
    """
    try:
        drv = get_driver()
        async with drv.session(database=_DB_NAME) as s:
            r = await s.run(
                "MATCH (sl:SleepLog) "
                "RETURN sl ORDER BY sl.created_at DESC LIMIT $limit",
                limit=limit,
            )
            records = await r.fetch(limit)

        logs = []
        for rec in records:
            node = dict(rec["sl"])
            # MemoryConsolidationCard ConsolidationLog 타입에 맞게 매핑
            logs.append({
                "id": node.get("id", ""),
                "started_at": node.get("created_at", ""),
                "completed_at": node.get("completed_at") or node.get("created_at", ""),
                "trigger_type": node.get("trigger_type", "manual"),
                "experiences_processed": node.get("experiences_processed", 0),
                "memories_strengthened": node.get("reinforced_count", 0),
                "memories_decayed": node.get("decayed_count", 0),
                "patterns_promoted": node.get("patterns_promoted", 0),
                "concepts_consolidated": node.get("concepts_consolidated", 0),
                "success": node.get("success", True),
                "processing_time_ms": node.get("duration_ms"),
                "development_stage": node.get("development_stage"),
            })

        return {"logs": logs, "total": len(logs)}
    except Exception as e:
        logger.error(f"get_sleep_logs error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Procedural Memory ─────────────────────────────────────────────────────────

@app.get("/api/procedural-memory")
async def get_procedural_memory(limit: int = 10):
    """
    절차 기억 조회 (MemoryConsolidationCard procedural 탭용)
    Neo4j Procedure 노드: task_type, approach, success_count, failure_count,
      total_uses, last_used, created_at
    """
    try:
        drv = get_driver()
        async with drv.session(database=_DB_NAME) as s:
            r = await s.run(
                "MATCH (p:Procedure) "
                "WITH p, "
                "  CASE WHEN p.total_uses > 0 "
                "       THEN toFloat(p.success_count) / p.total_uses "
                "       ELSE 0.5 END AS success_rate "
                "RETURN p, success_rate "
                "ORDER BY success_rate DESC LIMIT $limit",
                limit=limit,
            )
            records = await r.fetch(limit)

        memories = []
        for rec in records:
            node = dict(rec["p"])
            success_rate = float(rec["success_rate"])
            memories.append({
                "id": node.get("id", ""),
                "pattern_name": f"{node.get('task_type', '')}:{node.get('approach', '')}",
                "pattern_type": node.get("task_type", "conversation"),
                "pattern_description": node.get("approach"),
                "strength": round(success_rate, 3),
                "repetition_count": node.get("total_uses", 0),
                "success_rate": round(success_rate, 3),
                "activation_count": node.get("total_uses", 0),
                "last_activated_at": node.get("last_used"),
                "created_at": node.get("created_at", ""),
            })

        return {"procedural_memories": memories, "total": len(memories)}
    except Exception as e:
        logger.error(f"get_procedural_memory error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Curiosity (CuriosityLog) ───────────────────────────────────────────────────

@app.get("/api/curiosity")
async def get_curiosity(limit: int = 20, status: Optional[str] = None):
    """
    호기심 로그 조회 (CuriosityCard용)
    Neo4j CuriosityLog 노드: query, query_type, source, priority, status,
      exploration_count, created_at, satisfaction_after
    """
    try:
        drv = get_driver()
        if status:
            cypher = (
                "MATCH (cl:CuriosityLog) WHERE cl.status = $status "
                "RETURN cl ORDER BY cl.priority DESC, cl.created_at DESC LIMIT $limit"
            )
            params = {"status": status, "limit": limit}
        else:
            cypher = (
                "MATCH (cl:CuriosityLog) "
                "RETURN cl ORDER BY cl.priority DESC, cl.created_at DESC LIMIT $limit"
            )
            params = {"limit": limit}

        async with drv.session(database=_DB_NAME) as s:
            r = await s.run(cypher, **params)
            records = await r.fetch(limit)

        queue = []
        for rec in records:
            node = dict(rec["cl"])
            queue.append({
                "id": node.get("id", ""),
                "query": node.get("query", node.get("topic", "")),
                "query_type": node.get("query_type", "exploration"),
                "source": node.get("source", "internal"),
                "priority": round(float(node.get("priority", 0.5)), 3),
                "status": node.get("status", "pending"),
                "exploration_count": node.get("exploration_count", 0),
                "created_at": str(node.get("created_at", "")),
                "satisfaction_after": node.get("satisfaction_after"),
            })

        # 상태별 통계
        all_stats: dict[str, int] = {}
        all_source: dict[str, int] = {}
        for item in queue:
            s_key = item["status"]
            src_key = item["source"]
            all_stats[s_key] = all_stats.get(s_key, 0) + 1
            all_source[src_key] = all_source.get(src_key, 0) + 1

        return {
            "queue": queue,
            "exploration_logs": [],  # 탐색 로그는 별도 엔드포인트
            "stats": {
                "total": len(queue),
                "byStatus": all_stats,
                "bySource": all_source,
            },
        }
    except Exception as e:
        logger.error(f"get_curiosity error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/curiosity")
async def post_curiosity(request: Request):
    """
    호기심 생성/탐색 처리 (useIdleSleep, CuriosityCard 액션용)

    action:
      generate      - 새 호기심 생성 (CuriosityLog 노드 생성)
      explore_batch - 대기 중인 호기심 탐색 (status 업데이트)
      explore       - 단일 호기심 탐색
    """
    try:
        body = await request.json()
        action = body.get("action", "generate")
        drv = get_driver()

        if action == "generate":
            # 현재 Baby 상태에서 호기심 주제 추출 → CuriosityLog 노드 생성
            db = get_brain_db()
            state = await db.get_baby_state()
            # 감정 기반 호기심 주제 생성 (간단한 규칙 기반)
            dominant_emotion = state.get("dominant_emotion", "curiosity")
            topics = []
            async with drv.session(database=_DB_NAME) as s:
                # 최근 경험에서 탐색되지 않은 개념 추출
                r = await s.run(
                    "MATCH (c:Concept) WHERE NOT (c)-[:EXPLORED]->() "
                    "RETURN c.name AS name, c.category AS category "
                    "ORDER BY c.strength DESC LIMIT $limit",
                    limit=body.get("limit", 5),
                )
                records = await r.fetch(body.get("limit", 5))
                for rec in records:
                    topic = rec["name"] or ""
                    if not topic:
                        continue
                    # CuriosityLog 노드 생성
                    await s.run(
                        "CREATE (cl:CuriosityLog {id: randomUUID(), query: $query, "
                        "query_type: 'concept_exploration', source: 'concept_gap', "
                        "priority: 0.6, status: 'pending', exploration_count: 0, "
                        "created_at: datetime()})",
                        query=topic,
                    )
                    topics.append(topic)

            return {"success": True, "action": "generate", "generated": [{"query": t} for t in topics]}

        elif action in ("explore_batch", "explore"):
            batch_size = body.get("batch_size", 3)
            async with drv.session(database=_DB_NAME) as s:
                # 대기 중인 호기심 가져와 상태 업데이트
                r = await s.run(
                    "MATCH (cl:CuriosityLog) WHERE cl.status = 'pending' "
                    "RETURN cl.id AS id, cl.query AS query "
                    "ORDER BY cl.priority DESC LIMIT $limit",
                    limit=batch_size,
                )
                records = await r.fetch(batch_size)
                explored = []
                for rec in records:
                    await s.run(
                        "MATCH (cl:CuriosityLog {id: $id}) "
                        "SET cl.status = 'learned', cl.exploration_count = cl.exploration_count + 1, "
                        "cl.satisfaction_after = 0.6",
                        id=rec["id"],
                    )
                    explored.append({"query": rec["query"], "success": True})

            return {"success": True, "action": action, "explored": explored}

        else:
            return {"success": False, "error": f"Unknown action: {action}"}

    except Exception as e:
        logger.error(f"post_curiosity error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── PendingQuestion ──────────────────────────────────────────────────────────

@app.get("/api/pending-questions")
async def get_pending_questions_endpoint(status: Optional[str] = None, limit: int = 20):
    """
    PendingQuestion 목록 조회
    - status: pending | answered | dismissed (미지정 시 전체)
    """
    try:
        db = get_brain_db()
        questions = await db.get_pending_questions(status=status, limit=limit)
        return {"questions": questions, "total": len(questions)}
    except Exception as e:
        logger.error(f"get_pending_questions error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/pending-questions")
async def create_pending_question(request: PendingQuestionCreate):
    """
    PendingQuestion 생성
    - curiosity_log_id 지정 시 (:CuriosityLog)-[:GENERATED]->(:PendingQuestion) 관계 생성
    """
    try:
        db = get_brain_db()
        question = await db.insert_pending_question(
            question=request.question,
            source=request.source,
            curiosity_log_id=request.curiosity_log_id,
        )
        if not question:
            raise HTTPException(
                status_code=404,
                detail="CuriosityLog not found" if request.curiosity_log_id else "Failed to create question",
            )
        # Redis Pub/Sub 발행 (SSE로 브라우저에 전달)
        await publish_pending_question(question)
        return {"success": True, "question": question}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"create_pending_question error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/api/pending-questions/{question_id}")
async def update_question_status_endpoint(question_id: str, request: Request):
    """
    PendingQuestion 상태 변경
    body: { "status": "dismissed" | "pending" }
    """
    try:
        body = await request.json()
        new_status = body.get("status")
        if not new_status:
            raise HTTPException(status_code=400, detail="status is required")
        if new_status not in ("pending", "answered", "dismissed"):
            raise HTTPException(status_code=400, detail="status must be pending, answered, or dismissed")

        db = get_brain_db()
        updated = await db.update_question_status(question_id, new_status)
        if not updated:
            raise HTTPException(status_code=404, detail=f"PendingQuestion {question_id} not found")
        return {"success": True, "question": updated}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"update_question_status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/pending-questions/{question_id}/answer")
async def answer_pending_question(question_id: str, request: PendingQuestionAnswer):
    """
    PendingQuestion 답변 제출
    - status를 'answered'로 변경, answered_at 기록
    """
    try:
        db = get_brain_db()
        answered = await db.submit_question_answer(
            question_id=question_id,
            answer=request.answer,
            answer_confidence=request.answer_confidence,
        )
        if not answered:
            raise HTTPException(status_code=404, detail=f"PendingQuestion {question_id} not found")
        # Redis Pub/Sub 발행
        await publish_pending_question(answered)
        return {"success": True, "question": answered}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"answer_pending_question error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── User Models (E2-3: Theory of Mind) ────────────────────────────────────────

@app.get("/api/users")
async def get_users():
    """UserModel 목록 조회"""
    try:
        drv = get_driver()
        async with drv.session(database=_DB_NAME) as s:
            result = await s.run(
                "MATCH (u:UserModel) "
                "RETURN u ORDER BY u.interaction_count DESC"
            )
            records = await result.fetch(100)
        users = [dict(r["u"]) for r in records]
        return {"users": users, "total": len(users)}
    except Exception as e:
        logger.error(f"get_users error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/users/{speaker_id}")
async def get_user(speaker_id: str):
    """특정 사용자 상세 + 관심사"""
    try:
        db = get_brain_db()
        ctx = await db.get_user_context(speaker_id)
        if not ctx:
            raise HTTPException(status_code=404, detail=f"UserModel not found: {speaker_id}")
        return ctx
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"get_user error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Temporal Patterns (E2-2) ───────────────────────────────────────────────────

@app.get("/api/temporal-patterns")
async def get_temporal_patterns():
    """TemporalPattern 목록 조회 (confidence 내림차순)"""
    try:
        drv = get_driver()
        async with drv.session(database=_DB_NAME) as s:
            result = await s.run(
                "MATCH (tp:TemporalPattern) "
                "OPTIONAL MATCH (tp)-[:PATTERN_INVOLVES]->(c:Concept) "
                "WITH tp, collect(c.name) AS concepts "
                "RETURN tp, concepts ORDER BY tp.confidence DESC"
            )
            records = await result.fetch(50)
        patterns = []
        for r in records:
            p = dict(r["tp"])
            p["involved_concepts"] = r["concepts"]
            patterns.append(p)
        return {"patterns": patterns, "total": len(patterns)}
    except Exception as e:
        logger.error(f"get_temporal_patterns error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Imagination ────────────────────────────────────────────────────────────────

@app.get("/api/imagination")
async def get_imagination(limit: int = 10):
    """
    상상 세션 조회 (WorldModelCard ImaginationVisualizer용)
    Neo4j Imagination 노드: topic, imagination_type, curiosity_level,
      thoughts, insights, started_at, ended_at
    """
    try:
        db = get_brain_db()
        sessions = await db.get_recent_imagination_sessions(limit=limit)
        # embedding 등 큰 필드 제거, JSON 파싱
        result = []
        for s in sessions:
            s.pop("embedding", None)
            result.append(s)
        return {"sessions": result, "total": len(result)}
    except Exception as e:
        logger.error(f"get_imagination error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/imagination")
async def post_imagination(request: Request):
    """
    상상/예측/시뮬레이션 처리 (useIdleSleep 수면 중 상상 단계)

    action:
      imagine   - 상상 세션 시작 (topic 기반)
      predict   - 예측 생성
      simulate  - 목표 시뮬레이션
      verify    - 예측 검증
      stats     - 통계 조회
    """
    try:
        body = await request.json()
        action = body.get("action", "imagine")
        db = get_brain_db()

        if action == "imagine":
            topic = body.get("topic", "자유 연상")
            trigger = body.get("trigger", "idle_sleep")
            state = await db.get_baby_state()
            curiosity_level = state.get("curiosity", 0.5)
            session = await db.start_imagination_session(
                topic=topic,
                imagination_type="free_association",
                curiosity_level=curiosity_level,
                trigger=trigger,
            )
            if session:
                await db.end_imagination_session(
                    session_id=session.get("id", ""),
                    insights=["내재적 탐색 완료"],
                    curiosity_satisfied=curiosity_level + 0.1,
                )
            return {
                "success": True,
                "action": "imagine",
                "session": session or {},
                "imagination_sessions": 1,
            }

        elif action == "predict":
            scenario = body.get("scenario", "")
            prediction_text = f"{scenario}에서 긍정적 결과 예측"
            pred = await db.insert_prediction(
                experience_id=None,
                prediction=prediction_text,
                confidence=0.6,
                prediction_type="scenario",
            )
            return {"success": True, "action": "predict", "prediction": pred or {}}

        elif action == "simulate":
            goal = body.get("goal", "자유 탐색")
            sim = await db.insert_simulation(
                goal=goal,
                simulation_type="planning",
            )
            if sim:
                await db.complete_simulation(
                    simulation_id=sim.get("id", ""),
                    outcome="completed",
                    reward_signal=0.6,
                )
            return {"success": True, "action": "simulate", "simulation": sim or {}}

        elif action == "verify":
            prediction_id = body.get("prediction_id")
            actual_outcome = body.get("actual_outcome", "")
            if prediction_id:
                await db.verify_prediction(
                    prediction_id=prediction_id,
                    actual_outcome=actual_outcome,
                    was_correct=True,
                )
            return {"success": True, "action": "verify"}

        elif action == "stats":
            preds = await db.get_recent_predictions(limit=20)
            correct = sum(1 for p in preds if p.get("was_correct"))
            return {
                "success": True,
                "action": "stats",
                "total_predictions": len(preds),
                "correct_predictions": correct,
                "accuracy": correct / len(preds) if preds else 0,
            }

        else:
            return {"success": False, "error": f"Unknown action: {action}"}

    except Exception as e:
        logger.error(f"post_imagination error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Autonomy Metrics ───────────────────────────────────────────────────────────

@app.get("/api/autonomy-metrics")
async def get_autonomy_metrics():
    """
    자율성 지표 조회 (AutonomousGoalsCard metrics 탭용)
    Neo4j AutonomousGoal 노드 집계: goal_type별 평균 score
    """
    try:
        drv = get_driver()
        async with drv.session(database=_DB_NAME) as s:
            r = await s.run(
                "MATCH (g:AutonomousGoal) "
                "RETURN "
                "  avg(coalesce(g.epistemic_score, 0.5)) AS epistemic_curiosity, "
                "  avg(coalesce(g.diversive_score, 0.5)) AS diversive_curiosity, "
                "  avg(coalesce(g.empowerment_score, 0.5)) AS empowerment_drive, "
                "  avg(coalesce(g.combined_motivation, 0.5)) AS overall_autonomy, "
                "  count(CASE WHEN g.status = 'active' OR g.status IS NULL THEN 1 END) AS active_goals_count, "
                "  count(CASE WHEN g.status = 'completed' THEN 1 END) AS completed_goals_count"
            )
            rec = await r.single()

        if not rec:
            return {"metrics": None}

        return {
            "metrics": {
                "epistemic_curiosity": round(float(rec["epistemic_curiosity"] or 0.5), 3),
                "diversive_curiosity": round(float(rec["diversive_curiosity"] or 0.5), 3),
                "empowerment_drive": round(float(rec["empowerment_drive"] or 0.5), 3),
                "overall_autonomy": round(float(rec["overall_autonomy"] or 0.5), 3),
                "active_goals_count": rec["active_goals_count"] or 0,
                "completed_goals_count": rec["completed_goals_count"] or 0,
            }
        }
    except Exception as e:
        logger.error(f"get_autonomy_metrics error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Goal Progress (AutonomousGoalsCard history 탭) ────────────────────────────

@app.get("/api/goal-progress")
async def get_goal_progress(limit: int = 20):
    """
    목표 진행 기록 조회 (AutonomousGoalsCard history 탭용)
    Neo4j GoalProgress 노드가 없으면 AutonomousGoal 완료 기록으로 대체
    """
    try:
        drv = get_driver()
        async with drv.session(database=_DB_NAME) as s:
            r = await s.run(
                "MATCH (g:AutonomousGoal) "
                "WHERE g.status = 'completed' "
                "RETURN g.id AS id, g.id AS goal_id, "
                "  1 AS attempt_number, "
                "  'success' AS outcome, "
                "  coalesce(g.combined_motivation, 0.5) AS learning_gain, "
                "  g.trigger_reason AS insight, "
                "  coalesce(g.completed_at, g.created_at) AS created_at "
                "ORDER BY created_at DESC LIMIT $limit",
                limit=limit,
            )
            records = await r.fetch(limit)

        progress = [dict(rec) for rec in records]
        return {"progress": progress, "total": len(progress)}
    except Exception as e:
        logger.error(f"get_goal_progress error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Visual Experiences ─────────────────────────────────────────────────────────

@app.get("/api/visual-experiences")
async def get_visual_experiences(limit: int = 5):
    """
    시각 경험 조회 (sense/page.tsx recentVisuals용)
    Neo4j VisualExperience 노드 (vision.py에서 생성)
    """
    try:
        drv = get_driver()
        async with drv.session(database=_DB_NAME) as s:
            r = await s.run(
                "MATCH (ve:VisualExperience) "
                "RETURN ve ORDER BY ve.created_at DESC LIMIT $limit",
                limit=limit,
            )
            records = await r.fetch(limit)

        visuals = []
        for rec in records:
            node = dict(rec["ve"])
            node.pop("embedding", None)
            visuals.append(node)

        return {"visual_experiences": visuals, "total": len(visuals)}
    except Exception as e:
        logger.error(f"get_visual_experiences error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Memory Consolidation Stats (확장) ─────────────────────────────────────────
# 기존 GET /api/memory/consolidate 를 오버라이드하지 않고
# sleep-logs, procedural-memory 로 분리했으므로 기존 엔드포인트 유지.
# MemoryConsolidationCard fetchData가 호출하는 GET /api/memory/consolidate 응답에
# sleep_log_count 추가 (MemoryConsolidationCard stats 필드 보완)


# ── Simulations ────────────────────────────────────────────────────────────────

@app.get("/api/simulations")
async def get_simulations(limit: int = 20):
    """
    시뮬레이션 목록 조회 (useWorldModel hook용)
    Neo4j Imagination 노드 중 imagination_type이 simulation/planning인 것 반환
    """
    try:
        db = get_brain_db()
        sims = await db.get_recent_simulations(limit=limit)
        return {"simulations": sims or [], "total": len(sims or [])}
    except Exception as e:
        logger.error(f"get_simulations error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/causal-models")
async def get_causal_models(limit: int = 100):
    """
    인과관계 모델 조회 (useWorldModel hook causalModels + causalGraph용)
    Neo4j CAUSES 관계 반환
    """
    try:
        db = get_brain_db()
        models = await db.get_causal_models(limit=limit)
        return {"causal_models": models or [], "total": len(models or [])}
    except Exception as e:
        logger.error(f"get_causal_models error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Predictions ────────────────────────────────────────────────────────────────

@app.get("/api/predictions")
async def get_predictions(limit: int = 50):
    """
    예측 목록 조회 (usePredictions hook용)
    Neo4j Prediction 노드 반환
    """
    try:
        db = get_brain_db()
        preds = await db.get_recent_predictions(limit=limit)
        return {"predictions": preds or [], "total": len(preds or [])}
    except Exception as e:
        logger.error(f"get_predictions error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/api/predictions/{prediction_id}/verify")
async def verify_prediction_endpoint(prediction_id: str, request: Request):
    """
    예측 검증 (usePredictions.verifyPrediction용)
    was_correct, actual_outcome, insight_gained 업데이트
    """
    try:
        body = await request.json()
        was_correct: bool = body.get("was_correct", False)
        actual_outcome: str = body.get("actual_outcome", "")
        db = get_brain_db()
        await db.verify_prediction(
            prediction_id=prediction_id,
            actual_outcome=actual_outcome,
            was_correct=was_correct,
        )
        return {"success": True, "prediction_id": prediction_id, "was_correct": was_correct}
    except Exception as e:
        logger.error(f"verify_prediction_endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Audio Transcription (STT) ──────────────────────────────────────────────────

@app.post("/api/audio/transcribe")
async def audio_transcribe(request: Request):
    """
    음성 → 텍스트 변환 (STT)
    Gemini 멀티모달 Audio API 사용
    입력: { audio_data: str (base64), mime_type: str, duration_ms: int }
    출력: { text: str, confidence: float, language: str }
    """
    try:
        body = await request.json()
        audio_data_b64: str = body.get("audio_data", "")
        mime_type: str = body.get("mime_type", "audio/webm")
        duration_ms: int = body.get("duration_ms", 0)

        if not audio_data_b64:
            raise HTTPException(status_code=400, detail="audio_data is required")

        audio_bytes = base64.b64decode(audio_data_b64)

        from .llm_client import get_llm_client
        llm = get_llm_client()
        google_client = llm._get_google_client()

        prompt = (
            "이 오디오를 한국어로 정확하게 텍스트로 변환해주세요. "
            "변환된 텍스트만 출력하고 다른 설명은 하지 마세요."
        )

        try:
            # 새로운 SDK (google.genai)
            if hasattr(google_client, 'models'):
                from google.genai import types as genai_types
                audio_part = genai_types.Part.from_bytes(
                    data=audio_bytes,
                    mime_type=mime_type,
                )
                text_part = genai_types.Part.from_text(prompt)
                response = google_client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=[audio_part, text_part],
                )
                transcribed = response.text.strip()
            else:
                # 구버전 SDK (google.generativeai)
                import google.generativeai as genai
                model = google_client.GenerativeModel("gemini-2.0-flash")
                audio_part = {
                    "mime_type": mime_type,
                    "data": audio_data_b64,
                }
                response = model.generate_content([audio_part, prompt])
                transcribed = response.text.strip()
        except Exception as gemini_err:
            logger.warning(f"Gemini STT error: {gemini_err}, returning empty transcription")
            transcribed = ""

        return {
            "text": transcribed,
            "confidence": 0.9 if transcribed else 0.0,
            "language": "ko-KR",
            "duration_ms": duration_ms,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"audio_transcribe error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Speech Synthesis (TTS) ─────────────────────────────────────────────────────

@app.post("/api/speech/synthesize")
async def speech_synthesize(request: Request):
    """
    텍스트 → 음성 변환 (TTS)
    Gemini TTS API 사용 (gemini-2.5-flash-preview-tts)
    입력: { text: str, voice: str, speaking_rate: float, pitch: float }
    출력: { audio_content: str (base64 WAV), duration: float, format: str }
    """
    try:
        body = await request.json()
        text: str = body.get("text", "")
        voice: str = body.get("voice", "Kore")  # Gemini TTS voice (Korean)
        speaking_rate: float = body.get("speaking_rate", 1.0)
        pitch: float = body.get("pitch", 0.0)

        if not text:
            raise HTTPException(status_code=400, detail="text is required")

        from .llm_client import get_llm_client
        llm = get_llm_client()
        google_client = llm._get_google_client()

        audio_b64 = ""
        try:
            # 새로운 SDK (google.genai) — Gemini TTS
            if hasattr(google_client, 'models'):
                from google.genai import types as genai_types
                response = google_client.models.generate_content(
                    model="gemini-2.5-flash-preview-tts",
                    contents=text,
                    config=genai_types.GenerateContentConfig(
                        response_modalities=["AUDIO"],
                        speech_config=genai_types.SpeechConfig(
                            voice_config=genai_types.VoiceConfig(
                                prebuilt_voice_config=genai_types.PrebuiltVoiceConfig(
                                    voice_name=voice,
                                )
                            )
                        ),
                    ),
                )
                # 오디오 데이터 추출
                audio_data = response.candidates[0].content.parts[0].inline_data.data
                audio_b64 = base64.b64encode(audio_data).decode("utf-8")
            else:
                # 구버전 SDK는 TTS 미지원 — 빈 응답
                logger.warning("Gemini TTS requires new SDK (google-genai). Returning empty audio.")
                audio_b64 = ""
        except Exception as tts_err:
            logger.warning(f"Gemini TTS error: {tts_err}, returning empty audio")
            audio_b64 = ""

        return {
            "audio_content": audio_b64,
            "audio_url": None,
            "duration": len(text) * 0.08 if audio_b64 else 0,  # 대략적 추정
            "format": "audio/wav",
            "voice": voice,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"speech_synthesize error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Server Entry Point ────────────────────────────────────────────────────────

def run_server(host: str = "0.0.0.0", port: int = 8000):
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    run_server(args.host, args.port)
