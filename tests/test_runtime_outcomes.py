import asyncio
import json

import dotenv
import pytest

_load_dotenv = dotenv.load_dotenv
dotenv.load_dotenv = lambda *_args, **_kwargs: False
try:
    from neural.baby import api_server
finally:
    dotenv.load_dotenv = _load_dotenv

from neural.baby.runtime_outcomes import outcome_state


class FakeRequest:
    def __init__(self, body):
        self.body = body

    async def json(self):
        return self.body


class FakeStreamRequest:
    def __init__(self, disconnect_states):
        self.disconnect_states = list(disconnect_states)

    async def is_disconnected(self):
        if self.disconnect_states:
            return self.disconnect_states.pop(0)
        return True


class FakePubSub:
    def __init__(self, messages=None, subscribe_error=None, unsubscribe_error=None):
        self.messages = list(messages or [])
        self.subscribe_error = subscribe_error
        self.unsubscribe_error = unsubscribe_error
        self.subscribed_channels = ()
        self.get_message_calls = []
        self.unsubscribe_calls = 0
        self.close_calls = 0

    async def subscribe(self, *channels):
        self.subscribed_channels = channels
        if self.subscribe_error:
            raise self.subscribe_error

    async def get_message(self, **kwargs):
        self.get_message_calls.append(kwargs)
        if not self.messages:
            return None
        item = self.messages.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    async def unsubscribe(self):
        self.unsubscribe_calls += 1
        if self.unsubscribe_error:
            raise self.unsubscribe_error

    async def aclose(self):
        self.close_calls += 1


class FakeStreamRedis:
    def __init__(self, pubsubs):
        self.pubsubs = list(pubsubs)

    def pubsub(self):
        return self.pubsubs.pop(0)


def fail_if_called():
    raise AssertionError("database boundary must not be used")


@pytest.mark.parametrize("action", ["explore", "explore_batch"])
def test_curiosity_exploration_does_not_mark_fabricated_learning(
    monkeypatch, action
) -> None:
    monkeypatch.setattr(api_server, "get_driver", fail_if_called)
    result = asyncio.run(api_server.post_curiosity(FakeRequest({"action": action})))

    assert result["success"] is False
    assert result["status"] == "awaiting_evidence"
    assert result["explored"] == []
    assert result["execution"]["status"] == "not_executed"
    assert result["evaluation"] == {
        "status": "not_evaluated",
        "verified": False,
        "correct": None,
        "reward": None,
    }
    assert result["persisted"] is False


@pytest.mark.parametrize(
    ("body", "shape_key"),
    [
        ({"action": "imagine", "topic": "x"}, "session"),
        ({"action": "predict", "scenario": "x"}, "prediction"),
        ({"action": "simulate", "goal": "x"}, "simulation"),
        (
            {
                "action": "verify",
                "prediction_id": "prediction-1",
                "actual_outcome": "made up",
            },
            "prediction_id",
        ),
    ],
)
def test_imagination_actions_do_not_persist_fabricated_results(
    monkeypatch, body, shape_key
) -> None:
    monkeypatch.setattr(api_server, "get_brain_db", fail_if_called)
    result = asyncio.run(api_server.post_imagination(FakeRequest(body)))

    assert result["success"] is False
    assert result["status"] == "awaiting_evidence"
    assert shape_key in result
    assert result["execution"]["executed"] is False
    assert result["result"]["available"] is False
    assert result["evaluation"]["verified"] is False
    assert result["evaluation"]["correct"] is None
    assert result["evaluation"]["reward"] is None
    assert result["persisted"] is False


def test_imagination_stats_do_not_treat_legacy_flags_as_measured_accuracy(
    monkeypatch,
) -> None:
    class ReadOnlyPredictionDb:
        async def get_recent_predictions(self, *, limit):
            assert limit == 20
            return [
                {"id": "legacy-1", "was_correct": True},
                {"id": "legacy-2", "was_correct": True},
                {"id": "legacy-3", "was_correct": False},
                {"id": "unreviewed", "was_correct": None},
            ]

    monkeypatch.setattr(
        api_server,
        "get_brain_db",
        lambda: ReadOnlyPredictionDb(),
    )
    result = asyncio.run(api_server.post_imagination(FakeRequest({"action": "stats"})))

    assert result["success"] is True
    assert result["total_predictions"] == 4
    assert result["verified_prediction_count"] == 0
    assert result["correct_predictions"] is None
    assert result["accuracy"] is None
    assert result["measured_accuracy"] is None
    assert result["performance_claim_allowed"] is False
    assert result["legacy_unverified_diagnostics"] == {
        "status": "unverified",
        "source_field": "was_correct",
        "flagged_prediction_count": 3,
        "true_flag_count": 2,
        "false_flag_count": 1,
    }


def test_outcome_contract_distinguishes_no_result_incorrect_and_not_executed() -> None:
    not_executed = outcome_state(executed=False, result_available=False)
    no_result = outcome_state(executed=True, result_available=False)
    incorrect = outcome_state(
        executed=True,
        result_available=True,
        verified=True,
        correct=False,
        reward=0.0,
    )

    assert not_executed["execution"]["status"] == "not_executed"
    assert no_result["execution"]["status"] == "executed"
    assert no_result["result"]["status"] == "unavailable"
    assert no_result["evaluation"]["status"] == "not_evaluated"
    assert incorrect["evaluation"] == {
        "status": "evaluated",
        "verified": True,
        "correct": False,
        "reward": 0.0,
    }


def test_outcome_contract_rejects_claimed_verification_without_evidence() -> None:
    with pytest.raises(ValueError, match="require execution"):
        outcome_state(
            executed=False,
            result_available=False,
            verified=True,
            correct=True,
        )


