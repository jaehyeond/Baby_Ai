"""
Phase 0: Upstash Redis 연결 테스트

[Upstash Redis 연결 패턴 - 2026-03-19]

인스턴스: baby-ai-redis
플랫폼: GCP Tokyo (asia-northeast1)
URL 형식: rediss:// (TLS 필수 - redis:// 사용 불가)
Username: default
포트: 6379

주의사항:
  - Pub/Sub은 TCP 연결 필수 (HTTP REST SDK 불가)
  - redis-py asyncio 사용 (FastAPI와 통합)
  - ssl_cert_reqs=None: Upstash self-signed cert 허용
"""
import os
import asyncio
from dotenv import load_dotenv
import redis.asyncio as aioredis

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL")
print(f"Redis URL: {REDIS_URL[:40]}...{REDIS_URL[-20:]}")
print()


async def test_basic():
    """기본 SET/GET/DEL 테스트"""
    print("[Test 1] Basic SET/GET/DEL")
    client = aioredis.from_url(
        REDIS_URL,
        ssl_cert_reqs=None,  # Upstash self-signed cert
        decode_responses=True,
    )
    try:
        await client.set("phase0_test", "hello-baby-ai", ex=60)
        val = await client.get("phase0_test")
        assert val == "hello-baby-ai", f"Expected 'hello-baby-ai', got {val!r}"
        await client.delete("phase0_test")
        print(f"  [OK] SET/GET/DEL: {val!r}")
    finally:
        await client.aclose()


async def test_pubsub():
    """Pub/Sub 테스트 (FastAPI SSE 패턴)"""
    print("[Test 2] Pub/Sub (publisher -> subscriber)")

    pub_client = aioredis.from_url(
        REDIS_URL,
        ssl_cert_reqs=None,
        decode_responses=True,
    )
    sub_client = aioredis.from_url(
        REDIS_URL,
        ssl_cert_reqs=None,
        decode_responses=True,
    )

    received = []

    async def subscriber():
        async with sub_client.pubsub() as ps:
            await ps.subscribe("baby-ai:test-channel")
            # 최대 3초 대기, 1개 메시지 수신 후 종료
            async for msg in ps.listen():
                if msg["type"] == "message":
                    received.append(msg["data"])
                    break

    try:
        # subscriber를 백그라운드로 시작
        sub_task = asyncio.create_task(subscriber())
        await asyncio.sleep(0.5)  # subscribe 완료 대기

        # publisher에서 메시지 전송
        listeners = await pub_client.publish("baby-ai:test-channel", "phase0-pubsub-ok")
        print(f"  [OK] Published to {listeners} listener(s)")

        # subscriber 결과 대기 (최대 3초)
        await asyncio.wait_for(sub_task, timeout=3.0)
        assert received == ["phase0-pubsub-ok"], f"Got: {received}"
        print(f"  [OK] Received: {received[0]!r}")

    finally:
        await pub_client.aclose()
        await sub_client.aclose()


async def test_info():
    """Redis 서버 정보"""
    print("[Test 3] Server INFO")
    client = aioredis.from_url(
        REDIS_URL,
        ssl_cert_reqs=None,
        decode_responses=True,
    )
    try:
        info = await client.info("server")
        print(f"  [OK] Redis version: {info.get('redis_version', 'N/A')}")
        print(f"  [OK] OS: {info.get('os', 'N/A')}")
        print(f"  [OK] Mode: {info.get('redis_mode', 'N/A')}")
    finally:
        await client.aclose()


async def main():
    try:
        await test_basic()
        await test_pubsub()
        await test_info()

        print()
        print("[PHASE 0 REDIS COMPLETE] Upstash Redis connection verified")
        print(f"  Endpoint: clean-polecat-38197.upstash.io:6379")
        print("  TLS: enabled (rediss://)")
        print("  Pub/Sub: working")
        print("  Ready for Phase 1: Redis channel design")

    except Exception as e:
        print(f"[FAIL] {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
