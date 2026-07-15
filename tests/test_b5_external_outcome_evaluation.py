from scripts.research import b5_external_outcome_evaluation as b5


def _concept(concept_id: str, name: str, created_at: str = "2026-07-14T08:00:00+00:00") -> dict[str, str]:
    return {"id": concept_id, "name": name, "created_at": created_at}


def _record(experience_id: str, task: str) -> dict:
    return {
        "experience_id": experience_id,
        "task": task,
        "created_at": "2026-07-14T09:00:00+00:00",
        "cue_concepts": [],
        "predicted_concepts": [],
    }


def test_build_sequence_pairs_never_crosses_sequence_boundaries() -> None:
    records = [_record(item, item) for item in ("a1", "a2", "a3", "b1", "b2")]
    pairs, missing = b5.build_sequence_pairs(
        records,
        sequences=(("a", ("a1", "a2", "a3")), ("b", ("b1", "b2"))),
    )

    assert missing == []
    assert [
        (item["source"]["experience_id"], item["target"]["experience_id"])
        for item in pairs
    ] == [("a1", "a2"), ("a2", "a3"), ("b1", "b2")]


def test_external_input_terms_filter_generic_speech_acts() -> None:
    terms = b5.extract_external_input_terms(
        "컴퓨터와 로봇의 관계는 어떻게 연결되는지 왜 특별한지 설명해줘",
    )

    assert "컴퓨터" in terms
    assert "로봇" in terms
    assert "관계" in terms
    assert "왜" not in terms
    assert "어떻" not in terms
    assert "설명해줘" not in terms


def test_next_input_split_excludes_repeated_cue_only() -> None:
    split = b5.split_next_input_terms(
        "컴퓨터와 로봇의 관계를 설명해줘",
        [_concept("computer", "컴퓨터")],
    )

    assert "컴퓨터" in split["repeated_cue_terms"]
    assert "로봇" in split["external_terms"]
    assert "관계" in split["external_terms"]


def test_preexisting_outcome_split_blocks_future_concepts() -> None:
    concepts = [
        _concept("robot", "로봇", "2026-07-14T08:00:00+00:00"),
        _concept("future", "미래", "2026-07-14T10:00:00+00:00"),
    ]
    vocabulary = b5._available_vocabulary(
        concepts,
        "2026-07-14T09:00:00+00:00",
        [],
    )
    split = b5.split_preexisting_outcomes(["로봇", "미래"], vocabulary)

    assert split == {"preexisting": ["로봇"], "novel": ["미래"]}


def test_name_error_reuses_conservative_b4_matching() -> None:
    assert b5.compute_name_prediction_error(["신기한", "AI"], ["신기하", "ai"]) == 0.0
    assert b5.compute_name_prediction_error(["비비"], ["비빔밥"]) == 1.0
    assert b5.compute_name_prediction_error([], []) is None


def test_frequency_baseline_uses_only_strictly_prior_user_inputs() -> None:
    vocabulary = {
        b5.canonical_bucket("로봇"): [_concept("robot", "로봇")],
        b5.canonical_bucket("사과"): [_concept("apple", "사과")],
    }
    history = [
        {
            "task": "로봇을 알려줘",
            "created_at": "2026-07-14T08:00:00+00:00",
        },
        {
            "task": "사과를 알려줘",
            "created_at": "2026-07-14T10:00:00+00:00",
        },
    ]

    predicted = b5.frequency_baseline_predictions(
        history,
        "2026-07-14T09:00:00+00:00",
        vocabulary,
        limit=2,
    )

    assert predicted == ["로봇"]


def test_random_expected_error_matches_uniform_top_k() -> None:
    assert b5.expected_random_error(vocabulary_size=100, prediction_count=8) == 0.92
    assert b5.expected_random_error(vocabulary_size=4, prediction_count=8) == 0.0
    assert b5.expected_random_error(vocabulary_size=0, prediction_count=8) is None


