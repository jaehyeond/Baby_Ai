import copy

import pytest

from neural.baby.pending_question_semantics import canonical_json_sha256
from neural.baby.question_selection_contract import (
    build_question_selection_contract,
    select_question_from_probability_snapshot,
    validate_question_selection_contract,
)


def _snapshot() -> dict:
    payload = {
        "calibrator_probability_snapshot_version": 1,
        "phase": "J1.1B",
        "status": "offline_probability_snapshot_ready_not_runtime",
        "snapshot_scope": "train_calibration_replay_only",
        "snapshot_policy": "calibrated_relevance_probability_replay",
        "question_selection_policy_preview": (
            "max_mean_binary_entropy_tie_uncertainty_band_then_order"
        ),
        "calibrator_design_audit_sha256": "a" * 64,
        "train_only_calibrator_fit_sha256": "b" * 64,
        "independent_score_capture_sha256": "c" * 64,
        "union_label_pack_sha256": "d" * 64,
        "question_count": 3,
        "candidate_label_count": 6,
        "probability_count": 6,
        "question_snapshots": [
            {
                "order": 0,
                "candidate_count": 2,
                "top_concept_id": "q0-c0",
                "top_probability": 0.8,
                "mean_probability": 0.4,
                "mean_binary_entropy": 0.6,
                "uncertainty_band_count_0_4_to_0_6": 1,
                "concept_probabilities": [
                    {
                        "concept_id": "q0-c0",
                        "probability": 0.8,
                        "source_row_type": "fit_row",
                        "feature_values_sha256": "e" * 64,
                    },
                    {
                        "concept_id": "q0-c1",
                        "probability": 0.2,
                        "source_row_type": "fit_row",
                        "feature_values_sha256": "f" * 64,
                    },
                ],
            },
            {
                "order": 1,
                "candidate_count": 2,
                "top_concept_id": "q1-c0",
                "top_probability": 0.55,
                "mean_probability": 0.5,
                "mean_binary_entropy": 0.9,
                "uncertainty_band_count_0_4_to_0_6": 2,
                "concept_probabilities": [
                    {
                        "concept_id": "q1-c0",
                        "probability": 0.55,
                        "source_row_type": "fit_row",
                        "feature_values_sha256": "1" * 64,
                    },
                    {
                        "concept_id": "q1-c1",
                        "probability": 0.45,
                        "source_row_type": "excluded_uncertain",
                        "feature_values_sha256": "2" * 64,
                    },
                ],
            },
            {
                "order": 2,
                "candidate_count": 2,
                "top_concept_id": "q2-c0",
                "top_probability": 0.51,
                "mean_probability": 0.5,
                "mean_binary_entropy": 0.9,
                "uncertainty_band_count_0_4_to_0_6": 1,
                "concept_probabilities": [
                    {
                        "concept_id": "q2-c0",
                        "probability": 0.51,
                        "source_row_type": "fit_row",
                        "feature_values_sha256": "3" * 64,
                    },
                    {
                        "concept_id": "q2-c1",
                        "probability": 0.49,
                        "source_row_type": "fit_row",
                        "feature_values_sha256": "4" * 64,
                    },
                ],
            },
        ],
        "selected_order_preview": 1,
        "selected_order_preview_reason": (
            "highest_mean_binary_entropy_in_train_calibration_replay"
        ),
        "offline_probability_snapshot_gate": True,
        "runtime_probability_snapshot_gate": False,
        "question_selection_runtime_gate": False,
        "database_writes": False,
        "learning_enabled": False,
        "heldout_gate": False,
        "performance_claim_gate": False,
        "production_promotion_gate": False,
        "block_reasons": [],
        "next_step": "design_runtime_question_selection_contract_without_db_write",
    }
    payload["calibrator_probability_snapshot_sha256"] = canonical_json_sha256(
        payload
    )
    return payload


def test_selection_contract_is_deterministic_and_offline_only() -> None:
    snapshot = _snapshot()
    selection = select_question_from_probability_snapshot(snapshot)
    contract = build_question_selection_contract(snapshot)

    assert selection["selected_order"] == 1
    assert contract["offline_selection_preview"]["selected_order"] == 1
    assert contract["offline_question_selection_contract_gate"] is True
    assert contract["runtime_question_selection_gate"] is False
    assert contract["runtime_probability_snapshot_gate"] is False
    assert contract["database_writes"] is False
    assert contract["learning_enabled"] is False
    assert contract["production_promotion_gate"] is False


def test_selection_contract_validation_rejects_non_deterministic_preview() -> None:
    snapshot = _snapshot()
    contract = build_question_selection_contract(snapshot)
    invalid = copy.deepcopy(contract)
    invalid["offline_selection_preview"]["selected_order"] = 0
    invalid["offline_selection_preview"]["ranked_orders"][0]["order"] = 0

    with pytest.raises(ValueError, match="deterministic"):
        validate_question_selection_contract(invalid, snapshot)


def test_selection_contract_validation_rejects_runtime_gate_changes() -> None:
    contract = build_question_selection_contract(_snapshot())
    invalid = copy.deepcopy(contract)
    invalid["runtime_question_selection_gate"] = True

    with pytest.raises(ValueError, match="runtime gates"):
        validate_question_selection_contract(invalid)
