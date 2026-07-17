import copy

import pytest

from neural.baby.answer_source import (
    build_answer_source_readiness_report,
    build_user_reviewed_packs,
    route_answer_source,
    seal_answer_source_amendment,
    seal_candidate_label_pack,
    seal_reference_answer_pack,
    validate_answer_source_amendment,
    validate_candidate_label_pack,
    validate_reference_answer_pack,
)
from neural.baby.pending_question_semantics import text_sha256


def _fixtures() -> tuple[dict, dict, dict, dict, dict]:
    manifest = {
        "manifest_id": "manifest",
        "contract_sha256": "a" * 64,
        "questions": [{
            "order": 0,
            "question_id": "q0",
            "question": "기억과 학습은 어떻게 연결돼?",
            "question_sha256": "b" * 64,
        }],
    }
    raw_pack = {
        "raw_score_pack_sha256": "c" * 64,
        "sealed_at": "2026-07-16T10:00:00+09:00",
        "questions": [{
            "order": 0,
            "question_id": "q0",
            "question_sha256": "b" * 64,
            "concept_universe": [
                {"concept_id": "info", "concept_name": "정보"},
                {"concept_id": "noise", "concept_name": "말해줘"},
            ],
        }],
    }
    amendment = seal_answer_source_amendment({
        "answer_source_amendment_version": 1,
        "phase": "J1.1A",
        "status": "active",
        "created_at": "2026-07-16T10:01:00+09:00",
        "manifest_id": "manifest",
        "contract_sha256": "a" * 64,
        "raw_score_pack_sha256": "c" * 64,
        "superseded_next_step": "collect_new_user_answers_then_review_candidate_labels_and_fit_train_only_calibrators",
        "replacement_data_role": "teacher_labeled_calibration_bootstrap",
        "replacement_next_step": "draft_external_teacher_answers_and_candidate_labels_then_stop_for_batch_user_review",
        "original_artifacts_mutated": False,
        "user_direct_answers_required": False,
        "batch_user_review_required": True,
        "calibrator_fit_allowed": False,
        "database_writes": False,
        "learning_enabled": False,
        "heldout_gate": False,
        "performance_claim_gate": False,
        "production_promotion_gate": False,
    })
    answers = seal_reference_answer_pack({
        "reference_answer_pack_version": 1,
        "phase": "J1.1A",
        "created_at": "2026-07-16T10:02:00+09:00",
        "manifest_id": "manifest",
        "contract_sha256": "a" * 64,
        "raw_score_pack_sha256": "c" * 64,
        "answer_source_amendment_sha256": amendment["amendment_sha256"],
        "teacher_identity": "codex_assistant",
        "teacher_identity_scope": "conversation_assistant_not_model_snapshot",
        "answer_provenance": "external_teacher_drafted",
        "evidence_type": "general_conceptual_synthesis",
        "review_status": "awaiting_batch_user_review",
        "user_direct_answers": False,
        "calibrator_fit_allowed": False,
        "answer_count": 1,
        "answers": [{
            "order": 0,
            "question_id": "q0",
            "question": "기억과 학습은 어떻게 연결돼?",
            "question_sha256": "b" * 64,
            "question_type": "public_knowledge",
            "answer_source": "external_teacher",
            "answer": "기억은 학습을 돕고 학습은 기억을 바꾼다.",
        }],
    })
    labels = seal_candidate_label_pack({
        "candidate_label_pack_version": 1,
        "phase": "J1.1A",
        "created_at": "2026-07-16T10:02:00+09:00",
        "manifest_id": "manifest",
        "contract_sha256": "a" * 64,
        "raw_score_pack_sha256": "c" * 64,
        "reference_answer_pack_sha256": answers["reference_answer_pack_sha256"],
        "review_status": "awaiting_user_review",
        "reviewer_role": "assistant_draft",
        "reviewed_at": None,
        "calibrator_fit_allowed": False,
        "database_writes": False,
        "learning_enabled": False,
        "entries": [{
            "order": 0,
            "question_id": "q0",
            "question_sha256": "b" * 64,
            "answer_sha256": text_sha256("기억은 학습을 돕고 학습은 기억을 바꾼다."),
            "labels": [
                {"concept_id": "info", "concept_name": "정보", "decision": "proposed_approved", "rationale": "핵심 대상"},
                {"concept_id": "noise", "concept_name": "말해줘", "decision": "proposed_rejected", "rationale": "speech-act"},
            ],
        }],
    })
    return manifest, raw_pack, amendment, answers, labels


