"""Run the preregistered B5.1 next-user-input pilot.

The seven messages are fixed before any prediction is inspected.  A double
opt-in server mode stores each pre-turn graph prediction on its Experience but
does not score the LLM's same-turn response.  After collection, the B5 offline
evaluator compares each prediction with the next user input.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import httpx
from dotenv import load_dotenv
from neo4j import AsyncGraphDatabase


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from neural.baby.neo4j_db import BrainDatabase, close_driver, init_driver
from scripts.research.b3_curiosity_snapshot import build_message_snapshot
from scripts.research import b5_external_outcome_evaluation as b5


PILOT_NAME = "b5_1_preregistered_user_input_v2_1_20260715"
PILOT_SPLIT = "train"
PILOT_MESSAGES: tuple[str, ...] = (
    "하늘과 날씨의 관계를 말해줘.",
    "날씨와 도시의 관계를 말해줘.",
    "도시와 사람의 관계를 말해줘.",
    "사람과 이름의 관계를 말해줘.",
    "이름과 비비의 관계를 말해줘.",
    "비비와 개발자의 관계를 말해줘.",
    "개발자와 프로그램의 관계를 말해줘.",
)
DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "claudedocs"
    / "research"
    / "b5_1_external_outcome_pilot_v2_1_20260715.json"
)

TURN_AUDIT_QUERY = """
MATCH (e:Experience {id: $experience_id})
OPTIONAL MATCH (cue:Concept)
WHERE cue.id IN coalesce(e.curiosity_cue_ids, [])
WITH e, collect(DISTINCT {id: cue.id, name: cue.name}) AS cues
OPTIONAL MATCH (predicted:Concept)
WHERE predicted.id IN coalesce(e.predicted_concept_ids, [])
RETURN e.id AS experience_id,
       e.task AS task,
       toString(e.created_at) AS created_at,
       e.curiosity_scoring_mode AS scoring_mode,
       e.prediction_error AS prediction_error,
       e.learning_progress AS learning_progress,
       e.external_sequence_id AS external_sequence_id,
       e.external_turn_index AS external_turn_index,
       e.external_sequence_split AS external_sequence_split,
       e.external_sequence_contract_sha256 AS external_sequence_contract_sha256,
       cues,
       collect(DISTINCT {id: predicted.id, name: predicted.name}) AS predictions
"""

CUE_STATE_QUERY = """
UNWIND $cue_ids AS requested_id
MATCH (c:Concept {id: requested_id})
RETURN c.id AS id,
       c.name AS name,
       c.curiosity_error_ema AS error_ema,
       c.learning_progress AS learning_progress,
       c.curiosity_observations AS observations
