"""Read-only B5.5 gate for choosing a grounded prediction target.

This gate separates two questions that B5.4 had coupled:

1. Is the target definition causally aligned with an action the baby can choose?
2. Does the current database already contain leak-free pre-outcome predictions?

Existing answered questions are coverage evidence only.  They must never be
retrospectively scored because their answers were visible before any prediction
snapshot was stored.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from neo4j import AsyncGraphDatabase


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_B5_4_ARTIFACT = (
    PROJECT_ROOT
    / "claudedocs"
    / "research"
    / "b5_4_train_ablation_20260716.json"
)
DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "claudedocs"
    / "research"
    / "b5_5_target_validity_gate_20260716.json"
)
MIN_PAIRED_OUTCOMES = 6


COVERAGE_QUERY = """
CALL () {
  MATCH (e:Experience)
  WHERE e.task_type = 'conversation'
  RETURN count(e) AS conversation_count,
         sum(CASE WHEN e.output IS NOT NULL AND trim(e.output) <> ''
                  THEN 1 ELSE 0 END) AS conversation_with_output,
         sum(CASE WHEN e.output CONTAINS '?' THEN 1 ELSE 0 END)
           AS assistant_question_output_count,
         sum(CASE WHEN e.external_sequence_id IS NOT NULL THEN 1 ELSE 0 END)
           AS external_sequence_turn_count,
         sum(CASE WHEN e.external_sequence_id IS NOT NULL
                       AND size(coalesce(e.predicted_concept_ids, [])) > 0
                  THEN 1 ELSE 0 END) AS external_turn_with_prediction_snapshot
}
CALL () {
  MATCH (:Experience)-[r:NEXT_EXTERNAL_TURN]->(:Experience)
  RETURN count(r) AS external_sequence_link_count
}
CALL () {
  MATCH (pq:PendingQuestion)
  OPTIONAL MATCH (:CuriosityLog)-[link]->(pq)
  WITH pq, properties(pq) AS props,
       collect(DISTINCT type(link)) AS inbound_types
  RETURN count(pq) AS pending_question_count,
         sum(CASE WHEN pq.status = 'answered' THEN 1 ELSE 0 END)
           AS answered_question_count,
         sum(CASE WHEN pq.question IS NOT NULL AND trim(pq.question) <> ''
                  THEN 1 ELSE 0 END) AS pending_with_question,
         sum(CASE WHEN pq.answer IS NOT NULL AND trim(pq.answer) <> ''
                  THEN 1 ELSE 0 END) AS pending_with_answer,
         sum(CASE WHEN pq.answer IS NOT NULL
                       AND pq.asked_at IS NOT NULL
                       AND pq.answered_at IS NOT NULL
                       AND datetime(pq.answered_at) >= datetime(pq.asked_at)
                  THEN 1 ELSE 0 END) AS ordered_answer_count,
         sum(CASE WHEN pq.answer IS NOT NULL
                       AND pq.asked_at IS NOT NULL
                       AND pq.answered_at IS NOT NULL
                       AND datetime(pq.answered_at) < datetime(pq.asked_at)
                  THEN 1 ELSE 0 END) AS answer_before_question_count,
         sum(CASE WHEN pq.answer IS NOT NULL
                       AND (pq.asked_at IS NULL OR pq.answered_at IS NULL)
                  THEN 1 ELSE 0 END) AS answered_missing_time_count,
         sum(CASE WHEN 'GENERATED' IN inbound_types THEN 1 ELSE 0 END)
           AS generated_from_curiosity_count,
         sum(CASE WHEN size(coalesce(props['predicted_concept_ids'], [])) > 0
                  THEN 1 ELSE 0 END) AS pending_with_prediction_snapshot,
         sum(CASE WHEN pq.answer IS NOT NULL
                        AND size(coalesce(props['predicted_concept_ids'], [])) > 0
                        AND props['prediction_captured_at'] IS NOT NULL
                        AND pq.asked_at IS NOT NULL
                        AND datetime(props['prediction_captured_at']) <= datetime(pq.asked_at)
                   THEN 1 ELSE 0 END)
           AS pending_prediction_before_question_count
}
CALL () {
  MATCH (e:Experience)
  WHERE e.task_type = 'vision'
  RETURN count(e) AS vision_count,
         sum(CASE WHEN e.head_pose IS NOT NULL THEN 1 ELSE 0 END)
           AS vision_with_head_pose,
         sum(CASE WHEN size(coalesce(e.predicted_concept_ids, [])) > 0
                  THEN 1 ELSE 0 END) AS vision_with_prediction_snapshot
}
CALL () {
  MATCH (:Experience)-[r:NEXT_FRAME]->(:Experience)
  RETURN count(r) AS next_frame_count,
         sum(CASE WHEN r.pose_delta IS NOT NULL THEN 1 ELSE 0 END)
           AS next_frame_with_pose_delta
}
RETURN *
"""

PENDING_SOURCE_QUERY = """
MATCH (pq:PendingQuestion)
RETURN coalesce(pq.source, '<missing>') AS source,
       coalesce(pq.status, '<missing>') AS status,
       count(*) AS count
