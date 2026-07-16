from neural.baby import neo4j_db
from scripts.research import b5_6_pending_question_action_outcome as b56


def test_b5_6_offline_contract_passes_without_collection_or_scoring() -> None:
    report = b56.build_contract_report()

    assert report["status"] == "offline_contract_passed"
    assert report["passed_case_count"] == report["case_count"] == 16
    assert report["database_writes"] is False
    assert report["live_collection_started"] is False
    assert report["heldout_collection_started"] is False
    assert report["existing_answer_reuse"] is False
    assert report["prediction_scoring_started"] is False
    assert report["learning_state_updates"] is False
    assert report["instrumentation_contract_gate"] is True
    assert report["target_validity_gate"] is False
    assert report["production_promotion_gate"] is False


def test_b5_6_answer_persistence_does_not_update_learning_or_production_state() -> None:
    query = neo4j_db.PENDING_QUESTION_ANSWER_PERSIST_QUERY.casefold()

    for forbidden in (
        "prediction_error",
        "learning_progress",
        "integration_priority",
        "curiosity_error_ema",
        "curiositylog",
        "brainregion",
    ):
        assert forbidden not in query


def test_b5_6_preflight_queries_are_read_only() -> None:
    queries = " ".join((
        neo4j_db.PENDING_QUESTION_ACTION_STATE_QUERY,
        neo4j_db.PENDING_QUESTION_ACTION_SPLIT_CONFLICT_QUERY,
        neo4j_db.PENDING_QUESTION_CURIOSITY_SOURCE_QUERY,
        neo4j_db.PENDING_QUESTION_ANSWER_STATE_QUERY,
        neo4j_db.PENDING_QUESTION_OUTCOME_CONCEPT_QUERY,
    )).upper()

    for mutation in (" CREATE ", " MERGE ", " SET ", " DELETE ", " REMOVE "):
        assert mutation not in f" {queries} "