ORDER BY id
"""


def contract_sha256(messages: Iterable[str] = PILOT_MESSAGES) -> str:
    payload = json.dumps(
        list(messages),
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def validate_preregistered_contract(
    snapshots: list[dict[str, Any]],
    concepts: list[dict[str, Any]],
    *,
    captured_at: str,
) -> dict[str, Any]:
    """Check data sufficiency without exposing or adapting to predictions."""

    pairs: list[dict[str, Any]] = []
    unique_outcomes: set[str] = set()
    for index, (source, next_message) in enumerate(
        zip(snapshots, PILOT_MESSAGES[1:]),
        start=1,
    ):
        snapshot = source.get("snapshot") or {}
        cues = snapshot.get("cue_concepts") or []
        split = b5.split_next_input_terms(next_message, cues)
        vocabulary = b5._available_vocabulary(concepts, captured_at, cues)
        availability = b5.split_preexisting_outcomes(
            split["external_terms"],
            vocabulary,
        )
        unique_outcomes.update(
            b5.canonical_bucket(term)
            for term in availability["preexisting"]
            if b5.canonical_bucket(term)
        )
        pairs.append({
            "pair": index,
            "source_message": source["message"],
            "next_user_input": next_message,
            "cue_names": [item["name"] for item in cues if item.get("name")],
            "prediction_count": len(snapshot.get("predicted_concepts") or []),
            "preexisting_external_outcomes": availability["preexisting"],
            "novel_external_outcomes": availability["novel"],
        })

    scorable_pairs = [
        pair for pair in pairs if pair["preexisting_external_outcomes"]
    ]
    contract_gate = (
        len(scorable_pairs) >= b5.MIN_SCORABLE_PAIRS
        and len(unique_outcomes) >= b5.MIN_UNIQUE_EXTERNAL_OUTCOMES
        and all(pair["prediction_count"] > 0 for pair in pairs)
    )
    return {
        "message_count": len(PILOT_MESSAGES),
        "pair_count": len(pairs),
        "scorable_pair_count": len(scorable_pairs),
        "unique_preexisting_external_outcome_count": len(unique_outcomes),
        "minimum_scorable_pairs": b5.MIN_SCORABLE_PAIRS,
        "minimum_unique_external_outcomes": b5.MIN_UNIQUE_EXTERNAL_OUTCOMES,
        "contract_gate": contract_gate,
        "pairs": pairs,
    }


def validate_deferred_turn(
    record: dict[str, Any],
    expected_message: str,
    expected_sequence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Fail closed if a live turn was scored in the invalid same-turn mode."""

    cues = [item for item in record.get("cues") or [] if item and item.get("id")]
    predictions = [
        item for item in record.get("predictions") or [] if item and item.get("id")
    ]
    errors: list[str] = []
    if record.get("task") != expected_message:
        errors.append("task_mismatch")
    if record.get("scoring_mode") != "external_deferred":
        errors.append("scoring_mode_not_deferred")
    if record.get("prediction_error") is not None:
        errors.append("same_turn_prediction_error_present")
    if record.get("learning_progress") is not None:
        errors.append("same_turn_learning_progress_present")
    if not cues:
        errors.append("no_cues")
    if not predictions:
        errors.append("no_predictions")
    if expected_sequence:
        for field in (
            "external_sequence_id",
            "external_turn_index",
            "external_sequence_split",
            "external_sequence_contract_sha256",
        ):
            if record.get(field) != expected_sequence.get(field):
                errors.append(f"{field}_mismatch")
    return {
        "valid": not errors,
        "errors": errors,
        "experience_id": record.get("experience_id"),
        "task": record.get("task"),
        "created_at": record.get("created_at"),
        "scoring_mode": record.get("scoring_mode"),
        "cue_count": len(cues),
        "prediction_count": len(predictions),
        "external_sequence_id": record.get("external_sequence_id"),
        "external_turn_index": record.get("external_turn_index"),
        "external_sequence_split": record.get("external_sequence_split"),
    }


async def _fetch_all_concepts(driver: Any, database: str) -> list[dict[str, Any]]:
    async with driver.session(database=database) as session:
        result = await session.run(b5.CONCEPT_QUERY)
        return [dict(record) async for record in result]


async def _fetch_turn_audit(
    driver: Any,
    database: str,
    experience_id: str,
) -> dict[str, Any]:
    async with driver.session(database=database) as session:
        result = await session.run(
            TURN_AUDIT_QUERY,
            experience_id=experience_id,
        )
        record = await result.single()
    if not record:
        raise RuntimeError(f"Experience not found: {experience_id}")
    return dict(record)


async def _fetch_cue_states(
    driver: Any,
    database: str,
    cue_ids: list[str],
) -> list[dict[str, Any]]:
    async with driver.session(database=database) as session:
        result = await session.run(CUE_STATE_QUERY, cue_ids=cue_ids)
        return [dict(record) async for record in result]


