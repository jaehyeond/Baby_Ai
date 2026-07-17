"""Offline question-selection contract for J1.1B calibrated snapshots.

This module validates a deterministic selection policy over a sealed offline
probability snapshot.  It does not execute runtime question selection, write
the database, enable learning, or promote production behavior.
"""

from __future__ import annotations

import json
from typing import Any, Mapping

from neural.baby.calibrator_snapshot import (
    validate_calibrator_probability_snapshot,
)
from neural.baby.pending_question_semantics import canonical_json_sha256


QUESTION_SELECTION_CONTRACT_VERSION = 1
SELECTION_POLICY = "max_mean_binary_entropy_tie_uncertainty_band_then_order"
SELECTION_SCOPE = "offline_train_calibration_snapshot_policy_audit"


def _clone(value: Mapping[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(value, ensure_ascii=False))


def _seal_selection_contract(payload: Mapping[str, Any]) -> dict[str, Any]:
    normalized = _clone(payload)
    normalized.pop("question_selection_contract_sha256", None)
    normalized["question_selection_contract_sha256"] = canonical_json_sha256(
        normalized
    )
    return normalized


def _score_question(question: Mapping[str, Any]) -> tuple[float, int, int]:
    return (
        float(question["mean_binary_entropy"]),
        int(question["uncertainty_band_count_0_4_to_0_6"]),
        -int(question["order"]),
    )


def select_question_from_probability_snapshot(
    snapshot: Mapping[str, Any],
) -> dict[str, Any]:
    """Return deterministic offline selection preview from a sealed snapshot."""

    validated = validate_calibrator_probability_snapshot(snapshot)
    candidates = list(validated.get("question_snapshots") or [])
    if len(candidates) < 2:
        raise ValueError("question selection requires at least two candidates")
    ranked = sorted(candidates, key=_score_question, reverse=True)
    selected = ranked[0]
    runner_up = ranked[1]
    return {
        "selection_policy": SELECTION_POLICY,
        "selected_order": selected["order"],
        "selected_score": {
            "mean_binary_entropy": selected["mean_binary_entropy"],
            "uncertainty_band_count_0_4_to_0_6": selected[
                "uncertainty_band_count_0_4_to_0_6"
            ],
        },
        "runner_up_order": runner_up["order"],
        "runner_up_score": {
            "mean_binary_entropy": runner_up["mean_binary_entropy"],
            "uncertainty_band_count_0_4_to_0_6": runner_up[
                "uncertainty_band_count_0_4_to_0_6"
            ],
        },
        "ranked_orders": [
            {
                "rank": index + 1,
                "order": item["order"],
                "mean_binary_entropy": item["mean_binary_entropy"],
                "uncertainty_band_count_0_4_to_0_6": item[
                    "uncertainty_band_count_0_4_to_0_6"
                ],
                "candidate_count": item["candidate_count"],
                "top_concept_id": item["top_concept_id"],
                "top_probability": item["top_probability"],
            }
            for index, item in enumerate(ranked)
        ],
    }


def build_question_selection_contract(
    snapshot: Mapping[str, Any],
) -> dict[str, Any]:
    """Seal the offline selection policy audit for a probability snapshot."""

    validated = validate_calibrator_probability_snapshot(snapshot)
    selection = select_question_from_probability_snapshot(validated)
    contract = _seal_selection_contract({
        "question_selection_contract_version": QUESTION_SELECTION_CONTRACT_VERSION,
        "phase": "J1.1B",
        "status": "offline_question_selection_contract_ready_not_runtime",
        "selection_scope": SELECTION_SCOPE,
        "selection_policy": SELECTION_POLICY,
        "calibrator_probability_snapshot_sha256": validated[
            "calibrator_probability_snapshot_sha256"
        ],
        "calibrator_design_audit_sha256": validated[
            "calibrator_design_audit_sha256"
        ],
        "train_only_calibrator_fit_sha256": validated[
            "train_only_calibrator_fit_sha256"
        ],
        "question_count": validated["question_count"],
        "candidate_label_count": validated["candidate_label_count"],
        "probability_count": validated["probability_count"],
        "offline_selection_preview": selection,
        "offline_question_selection_contract_gate": True,
        "runtime_question_selection_gate": False,
        "runtime_probability_snapshot_gate": False,
        "database_writes": False,
        "learning_enabled": False,
        "heldout_gate": False,
        "performance_claim_gate": False,
        "production_promotion_gate": False,
        "block_reasons": [],
        "next_step": "define_fresh_pre_question_snapshot_inputs_before_runtime",
    })
    return validate_question_selection_contract(contract, validated)


def validate_question_selection_contract(
    payload: Mapping[str, Any],
    snapshot: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    normalized = _clone(payload)
    if normalized.get("question_selection_contract_version") != (
        QUESTION_SELECTION_CONTRACT_VERSION
    ):
        raise ValueError("unsupported question_selection_contract_version")
    if normalized.get("phase") != "J1.1B":
        raise ValueError("question selection contract must be J1.1B")
    if normalized.get("selection_scope") != SELECTION_SCOPE:
        raise ValueError("question selection scope mismatch")
    if normalized.get("selection_policy") != SELECTION_POLICY:
        raise ValueError("question selection policy mismatch")
    if snapshot is not None:
        validated_snapshot = validate_calibrator_probability_snapshot(snapshot)
        for field in (
            "calibrator_probability_snapshot_sha256",
            "calibrator_design_audit_sha256",
            "train_only_calibrator_fit_sha256",
            "question_count",
            "candidate_label_count",
            "probability_count",
        ):
            if normalized.get(field) != validated_snapshot.get(field):
                raise ValueError(f"question selection {field} binding mismatch")
        expected = select_question_from_probability_snapshot(validated_snapshot)
        if normalized.get("offline_selection_preview") != expected:
            raise ValueError("question selection preview is not deterministic")
    selection = dict(normalized.get("offline_selection_preview") or {})
    if selection.get("selection_policy") != SELECTION_POLICY:
        raise ValueError("offline selection preview policy mismatch")
    ranked_orders = list(selection.get("ranked_orders") or [])
    if not ranked_orders or selection.get("selected_order") != ranked_orders[0].get(
        "order"
    ):
        raise ValueError("offline selection preview selected order mismatch")
    required_false = (
        "runtime_question_selection_gate",
        "runtime_probability_snapshot_gate",
        "database_writes",
        "learning_enabled",
        "heldout_gate",
        "performance_claim_gate",
        "production_promotion_gate",
    )
    if any(normalized.get(field) is not False for field in required_false):
        raise ValueError("question selection contract cannot enable runtime gates")
    if normalized.get("offline_question_selection_contract_gate") is not True:
        raise ValueError("offline question selection contract gate must be true")
    supplied_hash = str(normalized.get("question_selection_contract_sha256") or "")
    unhashed = _clone(normalized)
    unhashed.pop("question_selection_contract_sha256", None)
    if supplied_hash != canonical_json_sha256(unhashed):
        raise ValueError("question_selection_contract_sha256 mismatch")
    return normalized
