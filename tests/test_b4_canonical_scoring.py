from scripts.research import b4_canonical_scoring


def _concept(concept_id: str, name: str) -> dict[str, str]:
    return {"id": concept_id, "name": name}


def test_conservative_name_match_accepts_observed_surface_variants() -> None:
    assert b4_canonical_scoring.conservative_name_match("관계", "관계를")
    assert b4_canonical_scoring.conservative_name_match("가구", "가구에")
    assert b4_canonical_scoring.conservative_name_match("신기한", "신기하")
    assert b4_canonical_scoring.conservative_name_match("AI", "ai")


def test_conservative_name_match_rejects_substrings_and_lexical_endings() -> None:
    for left, right in (
        ("비비", "비빔밥"),
        ("형", "형광등"),
        ("컴퓨터", "컴퓨터공학"),
        ("카메", "카메라"),
        ("오디", "오디오"),
        ("은하", "은한"),
        ("북하", "북한"),
    ):
        assert not b4_canonical_scoring.conservative_name_match(left, right)


def test_cue_surface_variant_is_stricter_than_general_name_matching() -> None:
    assert b4_canonical_scoring.is_cue_surface_variant("컴퓨터요", "컴퓨터")
    assert b4_canonical_scoring.is_cue_surface_variant("컴퓨터라", "컴퓨터")
    assert not b4_canonical_scoring.conservative_name_match("컴퓨터요", "컴퓨터")
    assert not b4_canonical_scoring.is_cue_surface_variant("카메라", "카메")


def test_canonical_error_excludes_cue_variants_and_recovers_hada_match() -> None:
    result = b4_canonical_scoring.compute_canonical_prediction_error(
        predicted_concepts=[
            _concept("computer-polite", "컴퓨터요"),
            _concept("interesting-attributive", "신기한"),
            _concept("ai", "AI"),
        ],
        actual_concepts=[
            _concept("computer-ending", "컴퓨터라"),
            _concept("interesting-stem", "신기하"),
            _concept("robot", "로봇"),
        ],
        cue_concepts=[_concept("computer", "컴퓨터")],
    )

    assert result["prediction_error"] == 0.5
    assert result["matches"] == [{
        "predicted_id": "interesting-attributive",
        "predicted_name": "신기한",
        "actual_id": "interesting-stem",
        "actual_name": "신기하",
    }]
    assert [item["name"] for item in result["excluded_predicted_cue_variants"]] == [
        "컴퓨터요",
    ]
    assert [item["name"] for item in result["excluded_actual_cue_variants"]] == [
        "컴퓨터라",
    ]


def test_replay_query_is_read_only() -> None:
    upper = b4_canonical_scoring.EXPERIENCE_QUERY.upper()
    for mutation in (" CREATE ", " MERGE ", " SET ", " DELETE ", " REMOVE "):
        assert mutation not in f" {upper} "


def test_concept_availability_uses_pre_turn_timestamp() -> None:
    experience_time = "2026-07-14T09:00:00+00:00"

    assert b4_canonical_scoring.concept_existed_before_turn(
        {"created_at": "2026-07-14T08:59:59+00:00"},
        experience_time,
    ) is True
    assert b4_canonical_scoring.concept_existed_before_turn(
        {"created_at": "2026-07-14T09:00:01+00:00"},
        experience_time,
    ) is False
    assert b4_canonical_scoring.concept_existed_before_turn(
        {"created_at": None},
        experience_time,
    ) is None


def test_replay_reports_exact_to_canonical_improvement() -> None:
    report = b4_canonical_scoring.summarize_replay([{
        "experience_id": "exp-1",
        "experience_created_at": "2026-07-14T09:00:00+00:00",
        "stored_exact_error": 1.0,
        "cue_concepts": [_concept("computer", "컴퓨터")],
        "predicted_concepts": [_concept("interesting-1", "신기한")],
        "actual_concepts": [
            {
                **_concept("computer-ending", "컴퓨터라"),
                "created_at": "2026-07-14T09:00:01+00:00",
            },
            {
                **_concept("interesting-2", "신기하"),
                "created_at": "2026-07-14T08:00:00+00:00",
            },
        ],
    }])

    assert report["exact_mean_error"] == 1.0
    assert report["canonical_mean_error"] == 0.0
    assert report["preexisting_canonical_mean_error"] == 0.0
    assert report["preexisting_actual_count"] == 1
    assert report["improved_experience_ids"] == ["exp-1"]
