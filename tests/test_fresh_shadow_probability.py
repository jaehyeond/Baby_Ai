import copy

import pytest

from neural.baby.fresh_shadow_probability import (
    build_fresh_pre_question_shadow_probability_snapshot,
    validate_fresh_pre_question_shadow_probability_snapshot,
)
from neural.baby.fresh_shadow_selection import (
    build_fresh_shadow_question_selection,
    select_question_from_fresh_shadow_probabilities,
    validate_fresh_shadow_question_selection,
)
from neural.baby.pending_question_semantics import canonical_json_sha256


FEATURE_NAMES = [
    "graph_raw_score",
    "local_core_raw_score",
    "graph_rank",
    "local_core_rank",
    "graph_rank_percentile",
    "local_core_rank_percentile",
    "in_graph_top_k",
    "in_local_core_top_k",
    "in_both_top_k",
]


def _features(graph_rank: int, local_rank: int) -> dict:
    return {
        "graph_raw_score": 0.3,
        "local_core_raw_score": 0.2,
        "graph_rank": graph_rank,
        "local_core_rank": local_rank,
        "graph_rank_percentile": 1.0,
        "local_core_rank_percentile": 0.5,
        "in_graph_top_k": 1,
        "in_local_core_top_k": 1,
        "in_both_top_k": 1,
    }


def _contract(fit_sha256: str) -> dict:
    payload = {
        "fresh_pre_question_snapshot_input_contract_version": 1,
        "phase": "J1.1B",
        "status": "fresh_pre_question_snapshot_input_contract_ready_not_runtime",
        "input_contract_scope": "fresh_pre_question_shadow_input_contract",
        "input_pack_version": 1,
        "input_pack_scope": "fresh_pre_question_shadow_input_pack",
        "selection_policy": "max_mean_binary_entropy_tie_uncertainty_band_then_order",
        "question_selection_contract_sha256": "1" * 64,
        "calibrator_probability_snapshot_sha256": "2" * 64,
        "calibrator_design_audit_sha256": "3" * 64,
        "train_only_calibrator_fit_sha256": fit_sha256,
        "feature_schema_sha256": canonical_json_sha256({
            "feature_names": FEATURE_NAMES,
        }),
        "feature_names": FEATURE_NAMES,
        "required_candidate_question_count_min": 2,
        "required_question_fields": [
            "order",
            "question_id",
            "question_sha256",
            "pre_question_captured_at",
            "candidate_rows",
        ],
        "required_candidate_row_fields": ["concept_id", "feature_values"],
        "forbidden_input_fields": [
            "answer",
            "answer_sha256",
            "answer_text",
            "calibrated_probability",
            "decision",
            "label",
            "outcome",
            "post_question_captured_at",
            "probability",
            "rationale",
            "review_status",
            "selected_order",
            "selected_question_id",
            "target",
            "user_review",
        ],
        "freshness_requirements": {
            "answers_labels_reviews_and_probabilities_forbidden": True,
            "features_must_be_captured_before_question_is_shown": True,
            "pre_question_captured_at_requires_timezone": True,
            "question_text_must_be_hash_bound_not_included": True,
        },
        "fresh_pre_question_snapshot_input_contract_gate": True,
        "fresh_snapshot_runtime_gate": False,
        "question_selection_runtime_gate": False,
        "runtime_probability_snapshot_gate": False,
        "database_writes": False,
        "learning_enabled": False,
        "heldout_gate": False,
        "performance_claim_gate": False,
        "production_promotion_gate": False,
        "block_reasons": [],
        "next_step": "capture_fresh_pre_question_snapshot_shadow_read_only_before_runtime_selection",
    }
    payload["fresh_pre_question_snapshot_input_contract_sha256"] = (
        canonical_json_sha256(payload)
    )
    return payload