async def _fetch_evaluation_inputs(
    driver: Any,
    database: str,
    experience_ids: list[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    async with driver.session(database=database) as session:
        result = await session.run(
            b5.SEQUENCE_QUERY,
            experience_ids=experience_ids,
        )
        sequence_records = [
            dict(record) for record in await result.fetch(len(experience_ids))
        ]
        result = await session.run(b5.HISTORY_QUERY)
        history = [dict(record) async for record in result]
        result = await session.run(b5.CONCEPT_QUERY)
        concepts = [dict(record) async for record in result]
    return sequence_records, history, concepts


async def _build_preflight(
    driver: Any,
    database: str,
    captured_at: str,
) -> tuple[dict[str, Any], list[str]]:
    await init_driver()
    try:
        db = BrainDatabase()
        snapshots = [
            await build_message_snapshot(db, message)
            for message in PILOT_MESSAGES[:-1]
        ]
    finally:
        await close_driver()
    concepts = await _fetch_all_concepts(driver, database)
    report = validate_preregistered_contract(
        snapshots,
        concepts,
        captured_at=captured_at,
    )
    cue_ids = sorted({
        str(item["id"])
        for source in snapshots
        for item in (source.get("snapshot") or {}).get("cue_concepts", [])
        if item.get("id")
    })
    return report, cue_ids


def _required_neo4j_env() -> dict[str, str]:
    required = {
        "NEO4J_URI": os.getenv("NEO4J_URI"),
        "NEO4J_USERNAME": os.getenv("NEO4J_USERNAME"),
        "NEO4J_PASSWORD": os.getenv("NEO4J_PASSWORD"),
        "NEO4J_DATABASE": os.getenv("NEO4J_DATABASE"),
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise RuntimeError(f"missing environment keys: {', '.join(missing)}")
    return {name: str(value) for name, value in required.items()}


async def _run(args: argparse.Namespace) -> dict[str, Any]:
    load_dotenv(PROJECT_ROOT / ".env")
    env = _required_neo4j_env()
    driver = AsyncGraphDatabase.driver(
        env["NEO4J_URI"],
        auth=(env["NEO4J_USERNAME"], env["NEO4J_PASSWORD"]),
    )
    started_at = datetime.now(timezone.utc).isoformat()
    try:
        await driver.verify_connectivity()
        if args.reevaluate:
            source_path = args.reevaluate.resolve()
            source_report = json.loads(source_path.read_text(encoding="utf-8"))
            experience_ids = list(source_report.get("experience_ids") or [])
            if len(experience_ids) < 2:
                raise RuntimeError("reevaluation artifact has fewer than two Experience IDs")
            records, history, concepts = await _fetch_evaluation_inputs(
                driver,
                env["NEO4J_DATABASE"],
                experience_ids,
            )
            source_name = str(source_report.get("pilot_name") or "b5_1_reevaluation")
            pairs, missing_ids = b5.build_sequence_pairs(
                records,
                sequences=((source_name, tuple(experience_ids)),),
            )
            return {
                "status": "reevaluated",
                "source_artifact": str(source_path),
                "pilot_name": source_name,
                "contract_sha256": source_report.get("contract_sha256"),
                "experience_ids": experience_ids,
                "evaluation": b5.summarize_evaluation(
                    pairs,
                    concepts,
                    history,
                    missing_experience_ids=missing_ids,
                ),
                "reevaluated_at": datetime.now(timezone.utc).isoformat(),
            }

        preflight, preflight_cue_ids = await _build_preflight(
            driver,
            env["NEO4J_DATABASE"],
            started_at,
        )
        base_report: dict[str, Any] = {
            "pilot_name": PILOT_NAME,
            "contract_sha256": contract_sha256(),
            "messages": list(PILOT_MESSAGES),
            "started_at": started_at,
            "preflight": preflight,
        }
        if not preflight["contract_gate"]:
            return {**base_report, "status": "blocked_by_preflight"}
        if args.preflight_only:
            return {**base_report, "status": "preflight_passed"}

        cue_states_before = await _fetch_cue_states(
            driver,
            env["NEO4J_DATABASE"],
            preflight_cue_ids,
        )

        async with httpx.AsyncClient(base_url=args.base_url, timeout=120.0) as client:
            health = await client.get("/health")
            health.raise_for_status()
            health_payload = health.json()
            if not health_payload.get("curiosity_external_outcome_eval_enabled"):
                raise RuntimeError("server external-outcome deferred mode is not enabled")
            if not health_payload.get("curiosity_external_sequence_contract_required"):
                raise RuntimeError("server external sequence contract is not required")

            turns: list[dict[str, Any]] = []
            experience_ids: list[str] = []
            for index, message in enumerate(PILOT_MESSAGES, start=1):
                response = await client.post(
                    "/api/conversation",
                    json={
                        "message": message,
                        "context": {
                            "speaker_id": "b5_1_pilot",
                            "external_outcome_evaluation": True,
                            "external_sequence_id": PILOT_NAME,
                            "external_turn_index": index - 1,
                            "external_sequence_split": PILOT_SPLIT,
                            "external_sequence_contract_sha256": contract_sha256(),
                        },
                    },
                )
                response.raise_for_status()
                payload = response.json()
                experience_id = payload.get("experience_id")
                if not experience_id:
                    raise RuntimeError(f"turn {index} returned no Experience ID")
                audit_record = await _fetch_turn_audit(
                    driver,
                    env["NEO4J_DATABASE"],
                    experience_id,
                )
                audit = validate_deferred_turn(
                    audit_record,
                    message,
                    {
                        "external_sequence_id": PILOT_NAME,
                        "external_turn_index": index - 1,
                        "external_sequence_split": PILOT_SPLIT,
                        "external_sequence_contract_sha256": contract_sha256(),
                    },
                )
                turns.append({"turn": index, **audit})
                experience_ids.append(experience_id)
                if not audit["valid"]:
                    raise RuntimeError(
                        f"turn {index} deferred audit failed: {audit['errors']}"
                    )
                if index < len(PILOT_MESSAGES) and args.delay:
                    await asyncio.sleep(args.delay)

        cue_states_after = await _fetch_cue_states(
            driver,
            env["NEO4J_DATABASE"],
            preflight_cue_ids,
        )
        cue_states_unchanged = cue_states_before == cue_states_after
        if not cue_states_unchanged:
            raise RuntimeError("deferred mode changed Concept curiosity state")

        records, history, concepts = await _fetch_evaluation_inputs(
            driver,
            env["NEO4J_DATABASE"],
            experience_ids,
        )
        pairs, missing_ids = b5.build_sequence_pairs(
            records,
            sequences=((PILOT_NAME, tuple(experience_ids)),),
        )
        evaluation = b5.summarize_evaluation(
            pairs,
            concepts,
            history,
            missing_experience_ids=missing_ids,
        )
        return {
            **base_report,
            "status": "completed",
            "health": {
                "status": health_payload.get("status"),
                "backend": health_payload.get("backend"),
                "external_outcome_eval_enabled": True,
                "external_sequence_contract_required": True,
            },
            "turns": turns,
            "deferred_state_audit": {
                "cue_count": len(preflight_cue_ids),
                "concept_curiosity_states_unchanged": cue_states_unchanged,
            },
            "experience_ids": experience_ids,
            "evaluation": evaluation,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }
    finally:
        await driver.close()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Preregistered live B5.1 external-outcome pilot",
    )
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--delay", type=float, default=0.25)
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument(
        "--reevaluate",
        type=Path,
        help="read an existing pilot artifact and rerun scoring without live calls",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if args.delay < 0:
        parser.error("--delay must be non-negative")
    return args


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = _parse_args()
    report = asyncio.run(_run(args))
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    print(rendered)
    if not args.preflight_only and report.get("status") in {"completed", "reevaluated"}:
        output = args.output.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(f"{rendered}\n", encoding="utf-8")


if __name__ == "__main__":
    main()
