import copy

import pytest

from neural.baby.candidate_universe import (
    build_independent_union,
    build_union_label_readiness_report,
    classify_candidate_vocabulary,
    exclude_question_cue_surfaces,
    seal_candidate_vocabulary,
    seal_independent_score_capture,
    seal_union_label_pack,
    validate_candidate_vocabulary,
    validate_independent_score_capture,
    validate_union_label_pack,
)


def test_validity_filter_is_predictor_neutral_and_auditable() -> None:
    eligible, rejected = classify_candidate_vocabulary([
        {"id": "memory", "name": "기억"},
        {"id": "robot", "name": "로봇"},
        {"id": "speech", "name": "설명해줘"},
        {"id": "tool", "name": "Search_dictionary"},
        {"id": "duplicate-a", "name": "컴퓨터"},
        {"id": "duplicate-b", "name": " 컴퓨터 "},
        {"id": "missing", "name": ""},
    ])

    assert [item["concept_id"] for item in eligible] == ["memory", "robot"]
    reasons = {item["concept_id"]: item["reason"] for item in rejected}
    assert reasons["speech"] == "audited_invalid_surface"
    assert reasons["tool"] == "audited_invalid_surface"
    assert reasons["duplicate-a"] == "duplicate_normalized_name"
    assert reasons["duplicate-b"] == "duplicate_normalized_name"
    assert reasons["missing"] == "missing_concept_name"


def test_question_cues_and_surface_fragments_cannot_compete() -> None:
    eligible, excluded = exclude_question_cue_surfaces([
        {"concept_id": "computer", "concept_name": "컴퓨터"},
        {"concept_id": "computer-topic", "concept_name": "컴퓨터라"},
        {"concept_id": "computer-polite", "concept_name": "컴퓨터요"},
        {"concept_id": "robot", "concept_name": "로봇"},
        {"concept_id": "hardware", "concept_name": "하드웨어"},
    ], ["컴퓨터", "로봇"])

    assert [item["concept_id"] for item in eligible] == ["hardware"]
    assert {item["reason"] for item in excluded} == {
        "exact_question_cue",
        "question_cue_surface_variant",
    }


def test_independent_union_requires_both_full_vocabulary_rankings() -> None:
    concepts = [
        {"concept_id": "a", "concept_name": "A"},
        {"concept_id": "b", "concept_name": "B"},
        {"concept_id": "c", "concept_name": "C"},
    ]
    graph = [
        {**concepts[0], "raw_score": 3.0},
        {**concepts[1], "raw_score": 2.0},
        {**concepts[2], "raw_score": 1.0},
    ]
    local = [
        {**concepts[2], "raw_score": 3.0},
        {**concepts[1], "raw_score": 2.0},
        {**concepts[0], "raw_score": 1.0},
    ]

    result = build_independent_union(concepts, graph, local, top_k=1)

    assert result["graph_top_k_ids"] == ["a"]
    assert result["local_core_top_k_ids"] == ["c"]
    assert [item["concept_id"] for item in result["union"]] == ["a", "c"]
    assert result["probabilities_computed"] is False
    assert result["calibrator_fit_allowed"] is False

    with pytest.raises(ValueError, match="exact complete"):
        build_independent_union(concepts, graph[:-1], local, top_k=1)


