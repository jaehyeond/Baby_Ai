import copy

import pytest

from scripts.research import b5_7_pending_question_train_pilot as b57


def _candidate(index: int, *, eligible: bool = True) -> dict:
    return {
        "curiosity_log_id": f"curiosity-{index}",
        "curiosity_source": "concept_gap",
        "query_type": "concept_exploration",
        "question": f"주제{index}를 설명해줘",
        "cue_count": 1,
        "prediction_count": 8,
        "eligible": eligible,
    }


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("서울", "서울을 설명해줘"),
        ("컴퓨터", "컴퓨터를 설명해줘"),
        ("비비와 형의 관계를 더 알아보자", "비비와 형의 관계를 설명해줘"),
    ],
)
def test_question_template_is_deterministic(query: str, expected: str) -> None:
    assert b57.question_from_curiosity_query(query) == expected


def test_manifest_selects_six_unique_train_actions_without_predictions() -> None:
    manifest = b57.build_manifest([_candidate(index) for index in range(8)])

    assert manifest["split"] == "train"
    assert manifest["question_count"] == 6
    assert len(manifest["questions"]) == 6
    assert b57.validate_manifest(manifest) == manifest
    assert all("predicted_concepts" not in item for item in manifest["questions"])
    assert all("predicted_concept_ids" not in item for item in manifest["questions"])


def test_manifest_rejects_insufficient_candidates_and_tampering() -> None:
    with pytest.raises(ValueError, match="need at least 6"):
        b57.build_manifest([_candidate(index) for index in range(5)])

    manifest = b57.build_manifest([_candidate(index) for index in range(6)])
    tampered = copy.deepcopy(manifest)
    tampered["questions"][0]["question"] = "바뀐 질문"
    with pytest.raises(ValueError, match="contract_sha256"):
        b57.validate_manifest(tampered)


def test_create_payload_is_train_only_and_double_opt_in() -> None:
    manifest = b57.build_manifest([_candidate(index) for index in range(6)])
    payload = b57.build_create_payload(
        manifest["questions"][0],
        manifest["contract_sha256"],
    )

    assert payload == {
        "question": "주제0를 설명해줘",
        "source": "b5_7_curiosity_train",
        "curiosity_log_id": "curiosity-0",
        "question_outcome_evaluation": True,
        "question_outcome_split": "train",
        "question_outcome_contract_sha256": manifest["contract_sha256"],
    }


def test_discovery_and_audit_queries_are_read_only() -> None:
    query = (
        f" {b57.CANDIDATE_QUERY} {b57.MANIFEST_QUESTION_AUDIT_QUERY} "
        f" {b57.ANSWER_PREFLIGHT_QUERY} {b57.POST_ANSWER_EVALUATION_QUERY} "
        f" {b57.CURIOSITY_STATE_QUERY} "
    ).upper()
    for mutation in (" CREATE ", " MERGE ", " SET ", " DELETE ", " REMOVE "):
        assert mutation not in query


def _manifest_and_answers() -> tuple[dict, dict]:
    manifest = b57.build_manifest([_candidate(index) for index in range(6)])
    answers = {
        "answer_pack_version": 1,
        "pilot_name": b57.PILOT_NAME,
        "contract_sha256": manifest["contract_sha256"],
        "answer_role": "user_final",
        "answer_provenance": "user_reviewed_adopted",
        "approved_at": "2026-07-16T09:30:11+09:00",
        "answers": [
            {
                "order": index,
                "curiosity_log_id": manifest["questions"][index]["curiosity_log_id"],
                "question_id": f"question-{index}",
                "answer_confidence": 1.0,
                "answer": f"최종 답변 {index}",
            }
            for index in range(6)
        ],
    }
    return manifest, answers


def test_answer_pack_is_bound_to_sealed_contract_and_user_adoption() -> None:
    manifest, answers = _manifest_and_answers()

    assert b57.validate_answer_pack(manifest, answers) == answers
    assert b57.build_answer_payload(answers["answers"][0]) == {
        "answer": "최종 답변 0",
        "answer_confidence": 1.0,
    }

    tampered = copy.deepcopy(answers)
    tampered["answers"][0]["curiosity_log_id"] = "wrong-action"
    with pytest.raises(ValueError, match="curiosity_log_id mismatch"):
        b57.validate_answer_pack(manifest, tampered)


def test_completed_train_answers_pass_structure_but_not_unreviewed_content_gate() -> None:
    manifest, _answers = _manifest_and_answers()
    records = [
        {
            "curiosity_log_id": entry["curiosity_log_id"],
            "question_id": f"question-{entry['order']}",
            "status": "answered",
            "has_answer": True,
            "prediction_captured_at": "2026-07-16T00:00:00+00:00",
            "asked_at": "2026-07-16T00:00:01+00:00",
            "answered_at": "2026-07-16T00:01:00+00:00",
            "cue_ids": [f"cue-{entry['order']}"],
            "predicted_ids": [f"outcome-{entry['order']}"],
            "outcome_ids": [f"outcome-{entry['order']}"],
            "scoring_mode": "external_recorded",
            "split": "train",
            "policy_action_key": f"action-{entry['order']}",
        }
        for entry in manifest["questions"]
    ]

    result = b57.evaluate_completed_answers(
        manifest,
        records,
        answer_provenance="user_reviewed_adopted",
        learning_state_unchanged=True,
    )

    assert result["structural_contract_gate"] is True
    assert result["outcome_content_validity_gate"] is False
    assert result["target_validity_gate"] is False
    assert result["target_validity_reason"] == "reviewed_outcome_labels_not_supplied"
    assert result["unique_outcome_count"] == 6
    assert result["total_prediction_hit_count"] == 6
    assert result["exploratory_train_overlap_signal"] is False
    assert result["evaluation_readiness_gate"] is False
    assert result["production_promotion_gate"] is False


def test_completed_train_answers_require_separate_reviewed_outcome_labels() -> None:
    manifest, _answers = _manifest_and_answers()
    records = [
        {
            "curiosity_log_id": entry["curiosity_log_id"],
            "question_id": f"question-{entry['order']}",
            "status": "answered",
            "has_answer": True,
            "prediction_captured_at": "2026-07-16T00:00:00+00:00",
            "asked_at": "2026-07-16T00:00:01+00:00",
            "answered_at": "2026-07-16T00:01:00+00:00",
            "cue_ids": [f"cue-{entry['order']}"],
            "predicted_ids": [f"outcome-{entry['order']}"],
            "outcome_ids": [f"outcome-{entry['order']}"],
            "scoring_mode": "external_recorded",
            "split": "train",
            "policy_action_key": f"action-{entry['order']}",
        }
        for entry in manifest["questions"]
    ]
    reviewed = {
        entry["order"]: [f"outcome-{entry['order']}"]
        for entry in manifest["questions"]
    }

    result = b57.evaluate_completed_answers(
        manifest,
        records,
        answer_provenance="user_reviewed_adopted",
        learning_state_unchanged=True,
        reviewed_outcome_ids_by_order=reviewed,
    )

    assert result["structural_contract_gate"] is True
    assert result["outcome_content_validity_gate"] is True
    assert result["target_validity_gate"] is True
    assert result["exploratory_train_overlap_signal"] is True

    invalid = b57.evaluate_completed_answers(
        manifest,
        records,
        answer_provenance="user_reviewed_adopted",
        learning_state_unchanged=True,
        reviewed_outcome_ids_by_order={0: ["not-an-outcome"]},
    )
    assert invalid["outcome_content_validity_gate"] is False
    assert invalid["target_validity_reason"] == "reviewed_outcome_labels_invalid"
