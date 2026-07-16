import asyncio

import pytest
from fastapi import HTTPException

from neural.baby import api_server, neo4j_db
from neural.baby.pending_question_outcome import (
    audit_pending_question_terms,
    build_pending_question_cue_terms,
    build_pending_question_terms,
    normalize_pending_question_prediction,
    parse_pending_question_action_contract,
    validate_pending_question_action_state,
    validate_pending_question_answer_state,
)


HASH_A = "a" * 64


class FakeResult:
    def __init__(self, records):
        self.records = list(records)
        self.index = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.index >= len(self.records):
            raise StopAsyncIteration
        record = self.records[self.index]
        self.index += 1
        return record

    async def single(self):
        return self.records[0] if self.records else None


class FakeSession:
    def __init__(self, tx):
        self.tx = tx

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    async def execute_write(self, operation):
        return await operation(self.tx)


class FakeDriver:
    def __init__(self, tx):
        self.tx = tx

    def session(self, *, database):
        assert database == neo4j_db._DB_NAME
        return FakeSession(self.tx)


def _metadata(**overrides):
    value = {
        "policy_action_id": "b5_6_action_001",
        "question_outcome_split": "train",
        "question_outcome_contract_sha256": HASH_A,
    }
    value.update(overrides)
    return value


def _snapshot(**overrides):
    value = {
        "cue_concepts": [{"id": "cue-1", "name": "서울"}],
        "predicted_concepts": [{"id": "pred-1", "name": "날씨"}],
        "input_terms": ["서울"],
        "captured_at": "2020-07-16T01:00:00+00:00",
    }
    value.update(overrides)
    return value


def _research_question(**overrides):
    value = {
        "id": "question-1",
        "status": "pending",
        "question_outcome_evaluation": True,
        "question_outcome_policy_action_key": "policy:b5_6_action_001",
        "question_outcome_split": "train",
        "question_outcome_contract_sha256": HASH_A,
        "prediction_captured_at": "2020-07-16T01:00:00+00:00",
        "curiosity_cue_ids": ["cue-1"],
        "predicted_concept_ids": ["pred-1"],
    }
    value.update(overrides)
    return value


def test_parse_action_contract_supports_explicit_or_curiosity_provenance() -> None:
    explicit = parse_pending_question_action_contract(_metadata(
        policy_action_id=" B5_6.Action-001 ",
        question_outcome_split=" TRAIN ",
        question_outcome_contract_sha256=HASH_A.upper(),
    ))
    curiosity = parse_pending_question_action_contract({
        "curiosity_log_id": "curiosity-1",
        "question_outcome_split": "heldout",
        "question_outcome_contract_sha256": HASH_A,
    })

    assert explicit["policy_action_key"] == "policy:b5_6.action-001"
    assert explicit["split"] == "train"
    assert curiosity["policy_action_key"] == "curiosity:curiosity-1"
    assert curiosity["policy_action_id"] is None


@pytest.mark.parametrize(
    "metadata",
    [
        {
            "question_outcome_split": "train",
            "question_outcome_contract_sha256": HASH_A,
        },
        _metadata(policy_action_id="x"),
        _metadata(question_outcome_split="validation"),
        _metadata(question_outcome_contract_sha256="abc"),
    ],
)
def test_parse_action_contract_rejects_incomplete_or_invalid_metadata(metadata) -> None:
    with pytest.raises(ValueError):
        parse_pending_question_action_contract(metadata)


def test_action_state_rejects_missing_source_duplicate_and_cross_split_hash() -> None:
    contract = parse_pending_question_action_contract(_metadata(
        curiosity_log_id="curiosity-1",
    ))

    assert validate_pending_question_action_state(
        contract, [], curiosity_log_exists=False
    )["reason"] == "curiosity_log_not_found"
    assert validate_pending_question_action_state(
        contract, [{"question_id": "q1"}]
    )["reason"] == "duplicate_policy_action"
    assert validate_pending_question_action_state(
        contract, [], conflicting_split_count=1
    )["reason"] == "contract_reused_across_splits"
    assert validate_pending_question_action_state(contract, []) == {
        "status": "valid",
        "reason": None,
    }


def test_prediction_snapshot_requires_cues_predictions_and_timezone() -> None:
    normalized = normalize_pending_question_prediction(_snapshot())

    assert normalized["cue_ids"] == ["cue-1"]
    assert normalized["predicted_ids"] == ["pred-1"]
    assert normalized["predicted_candidates"] == [{
        "id": "pred-1",
        "name": "날씨",
        "score": 0.0,
        "rank": 1,
    }]
    assert normalized["captured_at"].endswith("+00:00")
    with pytest.raises(ValueError):
        normalize_pending_question_prediction(_snapshot(predicted_concepts=[]))
    with pytest.raises(ValueError):
        normalize_pending_question_prediction(
            _snapshot(captured_at="2026-07-16T01:00:00")
        )


