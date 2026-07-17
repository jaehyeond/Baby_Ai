import copy

import pytest

from neural.baby.calibrator_design import build_calibrator_design_audit
from neural.baby.calibrator_fit import fit_train_only_calibrator
from neural.baby.calibrator_snapshot import (
    build_calibrator_probability_snapshot,
    validate_calibrator_probability_snapshot,
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


def _design_and_fit() -> tuple[dict, dict]:
    design = build_calibrator_design_audit(_capture(), _answers(), _labels())
    fit = fit_train_only_calibrator(design, max_iterations=80)
    return design, fit


def test_probability_snapshot_replays_every_union_candidate_offline() -> None:
    design, fit = _design_and_fit()
    snapshot = build_calibrator_probability_snapshot(design, fit)

    assert snapshot["offline_probability_snapshot_gate"] is True
    assert snapshot["runtime_probability_snapshot_gate"] is False
    assert snapshot["question_selection_runtime_gate"] is False
    assert snapshot["database_writes"] is False
    assert snapshot["learning_enabled"] is False
    assert snapshot["production_promotion_gate"] is False
    assert snapshot["question_count"] == 3
    assert snapshot["candidate_label_count"] == 12
    assert snapshot["probability_count"] == 12
    assert {item["candidate_count"] for item in snapshot["question_snapshots"]} == {4}


def test_probability_snapshot_probabilities_are_bounded_and_include_uncertain_rows() -> None:
    design, fit = _design_and_fit()
    snapshot = validate_calibrator_probability_snapshot(
        build_calibrator_probability_snapshot(design, fit),
        design,
        fit,
    )

    row_types = {
        probability["source_row_type"]
        for question in snapshot["question_snapshots"]
        for probability in question["concept_probabilities"]
    }
    assert row_types == {"fit_row", "excluded_uncertain"}
    assert all(
        0.0 <= probability["probability"] <= 1.0
        for question in snapshot["question_snapshots"]
        for probability in question["concept_probabilities"]
    )


def test_probability_snapshot_validation_rejects_runtime_gate_changes() -> None:
    design, fit = _design_and_fit()
    snapshot = build_calibrator_probability_snapshot(design, fit)
    invalid = copy.deepcopy(snapshot)
    invalid["question_selection_runtime_gate"] = True

    with pytest.raises(ValueError, match="runtime gates"):
        validate_calibrator_probability_snapshot(invalid)
