from __future__ import annotations

import asyncio

import pytest

from neural.baby.live_curiosity import (
    build_curiosity_cue_terms,
    compute_integration_priority,
    compute_prediction_error,
    select_curiosity_target,
    should_open_curiosity_gate,
    update_learning_progress,
)


def test_curiosity_cue_terms_restore_known_korean_surface_forms() -> None:
    assert build_curiosity_cue_terms(
        "비비와 형의 관계를 한 문장으로 말해줘.",
        extracted_terms=["형의", "관계", "문장", "말해줘"],
    ) == ["비비", "형", "관계", "문장", "말해줘"]


def test_curiosity_cue_terms_do_not_reintroduce_substring_matching() -> None:
    terms = build_curiosity_cue_terms(
        "비비빔밥과 형광등은 전혀 다른 단어야.",
        extracted_terms=["비비빔밥", "형광등", "전혀", "다른", "단어"],
    )
    assert "비비" not in terms
    assert "형" not in terms
    assert terms[:2] == ["비비빔밥", "형광등"]


def test_curiosity_cue_terms_filter_one_character_pronouns() -> None:
    terms = build_curiosity_cue_terms("나는 너와 형을 봤어.", extracted_terms=[])
    assert "나" not in terms
    assert "너" not in terms
    assert "형" in terms


def test_prediction_error_scores_non_cue_outcomes() -> None:
    error = compute_prediction_error(
        predicted_ids=["cue", "hit", "other"],
        actual_ids=["cue", "hit", "miss"],
        cue_ids=["cue"],
    )
    assert error == pytest.approx(0.5)


def test_prediction_error_skips_turn_without_non_cue_outcome() -> None:
    assert compute_prediction_error(["next"], ["cue"], ["cue"]) is None


def test_learning_progress_ignores_initial_and_worsening_error() -> None:
    initial = update_learning_progress(0.8, None, 0)
    assert initial.error_ema == pytest.approx(0.8)
    assert initial.learning_progress == 0.0
    assert initial.observations == 1

    worsening = update_learning_progress(1.0, initial.error_ema, initial.observations)
    assert worsening.error_ema == pytest.approx(0.88)
    assert worsening.learning_progress == 0.0


def test_learning_progress_reduction_opens_gate_only_after_repeated_evidence() -> None:
    update = update_learning_progress(0.2, 0.8, 2, alpha=0.4)
    assert update.error_ema == pytest.approx(0.56)
    assert update.learning_progress == pytest.approx(0.24)
    assert should_open_curiosity_gate(update.learning_progress, update.observations)
    assert not should_open_curiosity_gate(update.learning_progress, 2)


def test_integration_priority_uses_progress_not_raw_error() -> None:
    assert compute_integration_priority(0.45, 0.0) == pytest.approx(0.45)
    assert compute_integration_priority(0.45, 0.25) == pytest.approx(0.55)


def test_target_prefers_tractable_prediction_then_missed_outcome() -> None:
    assert select_curiosity_target(
        cue_ids=["cue"],
        predicted_ids=["predicted"],
        actual_ids=["cue", "missed", "predicted"],
    ) == "predicted"
    assert select_curiosity_target(
        cue_ids=["cue"],
        predicted_ids=["other"],
        actual_ids=["cue", "missed"],
    ) == "missed"


def test_prepare_prediction_keeps_all_selected_cues(monkeypatch) -> None:
    from neural.baby import neo4j_db

    calls: list[tuple[str, dict]] = []
    result_sets = [
        [
            {"cue_id": "bibi", "cue_name": "비비"},
            {"cue_id": "hyung", "cue_name": "형"},
        ],
        [
            {
                "candidate_id": "relation",
                "candidate_name": "관계",
                "score": 0.9,
            }
        ],
    ]

    class FakeResult:
        def __init__(self, records):
            self.records = records

        async def fetch(self, _limit):
            return self.records

    class FakeSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, _exc_type, _exc, _tb):
            return False

        async def run(self, query, **params):
            calls.append((query, params))
            return FakeResult(result_sets[len(calls) - 1])

    class FakeDriver:
        def session(self, database=None):
            assert database == neo4j_db._DB_NAME
            return FakeSession()

    monkeypatch.setattr(neo4j_db, "get_driver", lambda: FakeDriver())
    snapshot = asyncio.run(
        neo4j_db.BrainDatabase().prepare_curiosity_prediction(
            "비비와 형",
            cue_terms=["비비", "형"],
        )
    )

    assert [item["name"] for item in snapshot["cue_concepts"]] == ["비비", "형"]
    assert [item["name"] for item in snapshot["predicted_concepts"]] == ["관계"]
    assert calls[0][1]["cue_terms"] == ["비비", "형"]
    assert calls[1][1]["cue_ids"] == ["bibi", "hyung"]
    assert len(calls) == 2


def test_conversation_endpoint_wires_prediction_before_handler(monkeypatch) -> None:
    from neural.baby import api_server, conversation_handler

    events: list[str] = []
    received_cue_terms: list[list[str]] = []
    received_snapshots: list[dict | None] = []
    snapshot = {
        "cue_concepts": [{"id": "cue", "name": "비비"}],
        "predicted_concepts": [{"id": "target", "name": "형", "score": 0.8}],
    }

    class FakeDb:
        async def get_baby_state(self):
            return {"development_stage": 2}

        async def resolve_speaker_clearance(self, _speaker_id):
            return "public"

        async def prepare_curiosity_prediction(self, message, cue_terms=None):
            events.append(f"prepare:{message}")
            received_cue_terms.append(list(cue_terms or []))
            return snapshot

        async def record_curiosity_outcome(self, received_snapshot, experience_id):
            events.append(f"record:{experience_id}")
            received_snapshots.append(received_snapshot)
            return {
                "status": "recorded",
                "prediction_error": 0.5,
                "learning_progress": 0.1,
                "gated": True,
                "target_id": "target",
            }

    fake_db = FakeDb()
    monkeypatch.setattr(api_server, "get_brain_db", lambda: fake_db)

    async def fake_handle_conversation(message, context):
        events.append(f"handle:{message}")
        return {
            "output": "응답",
            "success": True,
            "emotional_state": {},
            "development_stage": 2,
            "experience_id": "exp-1",
        }

    monkeypatch.setattr(conversation_handler, "handle_conversation", fake_handle_conversation)

    response = asyncio.run(
        api_server.conversation(
            api_server.ConversationRequest(
                message="비비와 형의 관계",
                context={"speaker_id": "guest"},
            )
        )
    )

    assert response.experience_id == "exp-1"
    assert received_cue_terms == [["비비", "형", "관계"]]
    assert received_snapshots == [snapshot]
    assert events == [
        "prepare:비비와 형의 관계",
        "handle:비비와 형의 관계",
        "record:exp-1",
    ]
