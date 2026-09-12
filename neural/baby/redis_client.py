"""
Redis Client for Baby Brain
Phase 2: Pub/Sub + 캐시 래퍼

채널 목록 (baby-ai:* prefix):
  baby-ai:baby_state         - 감정/발달 상태 변화
  baby-ai:neuron_activation  - 뉴런 활성화 이벤트
  baby-ai:pending_question   - 새 질문 생성
  baby-ai:imagination        - 상상 세션 이벤트
  baby-ai:experience         - 새 경험 저장됨

  # Phase M1 (2026-05-11) — 관찰/학습 라이프사이클 이벤트
  baby-ai:vlm                - Quest passthrough VLM 추론 시작/종료
  baby-ai:gemini             - Gemini Vision 추론 시작/종료
  baby-ai:sleep              - 수면 모드 진입/종료, replay 진행
  baby-ai:binding            - 새 descriptor↔object binding 생성
  baby-ai:concept            - 신규 Concept 학습
  baby-ai:stage              - development_stage 전이
  baby-ai:adgr               - ADGR pruning/proposal/spawned (M3 예약, helper는 M3에서 추가)

연결: local Redis (redis://) 또는 인증서 검증 TLS Redis (rediss://)
드라이버: redis.asyncio (hiredis 백엔드)
"""

import os
import json
import logging
from typing import Any, Optional
from urllib.parse import parse_qsl, urlsplit

import redis.asyncio as aioredis
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# 채널 상수
CHANNEL_BABY_STATE       = "baby-ai:baby_state"
CHANNEL_NEURON_ACTIVATION = "baby-ai:neuron_activation"
CHANNEL_PENDING_QUESTION  = "baby-ai:pending_question"
CHANNEL_IMAGINATION       = "baby-ai:imagination"
CHANNEL_EXPERIENCE        = "baby-ai:experience"

# Phase M1 (2026-05-11) — 관찰/학습 라이프사이클 채널
CHANNEL_VLM     = "baby-ai:vlm"
CHANNEL_GEMINI  = "baby-ai:gemini"
CHANNEL_SLEEP   = "baby-ai:sleep"
CHANNEL_BINDING = "baby-ai:binding"
CHANNEL_CONCEPT = "baby-ai:concept"
CHANNEL_STAGE   = "baby-ai:stage"
CHANNEL_ADGR    = "baby-ai:adgr"  # M3 예약 (helper 미구현)

# 싱글톤
_redis_client: Optional[aioredis.Redis] = None


def redis_connection_options(redis_url: str) -> dict[str, Any]:
    """Build scheme-appropriate options without weakening TLS validation."""
    parsed = urlsplit(redis_url)
    scheme = parsed.scheme.lower()
    query: dict[str, list[str]] = {}
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        query.setdefault(key.lower(), []).append(value.strip().lower())

    tls_query_keys = sorted(key for key in query if key.startswith("ssl"))
    if scheme == "redis" and tls_query_keys:
        raise ValueError("redis:// must not include TLS query options")

    options: dict[str, Any] = {"decode_responses": True}
    if scheme == "rediss":
        cert_reqs = query.get("ssl_cert_reqs", [])
        if any(value != "required" for value in cert_reqs):
            raise ValueError("rediss:// must require certificate validation")
        hostname_checks = query.get("ssl_check_hostname", [])
        if any(value not in {"1", "true", "yes", "on"} for value in hostname_checks):
            raise ValueError("rediss:// must require hostname validation")
        options.update({
            "ssl_cert_reqs": "required",
            "ssl_check_hostname": True,
        })
    elif scheme != "redis":
        raise ValueError("REDIS_URL must use redis:// or rediss://")
    return options


def init_redis(redis_url: Optional[str] = None) -> aioredis.Redis:
    """Redis 클라이언트 초기화 (연결 확인은 readiness ping에서 수행)."""
    global _redis_client
    resolved_url = redis_url or os.getenv("REDIS_URL")
    if resolved_url is None:
        raise RuntimeError("REDIS_URL not set in environment")
    _redis_client = aioredis.from_url(
        resolved_url,
        **redis_connection_options(resolved_url),
    )
    logger.info("Redis client initialized")
    return _redis_client


async def close_redis() -> None:
    """Redis 연결 종료 (앱 lifespan 종료 시)"""
    global _redis_client
    if _redis_client:
        await _redis_client.aclose()
        _redis_client = None


def get_redis() -> aioredis.Redis:
    """현재 Redis 클라이언트 반환"""
    if _redis_client is None:
        raise RuntimeError("Redis client not initialized. Call init_redis() first.")
    return _redis_client


# ── Pub/Sub 헬퍼 ────────────────────────────────────────────────────────────

