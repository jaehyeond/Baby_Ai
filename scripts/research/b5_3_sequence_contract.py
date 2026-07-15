"""Offline B5.3 sequence-contract matrix; no Neo4j or live model calls."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from neural.baby.external_sequence import (
    EXTERNAL_SEQUENCE_CONTEXT_KEYS,
    parse_external_sequence_context,
    validate_external_sequence_state,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "claudedocs"
    / "research"
    / "b5_3_sequence_contract_20260716.json"
)
TRAIN_HASH = hashlib.sha256(b"b5_3_contract_train_fixture").hexdigest()
HELDOUT_HASH = hashlib.sha256(b"b5_3_contract_heldout_fixture").hexdigest()


def _context(
    *,
    sequence_id: str = "b5_3_train_fixture",
    turn_index: int = 0,
    split: str = "train",
    contract_hash: str = TRAIN_HASH,
) -> dict[str, Any]:
    return {
        "external_sequence_id": sequence_id,
        "external_turn_index": turn_index,
        "external_sequence_split": split,
        "external_sequence_contract_sha256": contract_hash,
    }


def _turn(
    turn_index: int,
    *,
    split: str = "train",
    contract_hash: str = TRAIN_HASH,
) -> dict[str, Any]:
    return {
        "turn_index": turn_index,
        "split": split,
        "contract_sha256": contract_hash,
    }


def build_contract_report() -> dict[str, Any]:
    cases: list[dict[str, Any]] = []

    def run_state_case(
        name: str,
        context: dict[str, Any],
        existing: list[dict[str, Any]],
        expected_status: str,
        expected_reason: str | None,
        *,
        conflicting_split_count: int = 0,
    ) -> None:
        result = validate_external_sequence_state(
            parse_external_sequence_context(context),
            existing,
            conflicting_split_count=conflicting_split_count,
        )
        cases.append({
            "name": name,
            "passed": (
                result["status"] == expected_status
                and result.get("reason") == expected_reason
            ),
            "expected_status": expected_status,
            "expected_reason": expected_reason,
            "actual_status": result["status"],
            "actual_reason": result.get("reason"),
            "expected_turn_index": result.get("expected_turn_index"),
        })

    run_state_case("first_train_turn", _context(), [], "valid", None)
    run_state_case(
        "next_contiguous_train_turn",
        _context(turn_index=2),
        [_turn(0), _turn(1)],
        "valid",
        None,
    )
    run_state_case(
        "duplicate_turn_rejected",
        _context(turn_index=1),
        [_turn(0), _turn(1)],
        "rejected",
        "duplicate_turn_index",
    )
    run_state_case(
        "gap_rejected",
        _context(turn_index=2),
        [_turn(0)],
        "rejected",
        "out_of_order_turn",
    )
    run_state_case(
        "split_change_rejected",
        _context(turn_index=1),
        [_turn(0, split="heldout")],
        "rejected",
        "sequence_split_mismatch",
    )
    run_state_case(
        "manifest_change_rejected",
        _context(turn_index=1),
        [_turn(0, contract_hash=HELDOUT_HASH)],
        "rejected",
        "sequence_contract_mismatch",
    )
    run_state_case(
        "train_heldout_hash_reuse_rejected",
        _context(turn_index=1),
        [_turn(0)],
        "rejected",
        "contract_reused_across_splits",
        conflicting_split_count=1,
    )

    missing_field_passed = False
    try:
        missing = _context()
        missing.pop("external_turn_index")
        parse_external_sequence_context(missing)
    except ValueError:
        missing_field_passed = True
    cases.append({
        "name": "missing_field_rejected",
        "passed": missing_field_passed,
        "expected_status": "rejected",
        "expected_reason": "invalid_contract_shape",
        "actual_status": "rejected" if missing_field_passed else "accepted",
        "actual_reason": "invalid_contract_shape" if missing_field_passed else None,
    })

    return {
        "status": "offline_contract_passed" if all(
            case["passed"] for case in cases
        ) else "offline_contract_failed",
        "phase": "B5.3",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "database_writes": False,
        "live_collection_started": False,
        "production_promotion_gate": False,
        "required_context_fields": list(EXTERNAL_SEQUENCE_CONTEXT_KEYS),
        "turn_index_origin": 0,
        "allowed_splits": ["train", "heldout"],
        "single_writer_research_contract": True,
        "production_concurrency_constraint_required": True,
        "case_count": len(cases),
        "passed_case_count": sum(case["passed"] for case in cases),
        "cases": cases,
    }


async def run_database_preflight() -> dict[str, Any]:
    """Exercise the real read-only Cypher path without creating a turn."""

    from neural.baby.neo4j_db import (
        BrainDatabase,
        EXTERNAL_SEQUENCE_PERSIST_QUERY,
        _DB_NAME,
        close_driver,
        get_driver,
        init_driver,
    )

    await init_driver()
    try:
        state = await BrainDatabase().validate_external_sequence_turn(
            parse_external_sequence_context(_context(
                sequence_id="b5_3_readonly_preflight",
                turn_index=0,
                split="train",
                contract_hash=TRAIN_HASH,
            ))
        )
        async with get_driver().session(database=_DB_NAME) as session:
            result = await session.run(
                f"EXPLAIN {EXTERNAL_SEQUENCE_PERSIST_QUERY}",
                experience_id="b5_3_explain_only",
                cue_ids=[],
                predicted_ids=[],
                input_terms_json="[]",
                captured_at="2026-07-16T00:00:00+00:00",
                sequence_id="b5_3_readonly_preflight",
                turn_index=0,
                previous_turn_index=-1,
                split="train",
                contract_sha256=TRAIN_HASH,
                recorded_at="2026-07-16T00:00:00+00:00",
                sequence_id_key="external_sequence_id",
                turn_index_key="external_turn_index",
            )
            await result.consume()
        return {**state, "persist_query_explain": "valid"}
    finally:
        await close_driver()


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Offline B5.3 sequence contract")
    parser.add_argument(
        "--db-preflight",
        action="store_true",
        help="also run the real read-only Neo4j sequence-state query",
    )
    args = parser.parse_args()
    report = build_contract_report()
    if args.db_preflight:
        database_preflight = asyncio.run(run_database_preflight())
        report["database_preflight"] = database_preflight
        if database_preflight.get("status") != "valid":
            report["status"] = "offline_contract_failed"
    DEFAULT_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    DEFAULT_OUTPUT.write_text(f"{rendered}\n", encoding="utf-8")
    print(rendered)
    if report["status"] != "offline_contract_passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
