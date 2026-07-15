import json

import pytest

from scripts.research import b5_1_external_outcome_pilot as pilot


def _concept(concept_id: str, name: str) -> dict[str, str]:
    return {
        "id": concept_id,
        "name": name,
        "created_at": "2026-07-14T00:00:00+00:00",
    }


def test_preregistered_contract_is_fixed_and_has_six_pairs() -> None:
    assert len(pilot.PILOT_MESSAGES) == 7
    assert len(set(pilot.PILOT_MESSAGES)) == 7
    assert len(pilot.contract_sha256()) == 64
    assert pilot.contract_sha256() == pilot.contract_sha256(pilot.PILOT_MESSAGES)
    assert all("어떻게" not in message for message in pilot.PILOT_MESSAGES)


def test_load_b5_4_manifest_checks_fixed_hash_and_budget(tmp_path) -> None:
    messages = [f"메시지 {index}" for index in range(7)]
    manifest = {
        "pilot_name": "b5_4_train_test",
        "split": "train",
        "contract_sha256": pilot.contract_sha256(messages),
        "max_live_turns": 7,
        "messages": messages,
    }
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")

    loaded = pilot.load_pilot_manifest(path)

    assert loaded["messages"] == tuple(messages)
    assert loaded["contract_sha256"] == pilot.contract_sha256(messages)


def test_load_b5_4_manifest_rejects_message_change_without_hash_change(tmp_path) -> None:
    messages = [f"메시지 {index}" for index in range(7)]
    manifest = {
        "pilot_name": "b5_4_train_test",
        "split": "train",
        "contract_sha256": pilot.contract_sha256(messages),
        "max_live_turns": 7,
        "messages": [*messages[:-1], "변경된 메시지"],
    }
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(ValueError, match="does not match"):
        pilot.load_pilot_manifest(path)


def test_contract_gate_passes_with_six_diverse_preexisting_outcomes(monkeypatch) -> None:
    snapshots = [
        {
            "message": message,
            "snapshot": {
                "cue_concepts": [_concept(f"cue-{index}", f"cue{index}")],
                "predicted_concepts": [_concept(f"pred-{index}", f"pred{index}")],
            },
        }
        for index, message in enumerate(pilot.PILOT_MESSAGES[:-1], start=1)
    ]
    outcomes = iter(("로봇", "카메라", "기억", "학습", "경험", "감정"))
    monkeypatch.setattr(
        pilot.b5,
        "split_next_input_terms",
        lambda _message, _cues: {
            "external_terms": [next(outcomes)],
            "all_terms": [],
            "repeated_cue_terms": [],
        },
    )
    concepts = [
        _concept(name, name)
        for name in ("로봇", "카메라", "기억", "학습", "경험", "감정")
    ]

    report = pilot.validate_preregistered_contract(
        snapshots,
        concepts,
        captured_at="2026-07-15T00:00:00+00:00",
    )

    assert report["pair_count"] == 6
    assert report["scorable_pair_count"] == 6
    assert report["unique_preexisting_external_outcome_count"] == 6
    assert report["contract_gate"] is True


def test_contract_gate_fails_when_predictions_are_missing(monkeypatch) -> None:
    snapshots = [
        {
            "message": message,
            "snapshot": {
                "cue_concepts": [_concept(f"cue-{index}", f"cue{index}")],
                "predicted_concepts": [],
            },
        }
        for index, message in enumerate(pilot.PILOT_MESSAGES[:-1], start=1)
    ]
    monkeypatch.setattr(
        pilot.b5,
        "split_next_input_terms",
        lambda _message, _cues: {
            "external_terms": ["로봇"],
            "all_terms": [],
            "repeated_cue_terms": [],
        },
    )

    report = pilot.validate_preregistered_contract(
        snapshots,
        [_concept("robot", "로봇")],
        captured_at="2026-07-15T00:00:00+00:00",
    )

    assert report["contract_gate"] is False


def test_deferred_turn_audit_rejects_same_turn_scores() -> None:
    valid_record = {
        "experience_id": "exp-1",
        "task": "컴퓨터는 무엇을 하는 도구야?",
        "created_at": "2026-07-15T00:00:00+00:00",
        "scoring_mode": "external_deferred",
        "prediction_error": None,
        "learning_progress": None,
        "cues": [_concept("computer", "컴퓨터")],
        "predictions": [_concept("robot", "로봇")],
    }
    invalid_record = {
        **valid_record,
        "prediction_error": 1.0,
        "learning_progress": 0.1,
    }

    assert pilot.validate_deferred_turn(
        valid_record,
        valid_record["task"],
    )["valid"] is True
    audit = pilot.validate_deferred_turn(invalid_record, invalid_record["task"])
    assert audit["valid"] is False
    assert "same_turn_prediction_error_present" in audit["errors"]
    assert "same_turn_learning_progress_present" in audit["errors"]


def test_deferred_turn_audit_checks_sequence_contract() -> None:
    record = {
        "experience_id": "exp-1",
        "task": "컴퓨터와 로봇",
        "created_at": "2026-07-15T00:00:00+00:00",
        "scoring_mode": "external_deferred",
        "prediction_error": None,
        "learning_progress": None,
        "cues": [_concept("computer", "컴퓨터")],
        "predictions": [_concept("robot", "로봇")],
        "external_sequence_id": pilot.PILOT_NAME,
        "external_turn_index": 0,
        "external_sequence_split": pilot.PILOT_SPLIT,
        "external_sequence_contract_sha256": pilot.contract_sha256(),
    }
    expected = {
        "external_sequence_id": pilot.PILOT_NAME,
        "external_turn_index": 0,
        "external_sequence_split": pilot.PILOT_SPLIT,
        "external_sequence_contract_sha256": pilot.contract_sha256(),
    }

    assert pilot.validate_deferred_turn(record, record["task"], expected)["valid"] is True
    invalid = pilot.validate_deferred_turn(
        {**record, "external_turn_index": 1},
        record["task"],
        expected,
    )
    assert invalid["valid"] is False
    assert "external_turn_index_mismatch" in invalid["errors"]


def test_turn_audit_query_is_read_only() -> None:
    upper = f" {pilot.TURN_AUDIT_QUERY} {pilot.CUE_STATE_QUERY} ".upper()
    for mutation in (" CREATE ", " MERGE ", " SET ", " DELETE ", " REMOVE "):
        assert mutation not in upper
