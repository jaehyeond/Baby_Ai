"""B5.6 offline contract and read-only Neo4j preflight.

No question is created and no answer is submitted by this script.  Write
queries are checked only with Neo4j ``EXPLAIN``.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from neural.baby.pending_question_outcome import (
    build_pending_question_terms,
    normalize_pending_question_prediction,
    parse_pending_question_action_contract,
    prediction_precedes_question,
    validate_pending_question_action_state,
    validate_pending_question_answer_state,
)


DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "claudedocs"
    / "research"
    / "b5_6_pending_question_action_outcome_20260716.json"
)
TRAIN_HASH = hashlib.sha256(b"b5_6_pending_question_train_fixture").hexdigest()


def _metadata(**overrides: Any) -> dict[str, Any]:
    value = {
        "policy_action_id": "b5_6_action_fixture",
        "question_outcome_split": "train",
        "question_outcome_contract_sha256": TRAIN_HASH,
    }
    value.update(overrides)
    return value


def _snapshot(**overrides: Any) -> dict[str, Any]:
    value = {
        "cue_concepts": [{"id": "cue-1", "name": "서울"}],
        "predicted_concepts": [{"id": "pred-1", "name": "날씨"}],
        "input_terms": ["서울"],
        "captured_at": "2026-07-16T00:00:00+00:00",
    }
    value.update(overrides)
    return value


def _question(**overrides: Any) -> dict[str, Any]:
    value = {
        "id": "question-1",
        "status": "pending",
        "question_outcome_evaluation": True,
        "question_outcome_policy_action_key": "policy:b5_6_action_fixture",
        "question_outcome_split": "train",
        "question_outcome_contract_sha256": TRAIN_HASH,
        "prediction_captured_at": "2026-07-16T00:00:00+00:00",
        "curiosity_cue_ids": ["cue-1"],
        "predicted_concept_ids": ["pred-1"],
    }
    value.update(overrides)
    return value


def build_contract_report() -> dict[str, Any]:
    cases: list[dict[str, Any]] = []

    def check(name: str, operation: Callable[[], bool]) -> None:
        try:
            passed = bool(operation())
            detail = None
        except Exception as exc:  # reported as evidence, not silently swallowed
            passed = False
            detail = f"{type(exc).__name__}: {exc}"
        cases.append({"name": name, "passed": passed, "detail": detail})

    def rejects(metadata: dict[str, Any]) -> bool:
        try:
            parse_pending_question_action_contract(metadata)
        except ValueError:
            return True
        return False

    explicit = parse_pending_question_action_contract(_metadata())
    curiosity = parse_pending_question_action_contract({
        "curiosity_log_id": "curiosity-fixture",
        "question_outcome_split": "train",
        "question_outcome_contract_sha256": TRAIN_HASH,
    })
    check("explicit_policy_action_valid", lambda: explicit["policy_action_key"].startswith("policy:"))
    check("curiosity_action_valid", lambda: curiosity["policy_action_key"] == "curiosity:curiosity-fixture")
    check("missing_action_provenance_rejected", lambda: rejects({
        "question_outcome_split": "train",
        "question_outcome_contract_sha256": TRAIN_HASH,
    }))
    check("invalid_split_rejected", lambda: rejects(_metadata(
        question_outcome_split="validation"
    )))
    check("invalid_hash_rejected", lambda: rejects(_metadata(
        question_outcome_contract_sha256="abc"
    )))
    check("new_action_state_valid", lambda: validate_pending_question_action_state(
        explicit, []
    )["status"] == "valid")
    check("missing_curiosity_source_rejected", lambda: validate_pending_question_action_state(
        curiosity, [], curiosity_log_exists=False
    )["reason"] == "curiosity_log_not_found")
    check("duplicate_action_rejected", lambda: validate_pending_question_action_state(
        explicit, [{"question_id": "existing"}]
    )["reason"] == "duplicate_policy_action")
    check("cross_split_hash_reuse_rejected", lambda: validate_pending_question_action_state(
        explicit, [], conflicting_split_count=1
    )["reason"] == "contract_reused_across_splits")
    check("pre_display_prediction_valid", lambda: normalize_pending_question_prediction(
        _snapshot()
    )["predicted_ids"] == ["pred-1"])
    check("post_display_prediction_rejected", lambda: not prediction_precedes_question(
        "2026-07-16T00:00:01+00:00",
        "2026-07-16T00:00:00+00:00",
    ))

    def empty_prediction_rejected() -> bool:
        try:
            normalize_pending_question_prediction(_snapshot(predicted_concepts=[]))
        except ValueError:
            return True
        return False

    check("empty_prediction_rejected", empty_prediction_rejected)
    check("legacy_answer_route_preserved", lambda: validate_pending_question_answer_state(
        {"status": "pending"}
    )["status"] == "legacy")
    check("new_research_answer_ready", lambda: validate_pending_question_answer_state(
        _question()
    )["status"] == "ready")
    check("duplicate_answer_rejected", lambda: validate_pending_question_answer_state(
        _question(status="answered", answer="existing")
    )["reason"] == "question_already_answered")
    check("handler_independent_terms", lambda: (
        "서울" in build_pending_question_terms("서울의 날씨를 설명해줘")
        and "날씨" in build_pending_question_terms("서울의 날씨를 설명해줘")
        and "설명해줘" not in build_pending_question_terms("서울의 날씨를 설명해줘")
    ))

    passed = sum(case["passed"] for case in cases)
    return {
        "status": "offline_contract_passed" if passed == len(cases) else "offline_contract_failed",
        "phase": "B5.6",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "database_writes": False,
        "live_collection_started": False,
        "heldout_collection_started": False,
        "existing_answer_reuse": False,
        "prediction_scoring_started": False,
        "learning_state_updates": False,
        "production_promotion_gate": False,
        "target_validity_gate": False,
        "evaluation_readiness_gate": False,
        "instrumentation_contract_gate": passed == len(cases),
        "protected_handler_change_required": False,
        "single_writer_research_contract": True,
        "production_concurrency_constraint_required": True,
        "server_opt_in_env": "CURIOSITY_QUESTION_OUTCOME_EVAL",
        "case_count": len(cases),
        "passed_case_count": passed,
        "cases": cases,
        "next_gate": (
            "collect_new_train_questions_only_after_explicit_user_approval"
        ),
    }


async def run_database_preflight() -> dict[str, Any]:
    """Run real state reads and EXPLAIN every persistence query without writes."""

    from neural.baby.neo4j_db import (
        BrainDatabase,
        PENDING_QUESTION_ACTION_PERSIST_QUERY,
        PENDING_QUESTION_ACTION_PERSIST_WITH_CURIOSITY_QUERY,
        PENDING_QUESTION_ACTION_SPLIT_CONFLICT_QUERY,
        PENDING_QUESTION_ACTION_STATE_QUERY,
        PENDING_QUESTION_ANSWER_PERSIST_QUERY,
        PENDING_QUESTION_ANSWER_STATE_QUERY,
        PENDING_QUESTION_CURIOSITY_SOURCE_QUERY,
        PENDING_QUESTION_OUTCOME_CONCEPT_QUERY,
        _DB_NAME,
        close_driver,
        get_driver,
        init_driver,
    )

    coverage_query = """
    MATCH (pq:PendingQuestion)
    WITH pq, properties(pq) AS props
    RETURN count(pq) AS pending_question_count,
           sum(CASE WHEN pq.answer IS NOT NULL THEN 1 ELSE 0 END)
             AS existing_answer_count,
           sum(CASE WHEN props['question_outcome_evaluation'] = true THEN 1 ELSE 0 END)
             AS research_question_count,
           sum(CASE WHEN props['external_outcome_concept_ids'] IS NOT NULL THEN 1 ELSE 0 END)
             AS research_outcome_count
    """
    contract = parse_pending_question_action_contract(_metadata(
        policy_action_id="b5_6_readonly_preflight"
    ))
    explain_jobs = {
        "action_state": (
            PENDING_QUESTION_ACTION_STATE_QUERY,
            {
                "policy_action_key": contract["policy_action_key"],
                "policy_action_key_name": "question_outcome_policy_action_key",
                "split_key_name": "question_outcome_split",
                "contract_key_name": "question_outcome_contract_sha256",
            },
        ),
        "split_conflict": (
            PENDING_QUESTION_ACTION_SPLIT_CONFLICT_QUERY,
            {
                "contract_sha256": contract["contract_sha256"],
                "split": "train",
                "contract_key_name": "question_outcome_contract_sha256",
                "split_key_name": "question_outcome_split",
            },
        ),
        "curiosity_source": (
            PENDING_QUESTION_CURIOSITY_SOURCE_QUERY,
            {"curiosity_log_id": "b5_6_explain_only"},
        ),
        "question_persist": (
            PENDING_QUESTION_ACTION_PERSIST_QUERY,
            {"props": {"question": "EXPLAIN only"}},
        ),
        "question_persist_with_curiosity": (
            PENDING_QUESTION_ACTION_PERSIST_WITH_CURIOSITY_QUERY,
            {
                "props": {"question": "EXPLAIN only"},
                "curiosity_log_id": "b5_6_explain_only",
                "policy_action_key": contract["policy_action_key"],
                "contract_sha256": contract["contract_sha256"],
                "recorded_at": "2026-07-16T00:00:00+00:00",
            },
        ),
        "answer_state": (
            PENDING_QUESTION_ANSWER_STATE_QUERY,
            {"question_id": "b5_6_explain_only"},
        ),
        "outcome_resolution": (
            PENDING_QUESTION_OUTCOME_CONCEPT_QUERY,
            {
                "outcome_terms": ["서울"],
                "prediction_captured_at": "2026-07-16T00:00:00+00:00",
                "cue_ids": [],
            },
        ),
        "answer_persist": (
            PENDING_QUESTION_ANSWER_PERSIST_QUERY,
            {
                "question_id": "b5_6_explain_only",
                "answer": "EXPLAIN only",
                "answer_confidence": 0.5,
                "answered_at": "2026-07-16T00:00:00+00:00",
                "outcome_terms_json": "[]",
                "outcome_concept_ids": [],
            },
        ),
    }

    await init_driver()
    try:
        state = await BrainDatabase().validate_pending_question_action(contract)
        explained: dict[str, str] = {}
        async with get_driver().session(database=_DB_NAME) as session:
            result = await session.run(coverage_query)
            coverage_record = await result.single()
            result = await session.run(
                PENDING_QUESTION_OUTCOME_CONCEPT_QUERY,
                outcome_terms=["서울"],
                prediction_captured_at=datetime.now(timezone.utc).isoformat(),
                cue_ids=[],
            )
            runtime_outcomes = [dict(item) async for item in result]
            for name, (query, parameters) in explain_jobs.items():
                result = await session.run(f"EXPLAIN {query}", **parameters)
                await result.consume()
                explained[name] = "valid"
        return {
            "status": state.get("status"),
            "reason": state.get("reason"),
            "current_coverage": dict(coverage_record) if coverage_record else {},
            "outcome_resolution_runtime_count": len(runtime_outcomes),
            "explained_queries": explained,
            "database_writes": False,
        }
    finally:
        await close_driver()


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(
        description="B5.6 PendingQuestion action-outcome contract"
    )
    parser.add_argument(
        "--db-preflight",
        action="store_true",
        help="also run real read-only queries and EXPLAIN write queries",
    )
    args = parser.parse_args()

    report = build_contract_report()
    if args.db_preflight:
        preflight = asyncio.run(run_database_preflight())
        report["database_preflight"] = preflight
        if preflight.get("status") != "valid" or any(
            value != "valid"
            for value in preflight.get("explained_queries", {}).values()
        ):
            report["status"] = "offline_contract_failed"
            report["instrumentation_contract_gate"] = False

    DEFAULT_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    DEFAULT_OUTPUT.write_text(f"{rendered}\n", encoding="utf-8")
    print(rendered)
    if report["status"] != "offline_contract_passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
