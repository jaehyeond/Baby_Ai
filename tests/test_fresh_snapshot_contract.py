import copy

import pytest

from neural.baby.fresh_snapshot_contract import (
    build_fresh_pre_question_snapshot_input_contract,
    build_shadow_fresh_pre_question_snapshot_input_pack,
    seal_fresh_pre_question_snapshot_input_pack,
    validate_fresh_pre_question_snapshot_input_contract,
    validate_fresh_pre_question_snapshot_input_pack,
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


def _selection_contract(design_sha256: str) -> dict:
    payload = {
        "question_selection_contract_version": 1,
        "phase": "J1.1B",
        "status": "offline_question_selection_contract_ready_not_runtime",
        "selection_scope": "offline_train_calibration_snapshot_policy_audit",
        "selection_policy": (
            "max_mean_binary_entropy_tie_uncertainty_band_then_order"
        ),
        "calibrator_probability_snapshot_sha256": "a" * 64,
        "calibrator_design_audit_sha256": design_sha256,
        "train_only_calibrator_fit_sha256": "c" * 64,
        "question_count": 2,
        "candidate_label_count": 4,
        "probability_count": 4,
        "offline_selection_preview": {
            "selection_policy": (
                "max_mean_binary_entropy_tie_uncertainty_band_then_order"
            ),
            "selected_order": 1,
            "selected_score": {
                "mean_binary_entropy": 0.9,
                "uncertainty_band_count_0_4_to_0_6": 2,
            },
            "runner_up_order": 0,
            "runner_up_score": {
                "mean_binary_entropy": 0.8,
                "uncertainty_band_count_0_4_to_0_6": 1,
            },
            "ranked_orders": [
                {
                    "rank": 1,
                    "order": 1,
                    "mean_binary_entropy": 0.9,
                    "uncertainty_band_count_0_4_to_0_6": 2,
                    "candidate_count": 2,
                    "top_concept_id": "q1-c0",
                    "top_probability": 0.51,
                },
                {
                    "rank": 2,
                    "order": 0,
                    "mean_binary_entropy": 0.8,
                    "uncertainty_band_count_0_4_to_0_6": 1,
                    "candidate_count": 2,
                    "top_concept_id": "q0-c0",
                    "top_probability": 0.6,
                },
            ],
        },
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
    }
    payload["question_selection_contract_sha256"] = canonical_json_sha256(payload)
    return payload


def _design_audit() -> dict:
    payload = {
        "calibrator_design_audit_version": 1,
        "phase": "J1.1B",
        "status": "train_only_calibrator_design_ready_fit_not_executed",
        "independent_score_capture_sha256": "d" * 64,
        "union_label_pack_sha256": "e" * 64,
        "reviewed_reference_answer_pack_sha256": "f" * 64,
        "feature_names": FEATURE_NAMES,
        "forbidden_feature_names": [],
        "target_mapping": {
            "approved": 1,
            "rejected": 0,
            "uncertain": "excluded_from_fit",
        },
        "split_strategy": "leave_one_question_out_grouped_by_question_order",
        "question_count": 2,
        "candidate_label_count": 4,
        "fit_row_count": 4,
        "excluded_uncertain_count": 0,
        "positive_count": 2,
        "negative_count": 2,
        "decision_counts": {
            "approved": 2,
            "rejected": 2,
            "uncertain": 0,
        },
        "fold_count": 2,
        "folds": [],
        "fit_rows": [
            {
                "order": 0,
                "question_id": "q0",
                "concept_id": "q0-c0",
                "target": 1,
                "feature_values": _features(),
            },
            {
                "order": 0,
                "question_id": "q0",
                "concept_id": "q0-c1",
                "target": 0,
                "feature_values": _features(),
            },
            {
                "order": 1,
                "question_id": "q1",
                "concept_id": "q1-c0",
                "target": 1,
                "feature_values": _features(),
            },
            {
                "order": 1,
                "question_id": "q1",
                "concept_id": "q1-c1",
                "target": 0,
                "feature_values": _features(),
            },
        ],
        "excluded_rows": [],
        "reviewed_label_gate": True,
        "dual_predictor_positive_coverage_gate": True,
        "leakage_guard_gate": True,
        "minimum_label_gate": True,
        "question_grouped_split_gate": True,
        "calibrator_design_gate": True,
        "fit_execution_gate": False,
        "calibrator_fit_gate": False,
        "database_writes": False,
        "learning_enabled": False,
        "probabilities_computed": False,
        "heldout_gate": False,
        "performance_claim_gate": False,
        "production_promotion_gate": False,
        "block_reasons": [],
        "next_step": "implement_train_only_calibrator_fit_script",
    }
    payload["calibrator_design_audit_sha256"] = canonical_json_sha256(payload)
    return payload


def _features() -> dict:
    return {
        "graph_raw_score": 0.3,
        "local_core_raw_score": 0.2,
        "graph_rank": 1,
        "local_core_rank": 2,
        "graph_rank_percentile": 1.0,
        "local_core_rank_percentile": 0.5,
        "in_graph_top_k": 1,
        "in_local_core_top_k": 1,
        "in_both_top_k": 1,
    }


def _input_pack(contract: dict) -> dict:
    payload = {
        "fresh_pre_question_input_pack_version": 1,
        "phase": "J1.1B",
        "input_pack_scope": "fresh_pre_question_shadow_input_pack",
        "selection_policy": "max_mean_binary_entropy_tie_uncertainty_band_then_order",
        "feature_schema_sha256": contract["feature_schema_sha256"],
        "feature_names": contract["feature_names"],
        "fresh_pre_question_snapshot_input_contract_sha256": contract[
            "fresh_pre_question_snapshot_input_contract_sha256"
        ],
        "pre_question_captured_at": "2026-07-18T10:00:00+09:00",
        "candidate_questions": [
            {
                "order": 0,
                "question_id": "q0",
                "question_sha256": "1" * 64,
                "pre_question_captured_at": "2026-07-18T10:00:00+09:00",
                "candidate_rows": [
                    {"concept_id": "q0-c0", "feature_values": _features()},
                    {"concept_id": "q0-c1", "feature_values": _features()},
                ],
            },
            {
                "order": 1,
                "question_id": "q1",
                "question_sha256": "2" * 64,
                "pre_question_captured_at": "2026-07-18T10:00:01+09:00",
                "candidate_rows": [
                    {"concept_id": "q1-c0", "feature_values": _features()},
                    {"concept_id": "q1-c1", "feature_values": _features()},
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
    }
    return seal_fresh_pre_question_snapshot_input_pack(payload)


def _capture() -> dict:
    return {
        "captured_at": "2026-07-18T10:00:00+09:00",
        "independent_score_capture_sha256": "3" * 64,
        "questions": [
            {
                "order": 0,
                "question_id": "q0",
                "question_sha256": "1" * 64,
                "independent_union": {
                    "eligible_concept_count": 4,
                    "graph_top_k_ids": ["q0-c0"],
                    "local_core_top_k_ids": ["q0-c1"],
                    "union": [
                        {
                            "concept_id": "q0-c0",
                            "graph_raw_score": 0.9,
                            "local_core_raw_score": 0.2,
                            "graph_rank": 1,
                            "local_core_rank": 2,
                        },
                        {
                            "concept_id": "q0-c1",
                            "graph_raw_score": 0.1,
                            "local_core_raw_score": 0.8,
                            "graph_rank": 2,
                            "local_core_rank": 1,
                        },
                    ],
                },
            },
            {
                "order": 1,
                "question_id": "q1",
                "question_sha256": "2" * 64,
                "independent_union": {
                    "eligible_concept_count": 4,
                    "graph_top_k_ids": ["q1-c0"],
                    "local_core_top_k_ids": ["q1-c1"],
                    "union": [
                        {
                            "concept_id": "q1-c0",
                            "graph_raw_score": 0.7,
                            "local_core_raw_score": 0.3,
                            "graph_rank": 1,
                            "local_core_rank": 2,
                        },
                        {
                            "concept_id": "q1-c1",
                            "graph_raw_score": 0.2,
                            "local_core_raw_score": 0.6,
                            "graph_rank": 2,
                            "local_core_rank": 1,
                        },
                    ],
                },
            },
        ],
    }


def test_fresh_input_contract_binds_selection_and_design_offline_only() -> None:
    design = _design_audit()
    contract = build_fresh_pre_question_snapshot_input_contract(
        _selection_contract(design["calibrator_design_audit_sha256"]),
        design,
    )

    assert contract["fresh_pre_question_snapshot_input_contract_gate"] is True
    assert contract["fresh_snapshot_runtime_gate"] is False
    assert contract["question_selection_runtime_gate"] is False
    assert contract["database_writes"] is False
    assert contract["learning_enabled"] is False
    assert contract["required_candidate_question_count_min"] == 2
    assert contract["next_step"] == (
        "capture_fresh_pre_question_snapshot_shadow_read_only_"
        "before_runtime_selection"
    )


def test_fresh_input_contract_rejects_runtime_gate_changes() -> None:
    design = _design_audit()
    contract = build_fresh_pre_question_snapshot_input_contract(
        _selection_contract(design["calibrator_design_audit_sha256"]),
        design,
    )
    invalid = copy.deepcopy(contract)
    invalid["fresh_snapshot_runtime_gate"] = True

    with pytest.raises(ValueError, match="runtime gates"):
        validate_fresh_pre_question_snapshot_input_contract(invalid)


def test_fresh_input_pack_accepts_pre_question_features_only() -> None:
    design = _design_audit()
    contract = build_fresh_pre_question_snapshot_input_contract(
        _selection_contract(design["calibrator_design_audit_sha256"]),
        design,
    )
    pack = validate_fresh_pre_question_snapshot_input_pack(
        _input_pack(contract),
        contract,
    )

    assert len(pack["candidate_questions"]) == 2
    assert pack["fresh_pre_question_input_pack_gate"] is True
    assert pack["question_selection_runtime_gate"] is False


def test_fresh_input_pack_rejects_answer_or_label_leakage() -> None:
    design = _design_audit()
    contract = build_fresh_pre_question_snapshot_input_contract(
        _selection_contract(design["calibrator_design_audit_sha256"]),
        design,
    )
    pack = _input_pack(contract)
    pack["candidate_questions"][0]["candidate_rows"][0]["target"] = 1

    with pytest.raises(ValueError, match="forbidden field"):
        validate_fresh_pre_question_snapshot_input_pack(pack, contract)


def test_fresh_input_pack_rejects_feature_schema_drift() -> None:
    design = _design_audit()
    contract = build_fresh_pre_question_snapshot_input_contract(
        _selection_contract(design["calibrator_design_audit_sha256"]),
        design,
    )
    pack = _input_pack(contract)
    del pack["candidate_questions"][0]["candidate_rows"][0]["feature_values"][
        "graph_rank"
    ]

    with pytest.raises(ValueError, match="feature schema"):
        validate_fresh_pre_question_snapshot_input_pack(pack, contract)


def test_shadow_input_pack_builder_converts_sealed_capture_features() -> None:
    design = _design_audit()
    contract = build_fresh_pre_question_snapshot_input_contract(
        _selection_contract(design["calibrator_design_audit_sha256"]),
        design,
    )
    pack = build_shadow_fresh_pre_question_snapshot_input_pack(contract, _capture())

    assert pack["question_count"] == 2
    assert pack["candidate_row_count"] == 4
    assert pack["source_scope"] == "sealed_train_capture_shadow_not_runtime_fresh"
    assert pack["database_writes"] is False
    assert pack["learning_enabled"] is False
    assert pack["next_step"] == (
        "compute_fresh_pre_question_shadow_probabilities_offline_"
        "before_runtime_selection"
    )


def test_fresh_input_pack_rejects_sha256_tamper() -> None:
    design = _design_audit()
    contract = build_fresh_pre_question_snapshot_input_contract(
        _selection_contract(design["calibrator_design_audit_sha256"]),
        design,
    )
    pack = build_shadow_fresh_pre_question_snapshot_input_pack(contract, _capture())
    pack["source_scope"] = "tampered"

    with pytest.raises(ValueError, match="sha256 mismatch"):
        validate_fresh_pre_question_snapshot_input_pack(pack, contract)
