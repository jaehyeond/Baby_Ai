from scripts.research import b5_8_measurement_validity_ranker as b58


def _path(cue_id: str, *, strength: float, relation_type: str = "", source: str = "", direction: str = "outbound") -> dict:
    return {
        "cue_id": cue_id,
        "path_length": 1,
        "edges": [{
            "strength": strength,
            "relation_type": relation_type,
            "source": source,
            "direction": direction,
        }],
    }


def test_source_aware_ranker_penalizes_reverse_semantic_hub() -> None:
    candidates = [
        {
            "id": "bibi",
            "name": "비비",
            "degree": 220,
            "paths": [_path(
                "computer",
                strength=0.94,
                relation_type="knows",
                source="semantic",
                direction="inbound",
            )],
        },
        {
            "id": "program",
            "name": "프로그램",
            "degree": 3,
            "paths": [_path(
                "computer",
                strength=0.14,
                relation_type="used_for",
                source="semantic",
            )],
        },
    ]

    ranked = b58.rank_source_aware_candidates(
        candidates,
        cue_names=["컴퓨터"],
        limit=8,
    )

    assert [item["id"] for item in ranked] == ["program", "bibi"]
    assert ranked[0]["score"] > ranked[1]["score"]


def test_source_aware_ranker_rewards_multi_cue_support_and_filters_noise() -> None:
    candidates = [
        {
            "id": "shared",
            "name": "관계",
            "degree": 6,
            "paths": [
                _path("story", strength=0.12, relation_type="contains", source="semantic"),
                _path("secret", strength=0.11, relation_type="reveals", source="semantic"),
            ],
        },
        {
            "id": "single",
            "name": "날짜",
            "degree": 5,
            "paths": [_path("story", strength=0.25, source="hebbian")],
        },
        {
            "id": "speech",
            "name": "말해줘",
            "degree": 1,
            "paths": [_path("story", strength=1.0, source="hebbian")],
        },
    ]

    ranked = b58.rank_source_aware_candidates(
        candidates,
        cue_names=["이야기", "비밀"],
        limit=8,
    )

    assert [item["id"] for item in ranked] == ["shared", "single"]
    assert ranked[0]["cue_support_count"] == 2


def test_ranker_is_deterministic_and_train_only_report_never_promotes() -> None:
    candidates = [
        {"id": "b", "name": "나무", "degree": 2, "paths": [_path("cue", strength=0.2)]},
        {"id": "a", "name": "가구", "degree": 2, "paths": [_path("cue", strength=0.2)]},
    ]

    first = b58.rank_source_aware_candidates(candidates, cue_names=["집"], limit=8)
    second = b58.rank_source_aware_candidates(list(reversed(candidates)), cue_names=["집"], limit=8)
    report = b58.summarize_train_diagnostic([{
        "question_id": "q1",
        "baseline_predicted_ids": ["missing"],
        "ranked_candidates": first,
        "outcome_ids": ["a"],
    }])

    assert [item["id"] for item in first] == ["a", "b"]
    assert first == second
    assert report["train_only"] is True
    assert report["production_promotion_gate"] is False
    assert report["production_block_reason"] == "post_hoc_same_six_train_questions"


def test_bounded_graph_queries_are_read_only() -> None:
    query = f" {b58.QUESTION_QUERY} {b58.CONCEPT_NAMES_QUERY} {b58.OUTCOME_RESOLUTION_QUERY} {b58.NEIGHBOR_QUERY} ".upper()

    for mutation in (" CREATE ", " MERGE ", " SET ", " DELETE ", " REMOVE "):
        assert mutation not in query
    assert "$PER_SOURCE_LIMIT" in query