def test_summary_refuses_promotion_when_external_data_is_too_sparse(monkeypatch) -> None:
    monkeypatch.setattr(
        b5,
        "evaluate_pair",
        lambda pair, concepts, history: {
            "graph_error": 0.0,
            "frequency_error": 1.0,
            "random_expected_error": 0.9,
            "preexisting_outcome_terms": [pair["outcome"]],
            "novel_outcome_terms": [],
            "invalid_cue_names": [],
        },
    )
    pairs = [{"outcome": "로봇"}, {"outcome": "로봇"}]
    report = b5.summarize_evaluation(pairs, [], [])

    assert report["baseline_gate"] is True
    assert report["data_gate"] is False
    assert report["promotion_gate"] is False
    assert report["verdict"] == "insufficient_external_outcome_data"


def test_summary_passes_only_with_diverse_data_and_both_baselines_beaten(monkeypatch) -> None:
    monkeypatch.setattr(
        b5,
        "evaluate_pair",
        lambda pair, concepts, history: {
            "graph_error": 0.0,
            "frequency_error": 0.5,
            "random_expected_error": 0.9,
            "preexisting_outcome_terms": [pair["outcome"]],
            "novel_outcome_terms": [],
            "invalid_cue_names": [],
        },
    )
    pairs = [
        {"outcome": outcome}
        for outcome in ("로봇", "사과", "서울", "기억", "로봇", "사과")
    ]
    report = b5.summarize_evaluation(pairs, [], [])

    assert report["data_gate"] is True
    assert report["baseline_gate"] is True
    assert report["robustness_gate"] is True
    assert report["promotion_gate"] is True
    assert report["verdict"] == "offline_gate_passed"


def test_summary_rejects_one_pair_advantage_as_not_robust(monkeypatch) -> None:
    def fake_evaluate(pair, _concepts, _history):
        better = pair["index"] == 0
        return {
            "graph_error": 0.0 if better else 1.0,
            "frequency_error": 1.0,
            "random_expected_error": 0.99,
            "preexisting_outcome_terms": [pair["outcome"]],
            "novel_outcome_terms": [],
            "invalid_cue_names": [],
        }

    monkeypatch.setattr(b5, "evaluate_pair", fake_evaluate)
    pairs = [
        {"index": index, "outcome": outcome}
        for index, outcome in enumerate(("로봇", "사과", "서울", "기억", "학습", "감정"))
    ]
    report = b5.summarize_evaluation(pairs, [], [])

    assert report["data_gate"] is True
    assert report["baseline_gate"] is True
    assert report["graph_better_than_frequency_pair_count"] == 1
    assert report["graph_hit_count"] == 1
    assert report["robustness_gate"] is False
    assert report["promotion_gate"] is False
    assert report["verdict"] == "positive_but_not_robust"


def test_sensor_route_requires_both_predictions_and_next_frame_links() -> None:
    no_predictions = b5.summarize_evaluation(
        [],
        [],
        [],
        sensor_coverage={
            "vision_experience_count": 45,
            "vision_with_observed_concepts": 40,
            "vision_with_prediction_snapshot": 0,
            "next_frame_link_count": 10,
        },
    )
    complete = b5.summarize_evaluation(
        [],
        [],
        [],
        sensor_coverage={
            "vision_with_prediction_snapshot": 3,
            "next_frame_link_count": 2,
        },
    )

    assert no_predictions["sensor_route_scorable"] is False
    assert complete["sensor_route_scorable"] is True


def test_all_b5_queries_are_read_only() -> None:
    combined = (
        f" {b5.SEQUENCE_QUERY} {b5.HISTORY_QUERY} {b5.CONCEPT_QUERY} "
        f" {b5.SENSOR_COVERAGE_QUERY} "
    ).upper()
    for mutation in (" CREATE ", " MERGE ", " SET ", " DELETE ", " REMOVE "):
        assert mutation not in combined