def test_answer_state_keeps_legacy_path_and_fails_closed_for_research() -> None:
    assert validate_pending_question_answer_state({"status": "pending"})["status"] == "legacy"
    assert validate_pending_question_answer_state(_research_question())["status"] == "ready"
    assert validate_pending_question_answer_state(
        _research_question(status="answered", answer="이미 답함")
    )["reason"] == "question_already_answered"
    assert validate_pending_question_answer_state(
        _research_question(predicted_concept_ids=[])
    )["reason"] == "incomplete_prediction_snapshot"


def test_pending_question_terms_are_handler_independent_and_filter_speech_acts() -> None:
    terms = build_pending_question_terms("서울의 날씨를 설명해줘")

    assert "서울" in terms
    assert "날씨" in terms
    assert "설명해줘" not in terms


def test_pending_question_cues_preserve_established_b2_normalization() -> None:
    terms = build_pending_question_cue_terms("비비와 형의 관계를 설명해줘")

    assert {"비비", "형", "관계"} <= set(terms)
    assert "설명해줘" not in terms


def test_pending_question_terms_preserve_numeric_facts_and_late_content() -> None:
    answer = (
        "1시간은 60분이고 3,600초입니다. 하루 24시간을 기준으로 하면 "
        "하루의 24분의 1에 해당합니다. 컴퓨터는 통신, 계산, 로봇 제어를 합니다."
    )

    terms = build_pending_question_terms(answer)
    audit = audit_pending_question_terms(answer, terms)

    assert {"1시간", "60분", "3600초", "24시간"} <= set(terms)
    assert "24분" not in terms
    assert {"계산", "로봇", "제어"} <= set(terms)
    assert audit["numeric_fact_coverage"] == 1.0
    assert audit["one_character_korean_terms"] == []
    assert audit["measurement_content_gate"] is True


def test_pending_question_terms_drop_known_predicate_fragments() -> None:
    terms = build_pending_question_terms(
        "서로 맺는 관계와 아직 모르는 비밀을 설명하는 특별한 장치입니다."
    )

    assert "관계" in terms
    assert "비밀" in terms
    assert "장치" in terms
    assert "서로" in terms
    assert not {"서", "맺", "모르", "모르는", "하", "하는"} & set(terms)


def test_legacy_create_endpoint_remains_unchanged(monkeypatch) -> None:
    events = []

    class FakeDb:
        async def insert_pending_question(self, **kwargs):
            events.append(("legacy_insert", kwargs))
            return {"id": "legacy-q", **kwargs}

    async def fake_publish(question):
        events.append(("publish", question["id"]))

    monkeypatch.setattr(api_server, "get_brain_db", lambda: FakeDb())
    monkeypatch.setattr(api_server, "publish_pending_question", fake_publish)
    result = asyncio.run(api_server.create_pending_question(
        api_server.PendingQuestionCreate(question="기존 질문")
    ))

    assert result["question"]["id"] == "legacy-q"
    assert [item[0] for item in events] == ["legacy_insert", "publish"]


def test_research_create_persists_before_publish(monkeypatch) -> None:
    events = []

    class FakeDb:
        async def validate_pending_question_action(self, contract):
            events.append(("validate", contract["policy_action_key"]))
            return {"status": "valid", "reason": None}

        async def prepare_curiosity_prediction(self, question, cue_terms=None):
            events.append(("predict", question, cue_terms))
            return _snapshot()

        async def insert_pending_question_action_outcome(self, **kwargs):
            events.append(("persist", kwargs["contract"]["policy_action_key"]))
            return {"status": "created", "question": {"id": "research-q"}}

    async def fake_publish(question):
        events.append(("publish", question["id"]))

    monkeypatch.setenv("CURIOSITY_QUESTION_OUTCOME_EVAL", "1")
    monkeypatch.setattr(api_server, "get_brain_db", lambda: FakeDb())
    monkeypatch.setattr(api_server, "publish_pending_question", fake_publish)
    request = api_server.PendingQuestionCreate(
        question="서울의 날씨를 알려줘",
        question_outcome_evaluation=True,
        **_metadata(),
    )
    result = asyncio.run(api_server.create_pending_question(request))

    assert result["question"]["id"] == "research-q"
    assert [item[0] for item in events] == [
        "validate", "predict", "persist", "publish"
    ]


