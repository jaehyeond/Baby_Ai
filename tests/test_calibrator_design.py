import copy

import pytest

from neural.baby.calibrator_design import (
    CALIBRATOR_DESIGN_FEATURE_NAMES,
    build_calibrator_design_audit,
    validate_calibrator_design_audit,
)
from neural.baby.candidate_universe import seal_union_label_pack


def _capture() -> dict:
    questions = []
    for order in range(2):
        prefix = f"q{order}"
        union = [
            {
                "concept_id": f"{prefix}-c0",
                "concept_name": "memory",
                "graph_raw_score": 0.9,
                "graph_rank": 1,
                "local_core_raw_score": -0.4,
                "local_core_rank": 2,
            },
            {
                "concept_id": f"{prefix}-c1",
                "concept_name": "learning",
                "graph_raw_score": 0.3,
                "graph_rank": 2,
                "local_core_raw_score": -0.1,
                "local_core_rank": 1,
            },
            {
                "concept_id": f"{prefix}-c2",
                "concept_name": "noise",
                "graph_raw_score": 0.1,
                "graph_rank": 3,
                "local_core_raw_score": -0.8,
                "local_core_rank": 3,
            },
            {
                "concept_id": f"{prefix}-c3",
                "concept_name": "ambiguous",
                "graph_raw_score": 0.05,
                "graph_rank": 4,
                "local_core_raw_score": -0.9,
                "local_core_rank": 4,
            },
        ]
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
        ],
    }


def _reviewed_labels() -> dict:
    entries = []
    for order in range(2):
        prefix = f"q{order}"
        entries.append({
            "order": order,
            "question_id": f"question-{order}",
            "question_sha256": f"{order}" * 64,
            "answer_sha256": ("c" if order == 0 else "d") * 64,
            "labels": [
                {
                    "concept_id": f"{prefix}-c0",
                    "concept_name": "memory",
                    "decision": "approved",
                    "rationale": "relevant graph candidate",
                },
                {
                    "concept_id": f"{prefix}-c1",
                    "concept_name": "learning",
                    "decision": "approved",
                    "rationale": "relevant local-core candidate",
                },
                {
                    "concept_id": f"{prefix}-c2",
                    "concept_name": "noise",
                    "decision": "rejected",
                    "rationale": "not relevant",
                },
                {
                    "concept_id": f"{prefix}-c3",
                    "concept_name": "ambiguous",
                    "decision": "uncertain",
                    "rationale": "ambiguous label",
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
        "label_count": 8,
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


def test_calibrator_design_uses_reviewed_binary_targets_and_excludes_uncertain() -> None:
    audit = build_calibrator_design_audit(
        _capture(), _answers(), _reviewed_labels()
    )

    assert audit["calibrator_design_gate"] is True
    assert audit["fit_execution_gate"] is False
    assert audit["calibrator_fit_gate"] is False
    assert audit["fit_row_count"] == 6
    assert audit["positive_count"] == 4
    assert audit["negative_count"] == 2
    assert audit["excluded_uncertain_count"] == 2
    assert audit["question_grouped_split_gate"] is True
    assert all(fold["fold_gate"] for fold in audit["folds"])


def test_calibrator_design_features_exclude_label_and_text_leakage() -> None:
    audit = build_calibrator_design_audit(
        _capture(), _answers(), _reviewed_labels()
    )

    forbidden = {"concept_name", "rationale", "decision", "question", "answer"}
    assert set(audit["feature_names"]) == set(CALIBRATOR_DESIGN_FEATURE_NAMES)
    assert forbidden.isdisjoint(audit["feature_names"])
    for row in audit["fit_rows"]:
        assert set(row["feature_values"]) == set(CALIBRATOR_DESIGN_FEATURE_NAMES)
        assert "concept_name" not in row
        assert "rationale" not in row


def test_calibrator_design_rejects_draft_labels() -> None:
    draft = copy.deepcopy(_reviewed_labels())
    draft["review_status"] = "awaiting_user_review"
    draft["reviewer_role"] = "assistant_draft"
    draft["reviewed_at"] = None
    for entry in draft["entries"]:
        for label in entry["labels"]:
            label["decision"] = f"proposed_{label['decision']}"
    draft = seal_union_label_pack(draft)

    with pytest.raises(ValueError, match="explicit user review"):
        build_calibrator_design_audit(_capture(), _answers(), draft)


def test_calibrator_design_audit_validation_catches_schema_drift() -> None:
    audit = build_calibrator_design_audit(
        _capture(), _answers(), _reviewed_labels()
    )
    invalid = copy.deepcopy(audit)
    invalid["feature_names"] = [*invalid["feature_names"], "concept_name"]

    with pytest.raises(ValueError, match="feature schema"):
        validate_calibrator_design_audit(invalid)