def test_health_endpoint_uses_nonhealthy_http_status(monkeypatch) -> None:
    captured = {}

    async def fake_readiness(**_kwargs):
        captured.update(_kwargs)
        return {"ready": False, "status": "unhealthy"}

    monkeypatch.setattr(api_server, "build_readiness_report", fake_readiness)
    response = asyncio.run(api_server.health_check())
    assert response.status_code == 503
    assert json.loads(response.body)["status"] == "unhealthy"
    assert captured["neo4j_reconnect"] is api_server._reconnect_neo4j_for_readiness


def test_lifespan_does_not_run_schema_or_seed(monkeypatch) -> None:
    calls = []

    async def fake_init_driver():
        calls.append("init_driver")

    async def fake_close_driver():
        calls.append("close_driver")

    async def fake_close_redis():
        calls.append("close_redis")

    monkeypatch.setattr(api_server, "init_driver", fake_init_driver)
    monkeypatch.setattr(api_server, "init_redis", lambda: calls.append("init_redis"))
    monkeypatch.setattr(api_server, "close_driver", fake_close_driver)
    monkeypatch.setattr(api_server, "close_redis", fake_close_redis)
    monkeypatch.setattr(api_server, "get_brain_db", fail_if_called)

    async def exercise_lifespan():
        async with api_server.lifespan(api_server.app):
            assert api_server.app.state.startup_initialization == {
                "status": "not_requested",
                "mutated": False,
                "mode": "external_explicit_only",
            }

    asyncio.run(exercise_lifespan())
    assert calls == ["init_driver", "init_redis", "close_driver", "close_redis"]


def test_conversation_handler_unavailable_is_503_without_fake_experience(
    monkeypatch,
) -> None:
    def unavailable_handler():
        raise ImportError("secret module path")

    monkeypatch.setattr(api_server, "_load_conversation_handler", unavailable_handler)
    monkeypatch.setattr(api_server, "get_brain_db", fail_if_called)

    with pytest.raises(api_server.HTTPException) as exc_info:
        asyncio.run(api_server.conversation(
            api_server.ConversationRequest(message="hello")
        ))

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == {
        "success": False,
        "status": "unavailable",
        "component": "conversation_handler",
        "message": "Conversation service is unavailable",
    }
    assert "secret" not in repr(exc_info.value.detail)


def test_sse_idle_heartbeat_disconnect_and_cleanup(monkeypatch) -> None:
    pubsub = FakePubSub(
        unsubscribe_error=ConnectionError("redis://secret-password")
    )
    redis = FakeStreamRedis([pubsub])
    request = FakeStreamRequest([False, True])
    monkeypatch.setattr(api_server, "get_redis", lambda: redis)
    monkeypatch.setattr(api_server, "_SSE_POLL_TIMEOUT_SECONDS", 0.001)
    monkeypatch.setattr(api_server, "_SSE_HEARTBEAT_SECONDS", 0.0)

    async def exercise():
        response = await api_server.event_stream(request)
        iterator = response.body_iterator
        assert await iterator.__anext__() == ": connected\n\n"
        assert await iterator.__anext__() == ": ping\n\n"
        with pytest.raises(StopAsyncIteration):
            await iterator.__anext__()

    asyncio.run(exercise())
    assert pubsub.get_message_calls == [{
        "ignore_subscribe_messages": True,
        "timeout": 0.001,
    }]
    assert pubsub.unsubscribe_calls == 1
    assert pubsub.close_calls == 1


def test_sse_subscribe_failure_is_sanitized_503_and_closes(monkeypatch) -> None:
    pubsub = FakePubSub(
        subscribe_error=ConnectionError("redis://user:secret@private-host")
    )
    monkeypatch.setattr(
        api_server,
        "get_redis",
        lambda: FakeStreamRedis([pubsub]),
    )

    with pytest.raises(api_server.HTTPException) as exc_info:
        asyncio.run(api_server.event_stream(FakeStreamRequest([])))

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == {
        "success": False,
        "status": "unavailable",
        "component": "redis",
        "message": "Event stream is unavailable",
    }
    assert "secret" not in repr(exc_info.value.detail)
    assert pubsub.unsubscribe_calls == 1
    assert pubsub.close_calls == 1


def test_sse_poll_failure_cleans_and_next_connection_can_receive(monkeypatch) -> None:
    failed = FakePubSub([
        ConnectionError("rediss://user:secret@private-host")
    ])
    recovered = FakePubSub([{"type": "message", "data": "restored"}])
    redis = FakeStreamRedis([failed, recovered])
    monkeypatch.setattr(api_server, "get_redis", lambda: redis)
    monkeypatch.setattr(api_server, "_SSE_POLL_TIMEOUT_SECONDS", 0.001)

    async def exercise():
        first_response = await api_server.event_stream(FakeStreamRequest([False]))
        first = first_response.body_iterator
        assert await first.__anext__() == ": connected\n\n"
        unavailable = await first.__anext__()
        assert unavailable.startswith("event: unavailable\ndata: ")
        assert "secret" not in unavailable
        with pytest.raises(StopAsyncIteration):
            await first.__anext__()

        second_response = await api_server.event_stream(
            FakeStreamRequest([False, True])
        )
        second = second_response.body_iterator
        assert await second.__anext__() == ": connected\n\n"
        assert await second.__anext__() == "data: restored\n\n"
        with pytest.raises(StopAsyncIteration):
            await second.__anext__()

    asyncio.run(exercise())
    assert failed.unsubscribe_calls == failed.close_calls == 1
    assert recovered.unsubscribe_calls == recovered.close_calls == 1
