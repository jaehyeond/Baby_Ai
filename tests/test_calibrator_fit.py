import copy

import pytest

from neural.baby.calibrator_design import build_calibrator_design_audit
from neural.baby.calibrator_fit import (
    fit_train_only_calibrator,
    validate_train_only_calibrator_fit,
)
from neural.baby.candidate_universe import seal_union_label_pack


def _capture() -> dict:
    questions = []
    for order in range(3):
        prefix = f"q{order}"
        union = []
        for index, name in enumerate(("memory", "learning", "noise", "ambiguous")):
            union.append({
                "concept_id": f"{prefix}-c{index}",
                "concept_name": name,
                "graph_raw_score": 1.0 - (index * 0.2) + (order * 0.01),
                "graph_rank": index + 1,
                "local_core_raw_score": -0.1 - (index * 0.2) - (order * 0.01),
                "local_core_rank": index + 1,
            })
        questions.append({
            "order": order,
            "question_id": f"question-{order}",
            "question_sha256": f"{order}" * 64,
            "independent_union": {
                "eligible_concept_count": 4,
                "top_k": 2,
                "selection_rule": "graph_top_k_union_local_core_top_k",
                "graph_top_k_ids": [f"{prefix}-c0", f"{prefix}-c1"],
                "local_core_top_k_ids": [f"{prefix}-c1", f"{prefix}-c0"],
                "union_count": 4,
                "union": union,
            },
        })
    return {
        "independent_score_capture_sha256": "a" * 64,
        "questions": questions,
    }


def _answers() -> dict:
    return {
        "reference_answer_pack_sha256": "b" * 64,
        "review_status": "user_reviewed",
        "answers": [
            {"order": 0, "answer_sha256": "c" * 64},
            {"order": 1, "answer_sha256": "d" * 64},
            {"order": 2, "answer_sha256": "e" * 64},
        ],
    }


def _labels() -> dict:
    entries = []
    answer_hashes = ["c" * 64, "d" * 64, "e" * 64]
    for order in range(3):
        prefix = f"q{order}"
        entries.append({
            "order": order,
            "question_id": f"question-{order}",
            "question_sha256": f"{order}" * 64,
            "answer_sha256": answer_hashes[order],
            "labels": [
                {
                    "concept_id": f"{prefix}-c0",
                    "concept_name": "memory",
                    "decision": "approved",
                    "rationale": "positive graph and local candidate",
                },
                {
                    "concept_id": f"{prefix}-c1",
                    "concept_name": "learning",
                    "decision": "approved",
                    "rationale": "second positive candidate",
                },
                {
                    "concept_id": f"{prefix}-c2",
                    "concept_name": "noise",
                    "decision": "rejected",
                    "rationale": "negative candidate",
                },
                {
                    "concept_id": f"{prefix}-c3",
                    "concept_name": "ambiguous",
                    "decision": "uncertain",
                    "rationale": "excluded from fit",
                },
            ],
        })
    return seal_union_label_pack({
        "union_label_pack_version": 1,
        "phase": "J1.1B",
        "independent_score_capture_sha256": "a" * 64,
        "reviewed_reference_answer_pack_sha256": "b" * 64,
        "semantic_label_source": (
            "external_teacher_drafted_against_user_reviewed_reference_answers"
        ),
        "review_status": "user_reviewed",
        "reviewer_role": "user",
        "reviewed_at": "2026-07-18T12:00:00+09:00",
        "label_count": 12,
        "entries": entries,
        "user_direct_answers": False,
        "database_writes": False,
        "learning_enabled": False,
        "probabilities_computed": False,
        "calibrator_fit_allowed": False,
        "heldout_gate": False,
        "performance_claim_gate": False,
        "production_promotion_gate": False,
    })


def _design() -> dict:
    return build_calibrator_design_audit(_capture(), _answers(), _labels())


def test_train_only_calibrator_fit_is_offline_and_deterministic() -> None:
    design = _design()
    first = fit_train_only_calibrator(design, max_iterations=80)
    second = fit_train_only_calibrator(design, max_iterations=80)

    assert first["train_only_calibrator_fit_sha256"] == second[
        "train_only_calibrator_fit_sha256"
    ]
    assert first["train_only_fit_execution_gate"] is True
    assert first["offline_probabilities_computed"] is True
    assert first["runtime_probabilities_computed"] is False
    assert first["database_writes"] is False
    assert first["learning_enabled"] is False
    assert first["heldout_gate"] is False
    assert first["production_promotion_gate"] is False
    assert first["fold_count"] == 3
    assert first["cross_validation_metrics"]["row_count"] == design["fit_row_count"]


def test_train_only_calibrator_predictions_are_bounded_and_bound_to_design() -> None:
    design = _design()
    artifact = fit_train_only_calibrator(design, max_iterations=80)
    validated = validate_train_only_calibrator_fit(artifact, design)

    assert validated["calibrator_design_audit_sha256"] == design[
        "calibrator_design_audit_sha256"
    ]
    assert len(validated["cross_validation_predictions"]) == design["fit_row_count"]
    assert all(
        0.0 <= item["probability"] <= 1.0
        for item in validated["cross_validation_predictions"]
    )
    assert set(validated["final_train_only_model"]["weights"]) == set(
        design["feature_names"]
    )


def test_train_only_calibrator_validation_rejects_runtime_gate_changes() -> None:
    artifact = fit_train_only_calibrator(_design(), max_iterations=80)
    invalid = copy.deepcopy(artifact)
    invalid["production_promotion_gate"] = True

    with pytest.raises(ValueError, match="runtime gates"):
        validate_train_only_calibrator_fit(invalid)
