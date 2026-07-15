"""Run a small live B3 conversation pilot and collect Neo4j observability.

Each message invokes the real FastAPI/Gemini conversation path and therefore
creates an Experience.  The script is intentionally sequential and prints the
created Experience IDs so every graph mutation remains auditable.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv
from neo4j import AsyncGraphDatabase


PROJECT_ROOT = Path(__file__).resolve().parents[2]

EXPERIENCE_QUERY = """
MATCH (e:Experience {id: $experience_id})
OPTIONAL MATCH (cue:Concept)
WHERE cue.id IN coalesce(e.curiosity_cue_ids, [])
WITH e, collect(DISTINCT {id: cue.id, name: cue.name}) AS cue_concepts
OPTIONAL MATCH (predicted:Concept)
WHERE predicted.id IN coalesce(e.predicted_concept_ids, [])
WITH e, cue_concepts,
     collect(DISTINCT {id: predicted.id, name: predicted.name}) AS predicted_concepts
OPTIONAL MATCH (e)-[:INVOLVES]->(actual:Concept)
WITH e, cue_concepts, predicted_concepts,
     collect(DISTINCT {id: actual.id, name: actual.name}) AS actual_concepts
OPTIONAL MATCH (cl:CuriosityLog)-[:TRIGGERED_BY]->(e)
RETURN e.prediction_error AS prediction_error,
       e.learning_progress AS learning_progress,
       e.integration_priority AS integration_priority,
       coalesce(e.curiosity_gated, false) AS gated,
       e.curiosity_target_id AS target_id,
       e.curiosity_primary_cue_id AS primary_cue_id,
       e.curiosity_primary_cue_name AS primary_cue_name,
       e.curiosity_primary_error_ema AS primary_error_ema,
       e.curiosity_primary_observations AS primary_observations,
       e.curiosity_cue_states_json AS cue_states_json,
       e.curiosity_actual_concept_ids AS scored_actual_concept_ids,
       e.curiosity_excluded_input_concept_ids AS excluded_input_concept_ids,
       cue_concepts,
       predicted_concepts,
       actual_concepts,
       collect(DISTINCT {
         id: cl.id,
         query: cl.query,
         source: cl.source,
         status: cl.status,
         target_key: cl.target_key
       }) AS curiosity_logs
"""


def _without_null_nodes(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [item for item in items if item and item.get("id")]


async def fetch_experience_observability(
    driver: Any,
    *,
    database: str,
    experience_id: str,
) -> dict[str, Any]:
    """Read the B3 fields and linked concepts for one created Experience."""

    async with driver.session(database=database) as session:
        result = await session.run(EXPERIENCE_QUERY, experience_id=experience_id)
        record = await result.single()
    if not record:
        raise RuntimeError(f"Experience not found: {experience_id}")

    cue_states_json = record["cue_states_json"]
    return {
        "prediction_error": record["prediction_error"],
        "learning_progress": record["learning_progress"],
        "integration_priority": record["integration_priority"],
        "gated": bool(record["gated"]),
        "target_id": record["target_id"],
        "primary_cue": {
            "id": record["primary_cue_id"],
            "name": record["primary_cue_name"],
            "error_ema": record["primary_error_ema"],
            "observations": record["primary_observations"],
        },
        "cue_states": json.loads(cue_states_json) if cue_states_json else [],
        "scored_actual_concept_ids": record["scored_actual_concept_ids"] or [],
        "excluded_input_concept_ids": record["excluded_input_concept_ids"] or [],
        "cue_concepts": _without_null_nodes(record["cue_concepts"] or []),
        "predicted_concepts": _without_null_nodes(
            record["predicted_concepts"] or []
        ),
        "actual_concepts": _without_null_nodes(record["actual_concepts"] or []),
        "curiosity_logs": _without_null_nodes(record["curiosity_logs"] or []),
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Live Phase 3 B3 curiosity pilot")
    parser.add_argument("--message", action="append", required=True)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--speaker-id", default="guest")
    parser.add_argument("--delay", type=float, default=0.25)
    args = parser.parse_args()
    if args.delay < 0:
        parser.error("--delay must be non-negative")
    return args


async def _run(args: argparse.Namespace) -> dict[str, Any]:
    load_dotenv(PROJECT_ROOT / ".env")
    required = {
        "NEO4J_URI": os.getenv("NEO4J_URI"),
        "NEO4J_USERNAME": os.getenv("NEO4J_USERNAME"),
        "NEO4J_PASSWORD": os.getenv("NEO4J_PASSWORD"),
        "NEO4J_DATABASE": os.getenv("NEO4J_DATABASE"),
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise RuntimeError(f"missing environment keys: {', '.join(missing)}")

    driver = AsyncGraphDatabase.driver(
        required["NEO4J_URI"],
        auth=(required["NEO4J_USERNAME"], required["NEO4J_PASSWORD"]),
    )
    results: list[dict[str, Any]] = []
    try:
        await driver.verify_connectivity()
        async with httpx.AsyncClient(base_url=args.base_url, timeout=120.0) as client:
            health = await client.get("/health")
            health.raise_for_status()

            for index, message in enumerate(args.message, start=1):
                response = await client.post(
                    "/api/conversation",
                    json={
                        "message": message,
                        "context": {"speaker_id": args.speaker_id},
                    },
                )
                response.raise_for_status()
                payload = response.json()
                experience_id = payload.get("experience_id")
                if not experience_id:
                    raise RuntimeError(f"turn {index} returned no Experience ID")

                observability = await fetch_experience_observability(
                    driver,
                    database=required["NEO4J_DATABASE"],
                    experience_id=experience_id,
                )
                results.append({
                    "turn": index,
                    "message": message,
                    "experience_id": experience_id,
                    "output": payload.get("output"),
                    "observability": observability,
                })
                if index < len(args.message) and args.delay:
                    await asyncio.sleep(args.delay)
    finally:
        await driver.close()

    return {
        "request_count": len(args.message),
        "speaker_id": args.speaker_id,
        "results": results,
    }


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = _parse_args()
    report = asyncio.run(_run(args))
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
