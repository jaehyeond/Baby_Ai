from __future__ import annotations

import asyncio

from scripts.research import (
    b3_curiosity_candidates,
    b3_curiosity_live_pilot,
    b3_curiosity_snapshot,
)


def test_b3_candidate_queries_are_read_only() -> None:
    for query in (
        b3_curiosity_candidates.CANDIDATE_QUERY,
        b3_curiosity_candidates.REGRESSION_QUERY,
    ):
        upper = query.upper()
        for mutation in (" CREATE ", " MERGE ", " SET ", " DELETE ", " REMOVE "):
            assert mutation not in f" {upper} "


def test_fetch_candidate_report_separates_fresh_and_regression() -> None:
    calls: list[tuple[str, dict]] = []

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
            if query == b3_curiosity_candidates.CANDIDATE_QUERY:
                return FakeResult([{
                    "id": "cup",
                    "name": "컵",
                    "category": "object",
                    "strength": 0.7,
                    "degree": 4,
                    "observations": 0,
                    "error_ema": None,
                    "learning_progress": None,
                    "top_neighbors": [
                        {"id": "table", "name": "식탁", "score": 0.8},
                    ],
                }])
            return FakeResult([{
                "id": "bibi",
                "name": "비비",
                "category": "identity",
                "strength": 0.9,
                "degree": 12,
                "observations": 4,
                "error_ema": 0.5,
                "learning_progress": 0.1,
            }])

    class FakeDriver:
        def session(self, database=None):
            assert database == "neo4j"
            return FakeSession()

    report = asyncio.run(
        b3_curiosity_candidates.fetch_candidate_report(
            FakeDriver(),
            database="neo4j",
            limit=10,
            min_degree=2,
            max_degree=20,
            include_observed=False,
            regression_names=["비비", "비비"],
        )
    )

    assert report["fresh_candidates"][0]["name"] == "컵"
    assert report["fresh_candidates"][0]["top_neighbors"][0]["name"] == "식탁"
    assert report["regression_controls"][0]["observations"] == 4
    assert calls[0][1] == {
        "limit": 10,
        "min_degree": 2,
        "max_degree": 20,
        "include_observed": False,
    }
    assert calls[1][1] == {"names": ["비비"]}


def test_build_message_snapshot_mirrors_endpoint_cue_logic() -> None:
    received: list[tuple[str, list[str]]] = []

    class FakeDb:
        async def prepare_curiosity_prediction(self, message, cue_terms=None):
            received.append((message, list(cue_terms or [])))
            return {
                "cue_concepts": [{"id": "seoul", "name": "서울"}],
                "predicted_concepts": [],
            }

    report = asyncio.run(
        b3_curiosity_snapshot.build_message_snapshot(
            FakeDb(),
            "서울은 어떤 도시야?",
        )
    )

    assert report["cue_terms"][0] == "서울"
    assert received == [("서울은 어떤 도시야?", report["cue_terms"])]
    assert report["snapshot"]["cue_concepts"][0]["name"] == "서울"


def test_live_pilot_experience_query_is_read_only() -> None:
    upper = b3_curiosity_live_pilot.EXPERIENCE_QUERY.upper()
    for mutation in (" CREATE ", " MERGE ", " SET ", " DELETE ", " REMOVE "):
        assert mutation not in f" {upper} "
