from __future__ import annotations

import asyncio

import pytest

from neural.baby.live_curiosity import (
    compute_integration_priority,
    compute_prediction_error,
    select_curiosity_target,
    should_open_curiosity_gate,
    update_learning_progress,
)


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


def test_conversation_endpoint_wires_prediction_before_handler(monkeypatch) -> None:
    from neural.baby import api_server, conversation_handler

    events: list[str] = []
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
            assert cue_terms == ["비비", "형"]
            return snapshot

        async def record_curiosity_outcome(self, received_snapshot, experience_id):
            events.append(f"record:{experience_id}")
            assert received_snapshot == snapshot
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
                message="비비와 형",
                context={"speaker_id": "guest"},
            )
        )
    )

    assert response.experience_id == "exp-1"
    assert events == ["prepare:비비와 형", "handle:비비와 형", "record:exp-1"]