def test_research_metadata_and_server_gate_fail_before_db_work(monkeypatch) -> None:
    class FailDb:
        def __getattr__(self, _name):
            raise AssertionError("DB work must not start")

    monkeypatch.setattr(api_server, "get_brain_db", lambda: FailDb())
    metadata_without_opt_in = api_server.PendingQuestionCreate(
        question="질문",
        **_metadata(),
    )
    with pytest.raises(HTTPException) as metadata_error:
        asyncio.run(api_server.create_pending_question(metadata_without_opt_in))
    assert metadata_error.value.status_code == 422

    monkeypatch.delenv("CURIOSITY_QUESTION_OUTCOME_EVAL", raising=False)
    disabled = api_server.PendingQuestionCreate(
        question="질문",
        question_outcome_evaluation=True,
        **_metadata(),
    )
    with pytest.raises(HTTPException) as disabled_error:
        asyncio.run(api_server.create_pending_question(disabled))
    assert disabled_error.value.status_code == 409

    non_boolean = api_server.PendingQuestionCreate(
        question="질문",
        question_outcome_evaluation="true",
        **_metadata(),
    )
    with pytest.raises(HTTPException) as type_error:
        asyncio.run(api_server.create_pending_question(non_boolean))
    assert type_error.value.status_code == 422


def test_legacy_answer_endpoint_remains_unchanged(monkeypatch) -> None:
    events = []

    class FakeDb:
        async def get_pending_question_action_outcome_state(self, question_id):
            events.append(("state", question_id))
            return {"status": "legacy"}

        async def submit_question_answer(self, **kwargs):
            events.append(("legacy_answer", kwargs))
            return {"id": kwargs["question_id"], "status": "answered"}

    async def fake_publish(question):
        events.append(("publish", question["id"]))

    monkeypatch.setattr(api_server, "get_brain_db", lambda: FakeDb())
    monkeypatch.setattr(api_server, "publish_pending_question", fake_publish)
    result = asyncio.run(api_server.answer_pending_question(
        "legacy-q",
        api_server.PendingQuestionAnswer(answer="기존 답변"),
    ))

    assert result["question"]["status"] == "answered"
    assert [item[0] for item in events] == ["state", "legacy_answer", "publish"]


def test_research_answer_records_only_external_outcome_path(monkeypatch) -> None:
    events = []

    class FakeDb:
        async def get_pending_question_action_outcome_state(self, question_id):
            events.append(("state", question_id))
            return {"status": "ready"}

        async def submit_pending_question_action_outcome(self, **kwargs):
            events.append(("outcome", kwargs))
            return {
                "status": "recorded",
                "question": {"id": kwargs["question_id"], "status": "answered"},
            }

        async def submit_question_answer(self, **_kwargs):
            raise AssertionError("legacy answer path must not run")

    async def fake_publish(question):
        events.append(("publish", question["id"]))

    monkeypatch.setenv("CURIOSITY_QUESTION_OUTCOME_EVAL", "1")
    monkeypatch.setattr(api_server, "get_brain_db", lambda: FakeDb())
    monkeypatch.setattr(api_server, "publish_pending_question", fake_publish)
    result = asyncio.run(api_server.answer_pending_question(
        "research-q",
        api_server.PendingQuestionAnswer(answer="맑은 날씨", answer_confidence=0.8),
    ))

    assert result["question"]["status"] == "answered"
    assert [item[0] for item in events] == ["state", "outcome", "publish"]
    assert "날씨" in events[1][1]["outcome_terms"]


def test_research_answer_server_gate_blocks_write(monkeypatch) -> None:
    class FakeDb:
        async def get_pending_question_action_outcome_state(self, _question_id):
            return {"status": "ready"}

        async def submit_pending_question_action_outcome(self, **_kwargs):
            raise AssertionError("research answer write must not run")

    monkeypatch.delenv("CURIOSITY_QUESTION_OUTCOME_EVAL", raising=False)
    monkeypatch.setattr(api_server, "get_brain_db", lambda: FakeDb())
    with pytest.raises(HTTPException) as disabled_error:
        asyncio.run(api_server.answer_pending_question(
            "research-q",
            api_server.PendingQuestionAnswer(answer="답변"),
        ))
    assert disabled_error.value.status_code == 409


