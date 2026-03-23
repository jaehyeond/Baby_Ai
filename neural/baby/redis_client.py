"""
Redis Client for Baby Brain
Phase 2: Pub/Sub + 캐시 래퍼

채널 목록 (baby-ai:* prefix):
  baby-ai:baby_state         - 감정/발달 상태 변화
  baby-ai:neuron_activation  - 뉴런 활성화 이벤트
  baby-ai:pending_question   - 새 질문 생성
  baby-ai:imagination        - 상상 세션 이벤트
  baby-ai:experience         - 새 경험 저장됨

연결: Upstash Redis (TLS, rediss://)
드라이버: redis.asyncio (hiredis 백엔드)
"""

import os
import json
import logging
from typing import Any, Optional

import redis.asyncio as aioredis
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

_REDIS_URL = os.getenv("REDIS_URL")  # rediss://default:...@clean-polecat-38197.upstash.io:6379

# 채널 상수
CHANNEL_BABY_STATE       = "baby-ai:baby_state"
CHANNEL_NEURON_ACTIVATION = "baby-ai:neuron_activation"
CHANNEL_PENDING_QUESTION  = "baby-ai:pending_question"
CHANNEL_IMAGINATION       = "baby-ai:imagination"
CHANNEL_EXPERIENCE        = "baby-ai:experience"

# 싱글톤
_redis_client: Optional[aioredis.Redis] = None


def init_redis() -> aioredis.Redis:
    """Redis 클라이언트 초기화 (앱 lifespan에서 1회 호출)"""
    global _redis_client
    if _REDIS_URL is None:
        raise RuntimeError("REDIS_URL not set in environment")
    _redis_client = aioredis.from_url(
        _REDIS_URL,
        ssl_cert_reqs=None,       # Upstash self-signed cert 허용
        decode_responses=True,    # bytes → str 자동 변환
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
