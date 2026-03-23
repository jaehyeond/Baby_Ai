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
from .redis_client import (
    init_redis, close_redis, get_redis,
    CHANNEL_BABY_STATE, CHANNEL_NEURON_ACTIVATION,
    CHANNEL_PENDING_QUESTION, CHANNEL_IMAGINATION,
    CHANNEL_EXPERIENCE,
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


class VisionProcessRequest(BaseModel):
    image_data: str
    mime_type: str = "image/jpeg"
    prompt: Optional[str] = None


class VisionProcessResponse(BaseModel):
    visual_experience: dict
    emotional_changes: dict
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
    """Concept 간 RELATES_TO 관계 목록 (brain 시각화용)"""
    try:
        async with get_driver().session(database=_DB_NAME) as s:
            result = await s.run(
                "MATCH (src:Concept)-[r:RELATES_TO]->(tgt:Concept) "
                "RETURN src.id AS from_concept_id, tgt.id AS to_concept_id, "
                "  coalesce(r.strength, 0.5) AS strength, "
                "  coalesce(r.relation_type, 'related') AS relation_type "
                "ORDER BY r.strength DESC LIMIT $limit",
                limit=limit,
            )
            records = await result.fetch(limit)
            relations = [
                {
                    "from_concept_id": rec["from_concept_id"],
                    "to_concept_id": rec["to_concept_id"],
                    "strength": round(float(rec["strength"]), 3),
                    "relation_type": rec["relation_type"],
                }
                for rec in records
            ]
        return {"relations": relations, "total": len(relations)}
    except Exception as e:
        logger.error(f"get_concept_relations error: {e}")
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

        return {"status": "ok", "mode": request.mode, **results}
    except Exception as e:
        logger.error(f"consolidate error: {e}")
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
    """이미지 처리 엔드포인트 (기존 유지)"""
    try:
        from .substrate import get_substrate
        image_data = base64.b64decode(request.image_data)
        substrate = get_substrate()
        result = await substrate.process_image(image_data, request.prompt)

        if result.visual_experience:
            return VisionProcessResponse(
                visual_experience=result.visual_experience.to_dict(),
                emotional_changes=result.visual_experience.emotional_response,
                success=result.success,
                message="Image processed successfully",
            )
        return VisionProcessResponse(
            visual_experience={},
            emotional_changes={},
            success=False,
            message=result.output or "Failed to process image",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/vision/stats")
async def get_vision_stats():
    """시각 처리 통계 (기존 유지)"""
    try:
        from .vision import get_vision_processor
        return get_vision_processor().get_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/process", response_model=ProcessResponse)
async def process_task(request: ProcessRequest):
    """일반 작업 처리 (기존 유지)"""
    try:
        from .substrate import get_substrate
        substrate = get_substrate()
        result = await substrate.process(request.task, request.context)
        return ProcessResponse(
            output=result.output,
            success=result.success,
            emotional_state=result.emotional_state,
            development_stage=result.development_stage,
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
