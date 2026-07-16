from scripts.research import b5_5_target_validity_gate as b55


def _coverage(**overrides: int) -> dict:
    base = {
        "external_sequence_turn_count": 7,
        "external_sequence_link_count": 6,
        "external_turn_with_prediction_snapshot": 7,
        "pending_question_count": 18,
        "answered_question_count": 15,
        "pending_with_question": 18,
        "pending_with_answer": 15,
        "ordered_answer_count": 15,
        "answer_before_question_count": 0,
        "answered_missing_time_count": 0,
        "generated_from_curiosity_count": 0,
        "pending_with_prediction_snapshot": 0,
        "pending_prediction_before_question_count": 0,
        "vision_count": 45,
        "vision_with_head_pose": 0,
        "vision_with_prediction_snapshot": 0,
        "next_frame_count": 36,
        "next_frame_with_pose_delta": 0,
    }
    return {**base, **overrides}


def _b5_4(passed: bool = False) -> dict:
    return {"evaluation": {"any_exploratory_gate_passed": passed}}


def test_pending_question_answer_is_selected_but_not_retroactively_ready() -> None:
    report = b55.evaluate_target_candidates(_coverage(), _b5_4())
    candidate = report["candidates"][
        "action_conditioned_pending_question_answer"
    ]

    assert report["selected_target"] == (
        "action_conditioned_pending_question_answer"
    )
    assert report["target_selection_gate"] is True
    assert candidate["target_validity_gate"] is True
    assert candidate["evaluation_readiness_gate"] is False
    assert candidate["existing_answers_reusable_for_scoring"] is False
    assert report["production_promotion_gate"] is False


def test_unconditioned_next_user_topic_is_rejected_even_with_sequence_data() -> None:
    report = b55.evaluate_target_candidates(_coverage(), _b5_4(passed=True))
    candidate = report["candidates"]["unconditioned_next_user_topic"]

    assert candidate["criteria"]["recorded_action_identity"] is False
    assert candidate["criteria"]["outcome_conditioned_on_baby_action"] is False
    assert candidate["target_validity_gate"] is False
    assert candidate["evaluation_readiness_gate"] is False


def test_sensor_target_is_deferred_without_recorded_action_and_prediction() -> None:
    report = b55.evaluate_target_candidates(_coverage(), _b5_4())
    candidate = report["candidates"]["action_conditioned_next_sensor_outcome"]

    assert candidate["observed_pair_count"] == 36
    assert candidate["observed_action_count"] == 0
    assert candidate["target_validity_gate"] is False
    assert candidate["evaluation_readiness_gate"] is False


def test_pending_target_becomes_ready_only_with_pre_answer_policy_predictions() -> None:
    coverage = _coverage(
        generated_from_curiosity_count=6,
        pending_with_prediction_snapshot=6,
        pending_prediction_before_question_count=6,
    )

    report = b55.evaluate_target_candidates(coverage, _b5_4())
    candidate = report["candidates"][
        "action_conditioned_pending_question_answer"
    ]

    assert candidate["target_validity_gate"] is True
    assert candidate["evaluation_readiness_gate"] is True
    assert report["evaluation_readiness_gate"] is True


def test_legacy_time_reversal_rejects_current_target_but_keeps_schema_recommendation() -> None:
    coverage = _coverage(
        ordered_answer_count=1,
        answer_before_question_count=14,
    )

    report = b55.evaluate_target_candidates(coverage, _b5_4())
    candidate = report["candidates"][
        "action_conditioned_pending_question_answer"
    ]

    assert candidate["target_schema_gate"] is True
    assert candidate["target_validity_gate"] is False
    assert report["selected_target"] is None
    assert report["recommended_instrumentation_target"] == (
        "action_conditioned_pending_question_answer"
    )
    assert report["target_selection_gate"] is False


def test_b5_5_queries_are_read_only() -> None:
    upper = f" {b55.COVERAGE_QUERY} {b55.PENDING_SOURCE_QUERY} ".upper()
    for mutation in (" CREATE ", " MERGE ", " SET ", " DELETE ", " REMOVE "):
        assert mutation not in upper