ORDER BY source, status
"""


def _count(coverage: dict[str, Any], key: str) -> int:
    return int(coverage.get(key) or 0)


def evaluate_target_candidates(
    coverage: dict[str, Any],
    b5_4_evidence: dict[str, Any],
) -> dict[str, Any]:
    """Choose a target definition without treating old outcomes as predictions."""

    external_turns = _count(coverage, "external_sequence_turn_count")
    external_links = _count(coverage, "external_sequence_link_count")
    external_snapshots = _count(
        coverage,
        "external_turn_with_prediction_snapshot",
    )
    b5_4_eval = b5_4_evidence.get("evaluation") or {}
    b5_4_train_signal = bool(b5_4_eval.get("any_exploratory_gate_passed"))

    answered = _count(coverage, "answered_question_count")
    with_answer = _count(coverage, "pending_with_answer")
    ordered_answers = _count(coverage, "ordered_answer_count")
    generated_questions = _count(
        coverage,
        "generated_from_curiosity_count",
    )
    pending_snapshots = _count(
        coverage,
        "pending_with_prediction_snapshot",
    )
    pre_question_predictions = _count(
        coverage,
        "pending_prediction_before_question_count",
    )

    next_user_criteria = {
        "external_outcome": True,
        "deterministic_pair_boundary": external_links > 0,
        "source_prediction_before_outcome": external_snapshots >= external_turns > 0,
        "recorded_action_identity": False,
        "outcome_conditioned_on_baby_action": False,
        "directly_closes_action_selection_loop": False,
    }
    next_user_valid = all(next_user_criteria.values())

    pending_definition_criteria = {
        "external_outcome": with_answer > 0,
        "deterministic_pair_boundary": answered > 0,
        "recorded_action_identity": _count(coverage, "pending_with_question") > 0,
        "action_precedes_outcome": (
            with_answer > 0 and ordered_answers == with_answer
        ),
        "outcome_conditioned_on_baby_action": True,
        "curiosity_policy_link_supported_by_schema": True,
    }
    pending_schema_gate = all(
        value
        for key, value in pending_definition_criteria.items()
        if key != "action_precedes_outcome"
    )
    pending_target_valid = all(pending_definition_criteria.values())
    pending_readiness_criteria = {
        "minimum_paired_outcomes": answered >= MIN_PAIRED_OUTCOMES,
        "pre_answer_prediction_snapshots": (
            pre_question_predictions >= MIN_PAIRED_OUTCOMES
        ),
        "curiosity_selected_actions": (
            generated_questions >= MIN_PAIRED_OUTCOMES
        ),
        "retrospective_scoring_forbidden": True,
    }
    pending_evaluation_ready = (
        pending_target_valid
        and all(pending_readiness_criteria.values())
    )

    vision_action_count = min(
        _count(coverage, "vision_with_head_pose"),
        _count(coverage, "next_frame_with_pose_delta"),
    )
    vision_criteria = {
        "external_outcome": _count(coverage, "next_frame_count") > 0,
        "deterministic_pair_boundary": _count(coverage, "next_frame_count") > 0,
        "recorded_action_identity": vision_action_count > 0,
        "action_precedes_outcome": vision_action_count > 0,
        "pre_outcome_prediction_snapshot": (
            _count(coverage, "vision_with_prediction_snapshot")
            >= MIN_PAIRED_OUTCOMES
        ),
        "directly_closes_action_selection_loop": True,
    }
    vision_valid = all(vision_criteria.values())

    candidates = {
        "unconditioned_next_user_topic": {
            "target_validity_gate": next_user_valid,
            "evaluation_readiness_gate": (
                next_user_valid
                and external_links >= MIN_PAIRED_OUTCOMES
                and b5_4_train_signal
            ),
            "criteria": next_user_criteria,
            "observed_pair_count": external_links,
            "empirical_train_signal": b5_4_train_signal,
            "verdict": "rejected_not_action_conditioned",
        },
        "action_conditioned_pending_question_answer": {
            "target_schema_gate": pending_schema_gate,
            "target_validity_gate": pending_target_valid,
            "evaluation_readiness_gate": pending_evaluation_ready,
            "definition_criteria": pending_definition_criteria,
            "readiness_criteria": pending_readiness_criteria,
            "observed_pair_count": answered,
            "eligible_pre_answer_prediction_count": pending_snapshots,
            "prediction_before_question_count": pre_question_predictions,
            "curiosity_selected_pair_count": generated_questions,
            "existing_answers_reusable_for_scoring": False,
            "verdict": (
                "valid_target_instrumentation_required"
                if pending_target_valid and not pending_evaluation_ready
                else "ready_for_preregistered_evaluation"
                if pending_evaluation_ready
                else "invalid_target"
            ),
        },
        "action_conditioned_next_sensor_outcome": {
            "target_validity_gate": vision_valid,
            "evaluation_readiness_gate": vision_valid,
            "criteria": vision_criteria,
            "observed_pair_count": _count(coverage, "next_frame_count"),
            "observed_action_count": vision_action_count,
            "verdict": "deferred_no_recorded_action_or_prediction",
        },
    }

    selected = (
        "action_conditioned_pending_question_answer"
        if pending_target_valid
        else None
    )
    recommended = (
        "action_conditioned_pending_question_answer"
        if pending_schema_gate
        else None
    )
    return {
        "selected_target": selected,
        "recommended_instrumentation_target": recommended,
        "target_selection_gate": selected is not None,
        "evaluation_readiness_gate": bool(
            selected and candidates[selected]["evaluation_readiness_gate"]
        ),
        "production_promotion_gate": False,
        "candidates": candidates,
        "decision": (
            "select_pending_question_answer_but_instrument_before_new_data"
            if selected and not pending_evaluation_ready
            else "selected_target_ready_for_preregistered_evaluation"
            if selected
            else "no_current_target_valid_recommend_pending_question_contract"
            if recommended
            else "no_valid_target_or_schema"
        ),
        "next_contract": {
            "phase": "B5.6",
            "protected_handler_change_required": False,
            "required_before_question_is_shown": [
                "curiosity_log_id_or_policy_action_id",
                "question_id",
                "prediction_captured_at",
                "predicted_concept_ids",
                "evaluation_split",
                "contract_sha256",
            ],
            "required_when_answer_arrives": [
                "answered_at",
                "external_answer_text",
                "external_outcome_concept_ids",
            ],
            "forbidden": [
                "score_existing_15_answers_retrospectively",
                "collect_heldout_before_train_signal",
                "change_production_threshold",
                "modify_conversation_handler_v30",
            ],
        },
    }


async def fetch_coverage(driver: Any, database: str) -> dict[str, Any]:
    async with driver.session(database=database) as session:
        result = await session.run(COVERAGE_QUERY)
        record = await result.single()
        result = await session.run(PENDING_SOURCE_QUERY)
        sources = [dict(item) async for item in result]
    return {
        **(dict(record) if record else {}),
        "pending_sources": sources,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read-only B5.5 target validity gate",
    )
    parser.add_argument("--b5-4-artifact", type=Path, default=DEFAULT_B5_4_ARTIFACT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--compact", action="store_true")
    return parser.parse_args()


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

    b5_4_path = args.b5_4_artifact.resolve()
    b5_4_evidence = json.loads(b5_4_path.read_text(encoding="utf-8"))
    driver = AsyncGraphDatabase.driver(
        str(required["NEO4J_URI"]),
        auth=(required["NEO4J_USERNAME"], required["NEO4J_PASSWORD"]),
    )
    try:
        await driver.verify_connectivity()
        coverage = await fetch_coverage(driver, str(required["NEO4J_DATABASE"]))
    finally:
        await driver.close()

    return {
        "status": "completed",
        "phase": "B5.5",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_b5_4_artifact": str(b5_4_path),
        "database_writes": False,
        "live_collection_started": False,
        "coverage": coverage,
        "gate": evaluate_target_candidates(coverage, b5_4_evidence),
    }


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = _parse_args()
    report = asyncio.run(_run(args))
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    output.write_text(f"{rendered}\n", encoding="utf-8")

    printed = report
    if args.compact:
        printed = {
            "status": report["status"],
            "database_writes": report["database_writes"],
            "live_collection_started": report["live_collection_started"],
            "coverage": report["coverage"],
            "selected_target": report["gate"]["selected_target"],
            "recommended_instrumentation_target": report["gate"][
                "recommended_instrumentation_target"
            ],
            "target_selection_gate": report["gate"]["target_selection_gate"],
            "evaluation_readiness_gate": report["gate"]["evaluation_readiness_gate"],
            "production_promotion_gate": report["gate"]["production_promotion_gate"],
            "decision": report["gate"]["decision"],
            "candidates": {
                name: {
                    "target_validity_gate": candidate["target_validity_gate"],
                    "evaluation_readiness_gate": candidate[
                        "evaluation_readiness_gate"
                    ],
                    "verdict": candidate["verdict"],
                }
                for name, candidate in report["gate"]["candidates"].items()
            },
            "output": str(output),
        }
    print(json.dumps(printed, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