async def publish(channel: str, data: Any) -> int:
    """채널에 메시지 발행. data는 dict/list → JSON 직렬화, str은 그대로."""
    client = get_redis()
    if isinstance(data, (dict, list)):
        payload = json.dumps(data, ensure_ascii=False)
    else:
        payload = str(data)
    count = await client.publish(channel, payload)
    logger.debug(f"Published to {channel}: {count} subscribers")
    return count


async def publish_baby_state(state: dict) -> None:
    """baby_state 변화 발행"""
    await publish(CHANNEL_BABY_STATE, {
        "type": "baby_state",
        "data": state,
    })


async def publish_neuron_activation(activations: list[dict]) -> None:
    """뉴런 활성화 이벤트 발행"""
    await publish(CHANNEL_NEURON_ACTIVATION, {
        "type": "neuron_activation",
        "data": activations,
    })


async def publish_pending_question(question: dict) -> None:
    """새 Pending Question 발행"""
    await publish(CHANNEL_PENDING_QUESTION, {
        "type": "pending_question",
        "data": question,
    })


async def publish_imagination(session: dict) -> None:
    """상상 세션 이벤트 발행"""
    await publish(CHANNEL_IMAGINATION, {
        "type": "imagination",
        "data": session,
    })


async def publish_experience(experience: dict) -> None:
    """새 경험 저장 이벤트 발행"""
    await publish(CHANNEL_EXPERIENCE, {
        "type": "experience",
        "data": {
            "id": experience.get("id"),
            "task_type": experience.get("task_type"),
            "dominant_emotion": experience.get("dominant_emotion"),
            "development_stage": experience.get("development_stage"),
        },
    })


# ── Phase M1 (2026-05-11): 관찰/학습 라이프사이클 publish helper ──────────────
# 모두 fire-and-forget 패턴. 발행 실패가 본 처리 로직을 깨지 않도록
# 호출부에서 try/except로 감싸는 것이 호출 규칙 (api_server.py 기존 패턴 일치).

async def publish_vlm_start(meta: dict) -> None:
    """Quest passthrough VLM 추론 시작 (post_quest_concepts 진입)"""
    await publish(CHANNEL_VLM, {"type": "vlm.processing.start", "data": meta})


async def publish_vlm_end(meta: dict) -> None:
    """Quest passthrough VLM 추론 종료 (post_quest_concepts return 직전)"""
    await publish(CHANNEL_VLM, {"type": "vlm.processing.end", "data": meta})


async def publish_gemini_start(meta: dict) -> None:
    """Gemini Vision 추론 시작 (process_vision LLM 호출 직전)"""
    await publish(CHANNEL_GEMINI, {"type": "gemini.processing.start", "data": meta})


async def publish_gemini_end(meta: dict) -> None:
    """Gemini Vision 추론 종료 (process_vision return 직전)"""
    await publish(CHANNEL_GEMINI, {"type": "gemini.processing.end", "data": meta})


async def publish_sleep_start(meta: dict) -> None:
    """수면 모드 진입 (memory_replay 진입 또는 M3 sleep_orchestrator 진입)"""
    await publish(CHANNEL_SLEEP, {"type": "sleep.start", "data": meta})


async def publish_sleep_end(meta: dict) -> None:
    """수면 모드 종료 (memory_replay sleep_log 생성 직후 또는 M3 종료)"""
    await publish(CHANNEL_SLEEP, {"type": "sleep.end", "data": meta})


async def publish_binding_created(binding: dict) -> None:
    """새 descriptor↔object binding 생성 (observation_count == 1 분기)"""
    await publish(CHANNEL_BINDING, {"type": "binding.created", "data": binding})


async def publish_concept_learned(concept: dict) -> None:
    """신규 Concept 학습 (insert_concept에서 was_new=True 분기)"""
    await publish(CHANNEL_CONCEPT, {"type": "concept.learned", "data": concept})


async def publish_stage_transition(payload: dict) -> None:
    """development_stage 전이 (api_server.py /api/conversation endpoint 레벨)

    payload: {prev_stage, next_stage, experience_count, trigger?}
    conversation_handler v30 미수정 제약 때문에 endpoint에서 before/after 비교로 검출.
    """
    await publish(CHANNEL_STAGE, {"type": "stage.transition", "data": payload})


# ── 캐시 헬퍼 ───────────────────────────────────────────────────────────────

async def cache_set(key: str, value: Any, ttl_seconds: int = 60) -> None:
    """값을 Redis에 캐시 (JSON 직렬화)"""
    client = get_redis()
    payload = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
    await client.setex(key, ttl_seconds, payload)


async def cache_get(key: str) -> Optional[Any]:
    """캐시에서 값 조회 (JSON 역직렬화)"""
    client = get_redis()
    raw = await client.get(key)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return raw