def test_sealed_capture_and_union_labels_remain_blocked_until_review() -> None:
    concepts = [
        {"concept_id": f"c{index}", "concept_name": f"concept-{index}"}
        for index in range(8)
    ]
    vocabulary = seal_candidate_vocabulary({
        "candidate_vocabulary_version": 2,
        "phase": "J1.1B",
        "status": "preflight_only",
        "created_at": "2026-07-16T12:00:00+09:00",
        "manifest_contract_sha256": "a" * 64,
        "reviewed_reference_answer_pack_sha256": "b" * 64,
        "reviewed_candidate_label_pack_sha256": "c" * 64,
        "graph_snapshot_sha256": "d" * 64,
        "selection_contract": {
            "source_vocabulary": "neo4j_full_concept_snapshot",
            "validity_filter_precedes_predictor_scoring": True,
            "semantic_labels_used_for_filtering": False,
            "graph_scores_required_for_full_question_vocabulary": True,
            "local_core_scores_required_for_full_question_vocabulary": True,
            "top_k": 8,
            "union_rule": "graph_top_k_union_local_core_top_k",
            "both_predictors_rescore_union": True,
        },
        "source_concept_count": 8,
        "eligible_concept_count": 8,
        "rejected_concept_count": 0,
        "rejection_counts": {},
        "eligible_concepts": concepts,
        "rejected_concepts": [],
        "question_scopes": [{
            "order": 0,
            "question_id": "q0",
            "question_sha256": "e" * 64,
            "cue_exclusions": [],
            "eligible_concept_count": 8,
        }],
        "database_writes": False,
        "learning_enabled": False,
        "gpu_inference_executed": False,
        "probabilities_computed": False,
        "calibrator_fit_allowed": False,
        "heldout_gate": False,
        "performance_claim_gate": False,
        "production_promotion_gate": False,
    })
    validate_candidate_vocabulary(vocabulary)
    graph = [{**item, "raw_score": float(8 - index)} for index, item in enumerate(concepts)]
    local = [{**item, "raw_score": float(index + 1)} for index, item in enumerate(concepts)]
    union = build_independent_union(concepts, graph, local)
    capture = seal_independent_score_capture({
        "independent_score_capture_version": 1,
        "phase": "J1.1B",
        "status": "raw_scores_sealed",
        "captured_at": "2026-07-16T12:01:00+09:00",
        "candidate_vocabulary_sha256": vocabulary["candidate_vocabulary_sha256"],
        "question_count": 1,
        "questions": [{
            "order": 0,
            "question_id": "q0",
            "question_sha256": "e" * 64,
            "eligible_concept_count": 8,
            "graph_raw_scores": graph,
            "local_core_raw_scores": local,
            "independent_union": union,
        }],
        "database_writes": False,
        "learning_enabled": False,
        "gpu_inference_executed": True,
        "probabilities_computed": False,
        "calibrator_fit_allowed": False,
        "heldout_gate": False,
        "performance_claim_gate": False,
        "production_promotion_gate": False,
    })
    validate_independent_score_capture(vocabulary, capture)
    answers = {
        "reference_answer_pack_sha256": "b" * 64,
        "review_status": "user_reviewed",
        "answers": [{"order": 0, "answer_sha256": "f" * 64}],
    }
    labels = seal_union_label_pack({
        "union_label_pack_version": 1,
        "phase": "J1.1B",
        "independent_score_capture_sha256": capture[
            "independent_score_capture_sha256"
        ],
        "reviewed_reference_answer_pack_sha256": "b" * 64,
        "semantic_label_source": (
            "external_teacher_drafted_against_user_reviewed_reference_answers"
        ),
        "review_status": "awaiting_user_review",
        "reviewer_role": "assistant_draft",
        "reviewed_at": None,
        "label_count": 8,
        "entries": [{
            "order": 0,
            "question_id": "q0",
            "question_sha256": "e" * 64,
            "answer_sha256": "f" * 64,
            "labels": [{
                **item,
                "decision": (
                    "proposed_approved" if index == 0 else "proposed_rejected"
                ),
                "rationale": "semantic decision",
            } for index, item in enumerate(concepts)],
        }],
        "user_direct_answers": False,
        "database_writes": False,
        "learning_enabled": False,
        "probabilities_computed": False,
        "calibrator_fit_allowed": False,
        "heldout_gate": False,
        "performance_claim_gate": False,
        "production_promotion_gate": False,
    })
    validate_union_label_pack(capture, answers, labels)
    report = build_union_label_readiness_report(capture, answers, labels)

    assert report["explicit_user_review_gate"] is False
    assert report["calibrator_fit_gate"] is False
    assert report["dual_predictor_positive_coverage_gate"] is True

    incomplete = copy.deepcopy(labels)
    incomplete["entries"][0]["labels"].pop()
    incomplete["label_count"] -= 1
    incomplete = seal_union_label_pack(incomplete)
    with pytest.raises(ValueError, match="complete independent union"):
        validate_union_label_pack(capture, answers, incomplete)
