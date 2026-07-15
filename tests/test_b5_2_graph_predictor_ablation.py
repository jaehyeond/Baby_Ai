from scripts.research import b5_2_graph_predictor_ablation as b52


def _concept(concept_id: str, name: str) -> dict[str, str]:
    return {"id": concept_id, "name": name, "created_at": "2026-07-01T00:00:00+00:00"}


def _history(
    experience_id: str,
    created_at: str,
    *concepts: dict[str, str],
) -> dict:
    return {
        "experience_id": experience_id,
        "created_at": created_at,
        "concepts": list(concepts),
    }


def test_history_filter_is_strictly_pre_source() -> None:
    history = [
        _history("past", "2026-07-14T00:00:00+00:00"),
        _history("same", "2026-07-15T00:00:00+00:00"),
        _history("future", "2026-07-16T00:00:00+00:00"),
    ]

    prior = b52._history_before(history, "2026-07-15T00:00:00+00:00")

    assert [item["experience_id"] for item in prior] == ["past"]


def test_cosine_penalizes_global_hub_without_using_target() -> None:
    cue = _concept("cue", "날씨")
    hub = _concept("hub", "문장")
    specific = _concept("specific", "도시")
    filler = _concept("filler", "기타")
    history = [
        _history("cue-specific", "2026-07-01T00:00:00+00:00", cue, specific),
        _history("cue-hub", "2026-07-02T00:00:00+00:00", cue, hub),
        *[
            _history(
                f"hub-{index}",
                f"2026-07-{index + 2:02d}T00:00:00+00:00",
                hub,
                filler,
            )
            for index in range(1, 8)
        ],
    ]
    source = {
        "created_at": "2026-07-15T00:00:00+00:00",
        "cue_concepts": [cue],
    }

    ranked = b52.rank_historical_associations(
        source,
        history,
        variant="historical_cosine",
        limit=2,
    )

    assert ranked["predicted_names"][0] == "도시"
    assert set(ranked["predicted_names"]) == {"도시", "문장"}


def test_multi_cue_variant_prioritizes_joint_support() -> None:
    cue_a = _concept("cue-a", "도시")
    cue_b = _concept("cue-b", "사람")
    joint = _concept("joint", "이름")
    single = _concept("single", "건물")
    history = [
        _history("a-joint", "2026-07-01T00:00:00+00:00", cue_a, joint),
        _history("b-joint", "2026-07-02T00:00:00+00:00", cue_b, joint),
        _history("a-single-1", "2026-07-03T00:00:00+00:00", cue_a, single),
        _history("a-single-2", "2026-07-04T00:00:00+00:00", cue_a, single),
        _history("a-single-3", "2026-07-05T00:00:00+00:00", cue_a, single),
    ]
    source = {
        "created_at": "2026-07-15T00:00:00+00:00",
        "cue_concepts": [cue_a, cue_b],
    }

    ranked = b52.rank_historical_associations(
        source,
        history,
        variant="historical_multi_cue_cosine",
        limit=2,
    )

    assert ranked["predicted_names"][0] == "이름"
    assert ranked["candidates"][0]["cue_support_count"] == 2


def test_candidate_ranker_filters_cue_and_future_records() -> None:
    cue = _concept("cue", "비비")
    past = _concept("past", "개발자")
    future = _concept("future", "프로그램")
    source = {
        "created_at": "2026-07-10T00:00:00+00:00",
        "cue_concepts": [cue],
    }
    history = [
        _history("past", "2026-07-01T00:00:00+00:00", cue, past),
        _history("future", "2026-07-11T00:00:00+00:00", cue, future),
    ]

    ranked = b52.rank_historical_associations(
        source,
        history,
        variant="historical_cooccurrence",
        limit=8,
    )

    assert ranked["predicted_names"] == ["개발자"]
    assert "비비" not in ranked["predicted_names"]
    assert "프로그램" not in ranked["predicted_names"]


def test_variant_summary_never_allows_direct_production_promotion() -> None:
    pairs = [
        {
            "error": 0.0,
            "frequency_error": 1.0,
            "random_expected_error": 0.99,
            "actual_names": [name],
        }
        for name in ("도시", "사람", "이름", "비비", "개발자", "프로그램")
    ]

    report = b52.summarize_variant("candidate", pairs)

    assert report["exploratory_gate"] is True
    assert report["production_promotion_gate"] is False
    assert report["production_block_reason"] == "same_pairs_used_for_candidate_selection"


def test_b5_2_queries_are_read_only() -> None:
    upper = f" {b52.ASSOCIATION_HISTORY_QUERY} {b52.TRANSITION_COVERAGE_QUERY} ".upper()
    for mutation in (" CREATE ", " MERGE ", " SET ", " DELETE ", " REMOVE "):
        assert mutation not in upper
