import copy

import pytest

from neural.baby.pending_question_semantics import (
    build_action_answer_relation_proposals,
    text_sha256,
    validate_semantic_label_pack,
)


HASH = "a" * 64


def _fixtures() -> tuple[dict, dict, dict, dict]:
    manifest = {
        "contract_sha256": HASH,
        "questions": [{"order": 0, "curiosity_log_id": "curiosity-0"}],
    }
    answers = {
        "contract_sha256": HASH,
        "answers": [{
            "order": 0,
            "curiosity_log_id": "curiosity-0",
            "question_id": "question-0",
            "answer": "컴퓨터는 정보를 처리합니다.",
        }],
    }
    artifact = {
        "contract_sha256": HASH,
        "questions": [{
            "order": 0,
            "outcome_ids": ["concept-info", "concept-noise"],
            "outcome_names": ["정보", "처리해"],
        }],
    }
    pack = {
        "semantic_label_pack_version": 1,
        "contract_sha256": HASH,
        "review_status": "draft_unreviewed",
        "reviewer_role": "assistant_draft",
        "reviewed_at": None,
        "entries": [{
            "order": 0,
            "curiosity_log_id": "curiosity-0",
            "question_id": "question-0",
            "answer_sha256": text_sha256("컴퓨터는 정보를 처리합니다."),
            "labels": [{
                "concept_id": "concept-info",
                "name": "정보",
                "decision": "proposed",
            }],
        }],
    }
    return manifest, answers, artifact, pack


def test_assistant_draft_is_valid_but_cannot_be_training_truth() -> None:
    manifest, answers, artifact, pack = _fixtures()

    validated = validate_semantic_label_pack(manifest, answers, artifact, pack)
    proposals = build_action_answer_relation_proposals(
        manifest, answers, artifact, pack
    )

    assert validated["review_status"] == "draft_unreviewed"
    assert proposals["semantic_target_validity_gate"] is False
    assert proposals["evaluation_target_ids_by_order"] == {"0": []}
    assert proposals["database_writes"] is False
    assert proposals["database_write_gate"] is False
    assert proposals["relation_proposals"][0]["write_eligible_after_schema_review"] is False
    with pytest.raises(ValueError, match="explicit user review"):
        validate_semantic_label_pack(
            manifest,
            answers,
            artifact,
            pack,
            require_user_review=True,
        )


def test_explicit_user_review_requires_decisions_and_timezone() -> None:
    manifest, answers, artifact, pack = _fixtures()
    reviewed = copy.deepcopy(pack)
    reviewed.update({
        "review_status": "user_reviewed",
        "reviewer_role": "user",
        "reviewed_at": "2026-07-16T15:00:00+09:00",
    })
    reviewed["entries"][0]["labels"][0]["decision"] = "approved"

    proposals = build_action_answer_relation_proposals(
        manifest, answers, artifact, reviewed
    )

    assert proposals["semantic_target_validity_gate"] is True
    assert proposals["evaluation_target_ids_by_order"] == {"0": ["concept-info"]}
    assert proposals["database_write_gate"] is False
    assert proposals["relation_proposals"][0]["write_eligible_after_schema_review"] is True

    undecided = copy.deepcopy(reviewed)
    undecided["entries"][0]["labels"][0]["decision"] = "proposed"
    with pytest.raises(ValueError, match="must decide"):
        validate_semantic_label_pack(manifest, answers, artifact, undecided)


def test_pack_rejects_answer_tampering_and_non_time_valid_concept() -> None:
    manifest, answers, artifact, pack = _fixtures()
    tampered_answer = copy.deepcopy(answers)
    tampered_answer["answers"][0]["answer"] = "바뀐 답변"
    with pytest.raises(ValueError, match="answer_sha256"):
        validate_semantic_label_pack(manifest, tampered_answer, artifact, pack)

    invalid_label = copy.deepcopy(pack)
    invalid_label["entries"][0]["labels"][0].update({
        "concept_id": "future-concept",
        "name": "미래",
    })
    with pytest.raises(ValueError, match="not a B5.8 time-valid outcome"):
        validate_semantic_label_pack(manifest, answers, artifact, invalid_label)
