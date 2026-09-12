"""Probe the isolated installed API and Redis, including outage and SSE recovery.

Never invokes a model or a implemented learning action. Test Redis keys expire.
"""
from __future__ import annotations
import argparse
import asyncio
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import time
import uuid

import httpx
import redis.asyncio as redis

ROOT = Path(__file__).resolve().parents[2]


async def sse_delivery(client, redis_client, sequence):
    marker = str(uuid.uuid4())
    async with client.stream("GET", "/api/events") as response:
        assert response.status_code == 200
        lines = response.aiter_lines()
        # The server's initial comment is sent after subscription is established.
        initial = await asyncio.wait_for(anext(lines), 5)
        assert initial.startswith(":"), "Initial SSE readiness comment missing"
        delivered = await redis_client.publish("baby-ai:experience", json.dumps({"type": "runtime_probe", "probe_id": marker, "sequence": sequence}))
        assert delivered >= 1
        async def receive():
            async for line in lines:
                if line.startswith("data: "):
                    payload = json.loads(line[6:])
                    if payload.get("probe_id") == marker:
                        return payload["sequence"]
            raise AssertionError("SSE closed before delivery")
        return await asyncio.wait_for(receive(), 5) == sequence


async def run(args):
    from dotenv import dotenv_values
    config = dotenv_values(args.env_file)
    if config.get("NEO4J_URI") != "bolt://127.0.0.1:17687" or config.get("REDIS_URL") != "redis://127.0.0.1:16379/0":
        raise ValueError("This probe only operates the isolated restore endpoints")
    result = {"captured_at_utc": datetime.now(timezone.utc).isoformat(),
              "model_api_calls": 0, "neo4j_write_calls": 0, "sensor_capture": False}
    async with httpx.AsyncClient(base_url="http://127.0.0.1:18000", timeout=10) as client:
        health = await client.get("/health")
        assert health.status_code == 200 and health.json()["ready"] is True, health.text
        result["healthy"] = health.json()
        assert (await client.get("/health/live")).status_code == 200
        for endpoint, action in (("/api/curiosity", "explore"), ("/api/curiosity", "explore_batch"),
                                 ("/api/imagination", "predict"), ("/api/imagination", "simulate"), ("/api/imagination", "verify")):
            response = await client.post(endpoint, json={"action": action})
            assert response.status_code == 200, (endpoint, action, response.status_code)
            data = response.json()
            assert data["status"] == "awaiting_evidence" and data["persisted"] is False
            assert data["execution"]["executed"] is False and data["evaluation"]["verified"] is False
        result["unsupported_actions_truthful"] = 5
        redis_client = redis.from_url(config["REDIS_URL"], decode_responses=True)
        sentinel = "bibi:runtime-probe:" + str(uuid.uuid4())
        try:
            await redis_client.set(sentinel, "persisted", ex=300)
            result["sse_first_delivery"] = await sse_delivery(client, redis_client, 1)
            if args.redis_lifecycle:
                wsl_root = "/mnt/" + ROOT.drive[0].lower() + ROOT.as_posix()[2:]
                script = wsl_root + "/scripts/deployment/redis_local.sh"
                runtime = wsl_root + "/.runtime"
                def lifecycle(action):
                    subprocess.run(["wsl.exe", "-d", "Ubuntu-22.04", "--exec", "sh", script, action, runtime], check=True, stdout=subprocess.DEVNULL, timeout=30)
                await asyncio.to_thread(lifecycle, "stop")
                try:
                    unhealthy = await client.get("/health")
                    assert unhealthy.status_code == 503 and not unhealthy.json()["checks"]["redis"]["healthy"]
                    assert (await client.get("/health/live")).status_code == 200
                    result["redis_outage_readiness_503_liveness_200"] = True
                finally:
                    await asyncio.to_thread(lifecycle, "start")
                deadline = time.monotonic() + 15
                while True:
                    restored = await client.get("/health")
                    if restored.status_code == 200:
                        break
                    assert time.monotonic() < deadline, "Readiness did not recover"
                    await asyncio.sleep(0.25)
                result["redis_restart_same_api_recovered"] = True
                result["redis_persistence"] = await redis_client.get(sentinel) == "persisted"
                assert result["redis_persistence"]
            result["sse_reconnected_delivery"] = await sse_delivery(client, redis_client, 2)
        finally:
            await redis_client.delete(sentinel)
            await redis_client.aclose()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print("ISOLATED_RUNTIME_VERIFIED")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--redis-lifecycle", action="store_true")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists; preserve previous evidence")
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