def test_db_question_transaction_revalidates_then_persists_snapshot(monkeypatch) -> None:
    calls = []

    class FakeTx:
        async def run(self, query, **parameters):
            calls.append((query, parameters))
            if query == neo4j_db.PENDING_QUESTION_ACTION_STATE_QUERY:
                return FakeResult([])
            if query == neo4j_db.PENDING_QUESTION_ACTION_SPLIT_CONFLICT_QUERY:
                return FakeResult([{"conflicting_split_count": 0}])
            if query == neo4j_db.PENDING_QUESTION_ACTION_PERSIST_QUERY:
                return FakeResult([{"pq": {"id": "question-1", **parameters["props"]}}])
            raise AssertionError(f"unexpected query: {query}")

    monkeypatch.setattr(neo4j_db, "get_driver", lambda: FakeDriver(FakeTx()))
    contract = parse_pending_question_action_contract(_metadata())
    result = asyncio.run(
        neo4j_db.BrainDatabase().insert_pending_question_action_outcome(
            question="서울의 날씨를 알려줘",
            source="research",
            contract=contract,
            prediction_snapshot=_snapshot(),
        )
    )

    assert result["status"] == "created"
    assert [query for query, _ in calls] == [
        neo4j_db.PENDING_QUESTION_ACTION_STATE_QUERY,
        neo4j_db.PENDING_QUESTION_ACTION_SPLIT_CONFLICT_QUERY,
        neo4j_db.PENDING_QUESTION_ACTION_PERSIST_QUERY,
    ]
    props = calls[-1][1]["props"]
    assert props["question_outcome_scoring_mode"] == "external_deferred"
    assert props["predicted_concept_ids"] == ["pred-1"]
    assert props["prediction_snapshot_version"] == 2
    assert '"rank": 1' in props["predicted_concepts_json"]
    assert props["prediction_captured_at"] <= props["asked_at"]


def test_db_question_transaction_rejects_duplicate_without_persist(monkeypatch) -> None:
    calls = []

    class FakeTx:
        async def run(self, query, **_parameters):
            calls.append(query)
            if query == neo4j_db.PENDING_QUESTION_ACTION_STATE_QUERY:
                return FakeResult([{"question_id": "existing"}])
            if query == neo4j_db.PENDING_QUESTION_ACTION_SPLIT_CONFLICT_QUERY:
                return FakeResult([{"conflicting_split_count": 0}])
            raise AssertionError("persistence must not run")

    monkeypatch.setattr(neo4j_db, "get_driver", lambda: FakeDriver(FakeTx()))
    result = asyncio.run(
        neo4j_db.BrainDatabase().insert_pending_question_action_outcome(
            question="중복 질문",
            source="research",
            contract=parse_pending_question_action_contract(_metadata()),
            prediction_snapshot=_snapshot(),
        )
    )

    assert result == {"status": "rejected", "reason": "duplicate_policy_action"}
    assert neo4j_db.PENDING_QUESTION_ACTION_PERSIST_QUERY not in calls


def test_db_answer_transaction_records_outcome_without_scoring(monkeypatch) -> None:
    calls = []
    ready_question = _research_question()

    class FakeTx:
        async def run(self, query, **parameters):
            calls.append((query, parameters))
            if query == neo4j_db.PENDING_QUESTION_ANSWER_STATE_QUERY:
                return FakeResult([{"pq": ready_question}])
            if query == neo4j_db.PENDING_QUESTION_OUTCOME_CONCEPT_QUERY:
                return FakeResult([{"concept_id": "outcome-1", "concept_name": "날씨"}])
            if query == neo4j_db.PENDING_QUESTION_ANSWER_PERSIST_QUERY:
                return FakeResult([{
                    "pq": {
                        **ready_question,
                        "status": "answered",
                        "answer": parameters["answer"],
                    }
                }])
            raise AssertionError(f"unexpected query: {query}")

    monkeypatch.setattr(neo4j_db, "get_driver", lambda: FakeDriver(FakeTx()))
    result = asyncio.run(
        neo4j_db.BrainDatabase().submit_pending_question_action_outcome(
            question_id="question-1",
            answer="맑은 날씨",
            answer_confidence=0.8,
            outcome_terms=["날씨"],
        )
    )

    assert result["status"] == "recorded"
    assert result["prediction_scored"] is False
    assert [query for query, _ in calls] == [
        neo4j_db.PENDING_QUESTION_ANSWER_STATE_QUERY,
        neo4j_db.PENDING_QUESTION_OUTCOME_CONCEPT_QUERY,
        neo4j_db.PENDING_QUESTION_ANSWER_PERSIST_QUERY,
    ]
    persist_params = calls[-1][1]
    assert persist_params["outcome_concept_ids"] == ["outcome-1"]
    assert "prediction_error" not in persist_params
