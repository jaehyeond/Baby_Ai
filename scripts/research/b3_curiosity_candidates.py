"""Select Phase 3 B3 cue candidates from Neo4j without mutating the graph.

The default cohort contains known concepts with no prior curiosity observations
and a bounded graph degree.  Existing B2 identity cues are reported separately
as regression controls, because their EMA state is already contaminated by live
validation turns.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
from typing import Any, Iterable

from dotenv import load_dotenv
from neo4j import AsyncGraphDatabase


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REGRESSION_NAMES = ("비비", "형", "관계")

CANDIDATE_QUERY = """
MATCH (c:Concept)-[rel:RELATES_TO]-(neighbor:Concept)
WHERE c.name IS NOT NULL AND trim(toString(c.name)) <> ''
WITH c, neighbor,
     max(coalesce(rel.hebb_strength, rel.strength, 0.0)) AS edge_score
ORDER BY edge_score DESC
WITH c,
     collect({id: neighbor.id, name: neighbor.name, score: edge_score}) AS neighbors
WITH c, size(neighbors) AS degree, neighbors[..5] AS top_neighbors
WHERE degree >= $min_degree
  AND degree <= $max_degree
  AND ($include_observed OR coalesce(c.curiosity_observations, 0) = 0)
RETURN c.id AS id,
       c.name AS name,
       c.category AS category,
       coalesce(c.strength, 0.0) AS strength,
       degree,
       coalesce(c.curiosity_observations, 0) AS observations,
       c.curiosity_error_ema AS error_ema,
       c.learning_progress AS learning_progress,
       top_neighbors
ORDER BY degree DESC, strength DESC, toLower(toString(name))
LIMIT $limit
"""

REGRESSION_QUERY = """
MATCH (c:Concept)
WHERE toLower(trim(toString(c.name))) IN $names
OPTIONAL MATCH (c)-[:RELATES_TO]-(neighbor:Concept)
RETURN c.id AS id,
       c.name AS name,
       c.category AS category,
       coalesce(c.strength, 0.0) AS strength,
       count(DISTINCT neighbor) AS degree,
       coalesce(c.curiosity_observations, 0) AS observations,
       c.curiosity_error_ema AS error_ema,
       c.learning_progress AS learning_progress
ORDER BY toLower(toString(name))
"""


def _serialize_record(record: Any, *, include_neighbors: bool) -> dict[str, Any]:
    item = {
        "id": record["id"],
        "name": record["name"],
        "category": record["category"],
        "strength": float(record["strength"] or 0.0),
        "degree": int(record["degree"] or 0),
        "observations": int(record["observations"] or 0),
        "error_ema": (
            None if record["error_ema"] is None else float(record["error_ema"])
        ),
        "learning_progress": (
            None
            if record["learning_progress"] is None
            else float(record["learning_progress"])
        ),
    }
    if include_neighbors:
        item["top_neighbors"] = [
            {
                "id": neighbor.get("id"),
                "name": neighbor.get("name"),
                "score": float(neighbor.get("score") or 0.0),
            }
            for neighbor in (record["top_neighbors"] or [])
        ]
    return item


async def fetch_candidate_report(
    driver: Any,
    *,
    database: str,
    limit: int,
    min_degree: int,
    max_degree: int,
    include_observed: bool,
    regression_names: Iterable[str],
) -> dict[str, Any]:
    """Run the two read-only candidate queries and return JSON-safe data."""

    names = list(dict.fromkeys(
        name.strip().casefold() for name in regression_names if name.strip()
    ))
    async with driver.session(database=database) as session:
        candidate_result = await session.run(
            CANDIDATE_QUERY,
            limit=limit,
            min_degree=min_degree,
            max_degree=max_degree,
            include_observed=include_observed,
        )
        candidate_records = await candidate_result.fetch(limit)

        regression_result = await session.run(REGRESSION_QUERY, names=names)
        regression_records = await regression_result.fetch(max(1, len(names)))

    return {
        "filters": {
            "limit": limit,
            "min_degree": min_degree,
            "max_degree": max_degree,
            "include_observed": include_observed,
        },
        "fresh_candidates": [
            _serialize_record(record, include_neighbors=True)
            for record in candidate_records
        ],
        "regression_controls": [
            _serialize_record(record, include_neighbors=False)
            for record in regression_records
        ],
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read-only Neo4j cue selection for Phase 3 B3",
    )
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--min-degree", type=int, default=2)
    parser.add_argument("--max-degree", type=int, default=20)
    parser.add_argument(
        "--include-observed",
        action="store_true",
        help="Include concepts that already have curiosity observations",
    )
    parser.add_argument(
        "--regression-name",
        action="append",
        dest="regression_names",
        help="Regression cue name; may be repeated",
    )
    args = parser.parse_args()
    if args.limit < 1:
        parser.error("--limit must be at least 1")
    if args.min_degree < 0 or args.max_degree < args.min_degree:
        parser.error("degree bounds must satisfy 0 <= min <= max")
    return args


async def _run(args: argparse.Namespace) -> dict[str, Any]:
    load_dotenv(PROJECT_ROOT / ".env")
    required = {
        "NEO4J_URI": os.getenv("NEO4J_URI"),
        "NEO4J_USERNAME": os.getenv("NEO4J_USERNAME"),
        "NEO4J_PASSWORD": os.getenv("NEO4J_PASSWORD"),
        "NEO4J_DATABASE": os.getenv("NEO4J_DATABASE"),
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise RuntimeError(f"missing environment keys: {', '.join(missing)}")

    driver = AsyncGraphDatabase.driver(
        required["NEO4J_URI"],
        auth=(required["NEO4J_USERNAME"], required["NEO4J_PASSWORD"]),
    )
    try:
        await driver.verify_connectivity()
        return await fetch_candidate_report(
            driver,
            database=required["NEO4J_DATABASE"],
            limit=args.limit,
            min_degree=args.min_degree,
            max_degree=args.max_degree,
            include_observed=args.include_observed,
            regression_names=args.regression_names or DEFAULT_REGRESSION_NAMES,
        )
    finally:
        await driver.close()


def main() -> None:
    args = _parse_args()
    report = asyncio.run(_run(args))
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