def _input_pack(contract: dict) -> dict:
    payload = {
        "fresh_pre_question_input_pack_version": 1,
        "phase": "J1.1B",
        "status": "fresh_pre_question_shadow_input_pack_ready_not_runtime",
        "input_pack_scope": "fresh_pre_question_shadow_input_pack",
        "source_scope": "sealed_train_capture_shadow_not_runtime_fresh",
        "selection_policy": "max_mean_binary_entropy_tie_uncertainty_band_then_order",
        "feature_schema_sha256": contract["feature_schema_sha256"],
        "feature_names": FEATURE_NAMES,
        "fresh_pre_question_snapshot_input_contract_sha256": contract[
            "fresh_pre_question_snapshot_input_contract_sha256"
        ],
        "source_independent_score_capture_sha256": "4" * 64,
        "pre_question_captured_at": "2026-07-18T10:00:00+09:00",
        "question_count": 2,
        "candidate_row_count": 4,
        "candidate_questions": [
            {
                "order": 0,
                "question_id": "q0",
                "question_sha256": "5" * 64,
                "pre_question_captured_at": "2026-07-18T10:00:00+09:00",
                "candidate_rows": [
                    {"concept_id": "q0-c0", "feature_values": _features(1, 2)},
                    {"concept_id": "q0-c1", "feature_values": _features(2, 1)},
                ],
            },
            {
                "order": 1,
                "question_id": "q1",
                "question_sha256": "6" * 64,
                "pre_question_captured_at": "2026-07-18T10:00:01+09:00",
                "candidate_rows": [
                    {"concept_id": "q1-c0", "feature_values": _features(1, 2)},
                    {"concept_id": "q1-c1", "feature_values": _features(2, 1)},
                ],
            },
        ],
        "fresh_pre_question_input_pack_gate": True,
        "fresh_snapshot_runtime_gate": False,
        "question_selection_runtime_gate": False,
        "runtime_probability_snapshot_gate": False,
        "database_writes": False,
        "learning_enabled": False,
        "heldout_gate": False,
        "performance_claim_gate": False,
        "production_promotion_gate": False,
        "block_reasons": [],
        "next_step": "compute_fresh_pre_question_shadow_probabilities_offline_before_runtime_selection",
    }
    payload["fresh_pre_question_input_pack_sha256"] = canonical_json_sha256(payload)
    return payload


def _fit() -> dict:
    payload = {
        "train_only_calibrator_fit_artifact_version": 1,
        "phase": "J1.1B",
        "status": "train_only_calibrator_fit_completed_offline_not_promoted",
        "calibrator_design_audit_sha256": "3" * 64,
        "independent_score_capture_sha256": "4" * 64,
        "union_label_pack_sha256": "7" * 64,
        "reviewed_reference_answer_pack_sha256": "8" * 64,
        "model_type": "l2_logistic_regression_binary_relevance_v1",
        "hyperparameters": {
            "l2": 0.1,
            "learning_rate": 0.1,
            "max_iterations": 1,
            "ece_bins": 5,
        },
        "feature_names": FEATURE_NAMES,
        "target_mapping": {
            "approved": 1,
            "rejected": 0,
            "uncertain": "excluded_from_fit",
        },
        "training_scope": "train_calibration_only",
        "evaluation_scope": "leave_one_question_out_on_train_calibration_only",
        "fit_row_count": 1,
        "excluded_uncertain_count": 0,
        "fold_count": 1,
        "fold_metrics": [],
        "cross_validation_predictions": [
            {
                "fold": "leave_order_0_out",
                "order": 0,
                "question_id": "q0",
                "concept_id": "q0-c0",
                "target": 1,
                "probability": 0.5,
            }
        ],
        "cross_validation_metrics": {},
        "final_train_only_model": {
            "model_type": "l2_logistic_regression_binary_relevance_v1",
            "feature_names": FEATURE_NAMES,
            "intercept": 0.0,
            "weights": {name: 0.0 for name in FEATURE_NAMES},
            "standardization": {
                "means": {name: 0.0 for name in FEATURE_NAMES},
                "scales": {name: 1.0 for name in FEATURE_NAMES},
            },
            "fitted_row_count": 1,
            "positive_count": 1,
            "negative_count": 0,
        },
        "train_only_fit_execution_gate": True,
        "offline_probabilities_computed": True,
        "runtime_probabilities_computed": False,
        "calibrator_fit_gate": True,
        "database_writes": False,
        "learning_enabled": False,
        "heldout_gate": False,
        "performance_claim_gate": False,
        "production_promotion_gate": False,
        "block_reasons": [],
        "next_step": "audit_question_selection_probability_snapshot_before_runtime_use",
    }
    payload["train_only_calibrator_fit_sha256"] = canonical_json_sha256(payload)
    return payload


