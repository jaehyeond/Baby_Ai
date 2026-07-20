"""Offline question selection over fresh shadow probabilities."""

from __future__ import annotations

import json
from typing import Any, Mapping

from neural.baby.fresh_shadow_probability import (
    validate_fresh_pre_question_shadow_probability_snapshot,
)
from neural.baby.pending_question_semantics import canonical_json_sha256
from neural.baby.question_selection_contract import SELECTION_POLICY


FRESH_SHADOW_SELECTION_VERSION = 1
FRESH_SHADOW_SELECTION_SCOPE = (
    "fresh_pre_question_shadow_probability_selection_audit"
)


def _clone(value: Mapping[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(value, ensure_ascii=False))


def _seal_selection(payload: Mapping[str, Any]) -> dict[str, Any]:
    normalized = _clone(payload)
    normalized.pop("fresh_shadow_question_selection_sha256", None)
    normalized["fresh_shadow_question_selection_sha256"] = canonical_json_sha256(
        normalized
    )
    return normalized


def _score_question(question: Mapping[str, Any]) -> tuple[float, int, int]:
    return (
        float(question["mean_binary_entropy"]),
        int(question["uncertainty_band_count_0_4_to_0_6"]),
        -int(question["order"]),
    )


def select_question_from_fresh_shadow_probabilities(
    probability_snapshot: Mapping[str, Any],
) -> dict[str, Any]:
    """Return deterministic offline selection from fresh shadow probabilities."""

    snapshot = validate_fresh_pre_question_shadow_probability_snapshot(
        probability_snapshot
    )
    candidates = list(snapshot.get("question_probability_snapshots") or [])
    if len(candidates) < 2:
        raise ValueError("fresh shadow selection requires at least two questions")
    ranked = sorted(candidates, key=_score_question, reverse=True)
    selected = ranked[0]
    runner_up = ranked[1]
    return {
        "selection_policy": SELECTION_POLICY,
        "selected_order": selected["order"],
        "selected_question_id": selected["question_id"],
        "selected_score": {
            "mean_binary_entropy": selected["mean_binary_entropy"],
            "uncertainty_band_count_0_4_to_0_6": selected[
                "uncertainty_band_count_0_4_to_0_6"
            ],
        },
        "runner_up_order": runner_up["order"],
        "runner_up_question_id": runner_up["question_id"],
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
                "question_id": item["question_id"],
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


def build_fresh_shadow_question_selection(
    probability_snapshot: Mapping[str, Any],
) -> dict[str, Any]:
    """Seal an offline fresh shadow selection artifact."""

    snapshot = validate_fresh_pre_question_shadow_probability_snapshot(
        probability_snapshot
    )
    selection = select_question_from_fresh_shadow_probabilities(snapshot)
    artifact = _seal_selection({
        "fresh_shadow_question_selection_version": FRESH_SHADOW_SELECTION_VERSION,
        "phase": "J1.1B",
        "status": "fresh_shadow_question_selection_ready_not_runtime",
        "selection_scope": FRESH_SHADOW_SELECTION_SCOPE,
        "selection_policy": SELECTION_POLICY,
        "fresh_pre_question_shadow_probability_snapshot_sha256": snapshot[
            "fresh_pre_question_shadow_probability_snapshot_sha256"
        ],
        "fresh_pre_question_input_pack_sha256": snapshot[
            "fresh_pre_question_input_pack_sha256"
        ],
        "fresh_pre_question_snapshot_input_contract_sha256": snapshot[
            "fresh_pre_question_snapshot_input_contract_sha256"
        ],
        "train_only_calibrator_fit_sha256": snapshot[
            "train_only_calibrator_fit_sha256"
        ],
        "question_count": snapshot["question_count"],
        "candidate_row_count": snapshot["candidate_row_count"],
        "probability_count": snapshot["probability_count"],
        "offline_selection_preview": selection,
        "fresh_shadow_question_selection_gate": True,
        "fresh_snapshot_runtime_gate": False,
        "question_selection_runtime_gate": False,
        "runtime_probability_snapshot_gate": False,
        "database_writes": False,
        "learning_enabled": False,
        "heldout_gate": False,
        "performance_claim_gate": False,
        "production_promotion_gate": False,
        "block_reasons": [],
        "next_step": (
            "capture_real_fresh_pre_question_shadow_inputs_read_only_"
            "before_runtime_selection"
        ),
    })
    return validate_fresh_shadow_question_selection(artifact, snapshot)


def validate_fresh_shadow_question_selection(
    payload: Mapping[str, Any],
    probability_snapshot: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    normalized = _clone(payload)
    if normalized.get("fresh_shadow_question_selection_version") != (
        FRESH_SHADOW_SELECTION_VERSION
    ):
        raise ValueError("unsupported fresh shadow question selection version")
    if normalized.get("phase") != "J1.1B":
        raise ValueError("fresh shadow question selection must be J1.1B")
    if normalized.get("status") != "fresh_shadow_question_selection_ready_not_runtime":
        raise ValueError("fresh shadow question selection status mismatch")
    if normalized.get("selection_scope") != FRESH_SHADOW_SELECTION_SCOPE:
        raise ValueError("fresh shadow question selection scope mismatch")
    if normalized.get("selection_policy") != SELECTION_POLICY:
        raise ValueError("fresh shadow question selection policy mismatch")
    if probability_snapshot is not None:
        snapshot = validate_fresh_pre_question_shadow_probability_snapshot(
            probability_snapshot
        )
        for field in (
            "fresh_pre_question_shadow_probability_snapshot_sha256",
            "fresh_pre_question_input_pack_sha256",
            "fresh_pre_question_snapshot_input_contract_sha256",
            "train_only_calibrator_fit_sha256",
            "question_count",
            "candidate_row_count",
            "probability_count",
        ):
            if normalized.get(field) != snapshot.get(field):
                raise ValueError(f"fresh shadow selection {field} mismatch")
        expected = select_question_from_fresh_shadow_probabilities(snapshot)
        if normalized.get("offline_selection_preview") != expected:
            raise ValueError("fresh shadow selection preview is not deterministic")

    selection = dict(normalized.get("offline_selection_preview") or {})
    if selection.get("selection_policy") != SELECTION_POLICY:
        raise ValueError("fresh shadow selection preview policy mismatch")
    ranked_orders = list(selection.get("ranked_orders") or [])
    if not ranked_orders or selection.get("selected_order") != ranked_orders[0].get(
        "order"
    ):
        raise ValueError("fresh shadow selection selected order mismatch")

    required_false = (
        "fresh_snapshot_runtime_gate",
        "question_selection_runtime_gate",
        "runtime_probability_snapshot_gate",
        "database_writes",
        "learning_enabled",
        "heldout_gate",
        "performance_claim_gate",
        "production_promotion_gate",
    )
    if any(normalized.get(field) is not False for field in required_false):
        raise ValueError("fresh shadow selection cannot enable runtime gates")
    if normalized.get("fresh_shadow_question_selection_gate") is not True:
        raise ValueError("fresh shadow question selection gate must be true")

    supplied_hash = str(normalized.get("fresh_shadow_question_selection_sha256") or "")
    unhashed = _clone(normalized)
    unhashed.pop("fresh_shadow_question_selection_sha256", None)
    if supplied_hash != canonical_json_sha256(unhashed):
        raise ValueError("fresh shadow question selection sha256 mismatch")
    return normalized