def test_answer_source_router_keeps_user_questions_exceptional() -> None:
    assert route_answer_source("public_knowledge") == "external_teacher"
    assert route_answer_source("personal_context") == "user"
    assert route_answer_source("sensor_observation") == "sensor"
    assert route_answer_source("tool_outcome") == "tool"
    assert route_answer_source("unresolved") == "abstain"
    with pytest.raises(ValueError, match="unsupported"):
        route_answer_source("always_ask_user")


def test_valid_draft_is_reviewable_but_cannot_fit_calibrator() -> None:
    manifest, raw, amendment, answers, labels = _fixtures()

    validate_answer_source_amendment(manifest, raw, amendment)
    validate_reference_answer_pack(manifest, raw, amendment, answers)
    validate_candidate_label_pack(manifest, raw, answers, labels)
    report = build_answer_source_readiness_report(
        manifest, raw, amendment, answers, labels
    )

    assert report["answer_source_contract_gate"] is True
    assert report["candidate_positive_coverage_gate"] is True
    assert report["provisional_calibrator_fit_gate"] is False
    assert report["question_selection_calibrator_gate"] is False
    assert report["database_writes"] is False
    assert report["learning_enabled"] is False
    assert "explicit_user_batch_review_missing" in report["block_reasons"]
    assert "candidate_universe_is_graph_selected_only" in report["block_reasons"]


def test_contract_rejects_tampering_and_missing_candidate_decision() -> None:
    manifest, raw, amendment, answers, labels = _fixtures()
    bad_amendment = copy.deepcopy(amendment)
    bad_amendment["raw_score_pack_sha256"] = "d" * 64
    bad_amendment = seal_answer_source_amendment(bad_amendment)
    with pytest.raises(ValueError, match="raw_score_pack_sha256"):
        validate_answer_source_amendment(manifest, raw, bad_amendment)

    bad_answer = copy.deepcopy(answers)
    bad_answer["answers"][0]["answer"] = "바뀐 답"
    with pytest.raises(ValueError, match="answer_sha256"):
        validate_reference_answer_pack(manifest, raw, amendment, bad_answer)

    incomplete = copy.deepcopy(labels)
    incomplete["entries"][0]["labels"].pop()
    incomplete = seal_candidate_label_pack(incomplete)
    with pytest.raises(ValueError, match="full concept universe"):
        validate_candidate_label_pack(manifest, raw, answers, incomplete)


def test_user_review_requires_final_decisions_but_does_not_bypass_fairness_gate() -> None:
    manifest, raw, amendment, answers, labels = _fixtures()
    reviewed_answers, reviewed = build_user_reviewed_packs(
        answers,
        labels,
        reviewed_at="2026-07-16T11:00:00+09:00",
    )

    validate_candidate_label_pack(
        manifest, raw, reviewed_answers, reviewed, require_user_review=True
    )
    report = build_answer_source_readiness_report(
        manifest, raw, amendment, reviewed_answers, reviewed
    )

    assert reviewed_answers["review_status"] == "user_reviewed"
    assert reviewed_answers["reviewer_role"] == "user"
    assert reviewed["calibrator_fit_allowed"] is False
    assert answers["review_status"] == "awaiting_batch_user_review"
    assert labels["review_status"] == "awaiting_user_review"
    assert report["provisional_calibrator_fit_gate"] is True
    assert report["fair_candidate_universe_gate"] is False
    assert report["question_selection_calibrator_gate"] is False
    assert report["status"] == "blocked_pending_candidate_universe_v2"

    undecided = copy.deepcopy(reviewed)
    undecided["entries"][0]["labels"][0]["decision"] = "proposed_approved"
    undecided = seal_candidate_label_pack(undecided)
    with pytest.raises(ValueError, match="decision"):
        validate_candidate_label_pack(manifest, raw, reviewed_answers, undecided)


def test_reviewed_labels_cannot_bind_to_unreviewed_answers() -> None:
    manifest, raw, _, answers, labels = _fixtures()
    _, reviewed_labels = build_user_reviewed_packs(
        answers,
        labels,
        reviewed_at="2026-07-16T11:00:00+09:00",
    )
    rebound = copy.deepcopy(reviewed_labels)
    rebound["reference_answer_pack_sha256"] = answers[
        "reference_answer_pack_sha256"
    ]
    rebound = seal_candidate_label_pack(rebound)

    with pytest.raises(ValueError, match="user-reviewed reference answers"):
        validate_candidate_label_pack(manifest, raw, answers, rebound)
