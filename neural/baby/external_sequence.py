"""Fail-closed contract for B5 external-outcome conversation sequences."""

from __future__ import annotations

import re
from typing import Any, Iterable


EXTERNAL_SEQUENCE_CONTEXT_KEYS = (
    "external_sequence_id",
    "external_turn_index",
    "external_sequence_split",
    "external_sequence_contract_sha256",
)
EXTERNAL_SEQUENCE_SPLITS = frozenset({"train", "heldout"})
_SEQUENCE_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{2,127}$")
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
MAX_EXTERNAL_TURN_INDEX = 9_999


def parse_external_sequence_context(context: dict[str, Any] | None) -> dict[str, Any]:
    """Normalize one sequence turn or raise ``ValueError`` before live work."""

    raw = dict(context or {})
    missing = [key for key in EXTERNAL_SEQUENCE_CONTEXT_KEYS if raw.get(key) is None]
    if missing:
        raise ValueError(f"missing external sequence fields: {', '.join(missing)}")

    sequence_id = str(raw["external_sequence_id"]).strip().casefold()
    if not _SEQUENCE_ID_PATTERN.fullmatch(sequence_id):
        raise ValueError(
            "external_sequence_id must be 3-128 lowercase letters, digits, '.', '_', or '-'"
        )

    turn_index = raw["external_turn_index"]
    if isinstance(turn_index, bool) or not isinstance(turn_index, int):
        raise ValueError("external_turn_index must be an integer")
    if turn_index < 0 or turn_index > MAX_EXTERNAL_TURN_INDEX:
        raise ValueError(
            f"external_turn_index must be between 0 and {MAX_EXTERNAL_TURN_INDEX}"
        )

    split = str(raw["external_sequence_split"]).strip().casefold()
    if split not in EXTERNAL_SEQUENCE_SPLITS:
        raise ValueError("external_sequence_split must be 'train' or 'heldout'")

    contract_sha256 = str(raw["external_sequence_contract_sha256"]).strip().casefold()
    if not _SHA256_PATTERN.fullmatch(contract_sha256):
        raise ValueError("external_sequence_contract_sha256 must be 64 lowercase hex chars")

    return {
        "sequence_id": sequence_id,
        "turn_index": turn_index,
        "split": split,
        "contract_sha256": contract_sha256,
    }


def validate_external_sequence_state(
    contract: dict[str, Any],
    existing_turns: Iterable[dict[str, Any]],
    *,
    conflicting_split_count: int = 0,
) -> dict[str, Any]:
    """Validate contiguous order and train/heldout isolation against DB state."""

    normalized = parse_external_sequence_context({
        "external_sequence_id": contract.get("sequence_id"),
        "external_turn_index": contract.get("turn_index"),
        "external_sequence_split": contract.get("split"),
        "external_sequence_contract_sha256": contract.get("contract_sha256"),
    })
    turns = [dict(item) for item in existing_turns]
    if int(conflicting_split_count or 0) > 0:
        return {
            "status": "rejected",
            "reason": "contract_reused_across_splits",
            "expected_turn_index": None,
        }

    indices: list[int] = []
    for item in turns:
        index = item.get("turn_index")
        if isinstance(index, bool) or not isinstance(index, int) or index < 0:
            return {
                "status": "rejected",
                "reason": "invalid_existing_turn_index",
                "expected_turn_index": None,
            }
        if item.get("split") != normalized["split"]:
            return {
                "status": "rejected",
                "reason": "sequence_split_mismatch",
                "expected_turn_index": None,
            }
        if item.get("contract_sha256") != normalized["contract_sha256"]:
            return {
                "status": "rejected",
                "reason": "sequence_contract_mismatch",
                "expected_turn_index": None,
            }
        indices.append(index)

    if len(indices) != len(set(indices)):
        return {
            "status": "rejected",
            "reason": "invalid_existing_duplicate_turn",
            "expected_turn_index": None,
        }
    ordered = sorted(indices)
    if ordered != list(range(len(ordered))):
        return {
            "status": "rejected",
            "reason": "invalid_existing_sequence_gap",
            "expected_turn_index": None,
        }

    expected = len(ordered)
    requested = normalized["turn_index"]
    if requested in indices:
        reason = "duplicate_turn_index"
    elif requested != expected:
        reason = "out_of_order_turn"
    else:
        return {
            "status": "valid",
            "reason": None,
            "expected_turn_index": expected,
        }
    return {
        "status": "rejected",
        "reason": reason,
        "expected_turn_index": expected,
    }