def _bundle() -> tuple[dict, dict, dict]:
    fit = _fit()
    contract = _contract(fit["train_only_calibrator_fit_sha256"])
    return contract, _input_pack(contract), fit


def test_shadow_probability_snapshot_computes_offline_probabilities_only() -> None:
    contract, pack, fit = _bundle()

    snapshot = build_fresh_pre_question_shadow_probability_snapshot(
        contract,
        pack,
        fit,
    )

    assert snapshot["fresh_shadow_probability_snapshot_gate"] is True
    assert snapshot["probability_count"] == 4
    assert snapshot["fresh_snapshot_runtime_gate"] is False
    assert snapshot["question_selection_runtime_gate"] is False
    assert snapshot["database_writes"] is False
    assert snapshot["learning_enabled"] is False
    assert snapshot["next_step"] == (
        "select_fresh_shadow_question_offline_before_runtime_selection"
    )


def test_shadow_probability_snapshot_rejects_fit_binding_mismatch() -> None:
    contract, pack, fit = _bundle()
    invalid = copy.deepcopy(contract)
    invalid["train_only_calibrator_fit_sha256"] = "9" * 64
    unhashed = copy.deepcopy(invalid)
    unhashed.pop("fresh_pre_question_snapshot_input_contract_sha256")
    invalid["fresh_pre_question_snapshot_input_contract_sha256"] = (
        canonical_json_sha256(unhashed)
    )
    invalid_pack = _input_pack(invalid)

    with pytest.raises(ValueError, match="fit binding"):
        build_fresh_pre_question_shadow_probability_snapshot(
            invalid,
            invalid_pack,
            fit,
        )


def test_shadow_probability_snapshot_rejects_runtime_gate_tamper() -> None:
    contract, pack, fit = _bundle()
    snapshot = build_fresh_pre_question_shadow_probability_snapshot(
        contract,
        pack,
        fit,
    )
    snapshot["runtime_probability_snapshot_gate"] = True

    with pytest.raises(ValueError, match="runtime gates"):
        validate_fresh_pre_question_shadow_probability_snapshot(snapshot)


def test_shadow_probability_snapshot_rejects_sha256_tamper() -> None:
    contract, pack, fit = _bundle()
    snapshot = build_fresh_pre_question_shadow_probability_snapshot(
        contract,
        pack,
        fit,
    )
    snapshot["question_probability_snapshots"][0]["top_probability"] = 0.123

    with pytest.raises(ValueError, match="sha256 mismatch"):
        validate_fresh_pre_question_shadow_probability_snapshot(snapshot)


def test_fresh_shadow_question_selection_is_deterministic_offline_only() -> None:
    contract, pack, fit = _bundle()
    snapshot = build_fresh_pre_question_shadow_probability_snapshot(
        contract,
        pack,
        fit,
    )
    preview = select_question_from_fresh_shadow_probabilities(snapshot)
    selection = build_fresh_shadow_question_selection(snapshot)

    assert preview["selected_order"] == 0
    assert selection["offline_selection_preview"] == preview
    assert selection["fresh_shadow_question_selection_gate"] is True
    assert selection["question_selection_runtime_gate"] is False
    assert selection["database_writes"] is False
    assert selection["learning_enabled"] is False


def test_fresh_shadow_question_selection_rejects_runtime_gate_tamper() -> None:
    contract, pack, fit = _bundle()
    snapshot = build_fresh_pre_question_shadow_probability_snapshot(
        contract,
        pack,
        fit,
    )
    selection = build_fresh_shadow_question_selection(snapshot)
    selection["question_selection_runtime_gate"] = True

    with pytest.raises(ValueError, match="runtime gates"):
        validate_fresh_shadow_question_selection(selection)


def test_fresh_shadow_question_selection_rejects_preview_tamper() -> None:
    contract, pack, fit = _bundle()
    snapshot = build_fresh_pre_question_shadow_probability_snapshot(
        contract,
        pack,
        fit,
    )
    selection = build_fresh_shadow_question_selection(snapshot)
    selection["offline_selection_preview"]["selected_order"] = 1

    with pytest.raises(ValueError, match="deterministic"):
        validate_fresh_shadow_question_selection(selection, snapshot)
