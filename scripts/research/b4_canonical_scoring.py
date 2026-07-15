"""Offline B4 replay for conservative concept-name scoring.

The production learning-progress rule remains unchanged. This module replays
preserved B3 Experiences read-only and asks whether conservative Korean surface
normalization recovers genuine matches without broad substring matching.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from dotenv import load_dotenv
from neo4j import AsyncGraphDatabase

from neural.baby.live_curiosity import compute_prediction_error


PROJECT_ROOT = Path(__file__).resolve().parents[2]

B3_EXPERIENCE_IDS = (
    "6d426fe9-2d0f-4ed8-94eb-e6e30db48011",
    "3316f5f6-296c-4664-b2cc-cd705e430f02",
    "0246aef4-38e5-4c13-af1e-34ca79ee9bf7",
    "282a9570-4136-4d61-9d6f-301147a43d85",
    "a00f9758-fda3-4b56-8fca-2d9a83432236",
    "50e2e34f-f8e3-49e3-8cb5-a4d841f3e232",
    "291e1790-d5a9-49c1-aaa0-0996730c2a1c",
    "b8e61dce-dfbb-46e7-b7b6-63d1ff2f47e7",
    "d80c1329-45b6-4fb2-b7f9-d4da08a68a22",
    "ffd88f20-72c5-4973-9de6-7986cb3113c1",
    "01f4d589-5dd9-438b-86c7-0597067126f9",
    "ed7f3ef4-c1f4-486b-aff5-7d3c834f5d5d",
)

EXPERIENCE_QUERY = """
UNWIND $experience_ids AS requested_id
MATCH (e:Experience {id: requested_id})
OPTIONAL MATCH (cue:Concept)
WHERE cue.id IN coalesce(e.curiosity_cue_ids, [])
WITH requested_id, e,
     collect(DISTINCT {
       id: cue.id,
       name: cue.name,
       created_at: toString(cue.created_at)
     }) AS cue_concepts
OPTIONAL MATCH (predicted:Concept)
WHERE predicted.id IN coalesce(e.predicted_concept_ids, [])
WITH requested_id, e, cue_concepts,
     collect(DISTINCT {
       id: predicted.id,
       name: predicted.name,
       created_at: toString(predicted.created_at)
     }) AS predicted_concepts
OPTIONAL MATCH (actual:Concept)
WHERE actual.id IN coalesce(e.curiosity_actual_concept_ids, [])
RETURN requested_id AS experience_id,
       toString(e.created_at) AS experience_created_at,
       e.prediction_error AS stored_exact_error,
       cue_concepts,
       predicted_concepts,
       collect(DISTINCT {
         id: actual.id,
         name: actual.name,
         created_at: toString(actual.created_at)
       }) AS actual_concepts
ORDER BY experience_id
"""

_WHITESPACE_RE = re.compile(r"\s+")
_EDGE_PUNCTUATION_RE = re.compile(r"^[\W_]+|[\W_]+$", re.UNICODE)
_SAFE_KOREAN_PARTICLES = tuple(sorted((
    "에서", "에게", "한테", "처럼", "까지", "부터", "조차", "마저", "으로", "이랑",
    "은", "는", "이", "가", "을", "를", "의", "와", "과", "에", "로", "랑",
), key=len, reverse=True))
_CUE_ONLY_UTTERANCE_SUFFIXES = ("라니", "이라니", "요", "라")


def normalize_concept_name(name: Any) -> str:
    """Normalize Unicode, case, surrounding punctuation, and whitespace."""

    normalized = unicodedata.normalize("NFKC", str(name or "")).casefold().strip()
    normalized = _EDGE_PUNCTUATION_RE.sub("", normalized)
    return _WHITESPACE_RE.sub(" ", normalized)


def conservative_canonical_forms(name: Any) -> set[str]:
    """Return exact and narrowly justified Korean canonical forms."""

    normalized = normalize_concept_name(name)
    if not normalized:
        return set()

    forms = {normalized}
    for particle in _SAFE_KOREAN_PARTICLES:
        if not normalized.endswith(particle):
            continue
        stem = normalized[: -len(particle)]
        if len(stem) >= 2:
            forms.add(stem)
        break

    # Observed handler split: 신기한 (attributive) vs 신기하 (stem).
    # Require a two-syllable base so lexical two-syllable nouns such as 북한,
    # 은하, 무한 are not rewritten.
    if len(normalized) >= 3 and normalized[-1] in {"한", "하"}:
        forms.add(f"{normalized[:-1]}하다")

    return forms


def conservative_name_match(left: Any, right: Any) -> bool:
    """Match by exact conservative forms, never by substring containment."""

    left_forms = conservative_canonical_forms(left)
    right_forms = conservative_canonical_forms(right)
    return bool(left_forms and right_forms and left_forms & right_forms)


def is_cue_surface_variant(name: Any, cue_name: Any) -> bool:
    """Identify a scored name that is only a surface variant of a known cue."""

    if conservative_name_match(name, cue_name):
        return True

    normalized = normalize_concept_name(name)
    cue = normalize_concept_name(cue_name)
    if len(cue) < 3:
        return False
    for suffix in _CUE_ONLY_UTTERANCE_SUFFIXES:
        if normalized == f"{cue}{suffix}":
            return True
    return False


def _valid_concepts(items: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return [item for item in items if item and item.get("id") and item.get("name")]


def _parse_timestamp(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def concept_existed_before_turn(
    concept: dict[str, Any],
    experience_created_at: Any,
) -> bool | None:
    """Return True/False when timestamps prove availability, else None."""

    concept_time = _parse_timestamp(concept.get("created_at"))
    experience_time = _parse_timestamp(experience_created_at)
    if concept_time is None or experience_time is None:
        return None
    return concept_time <= experience_time


def compute_canonical_prediction_error(
    predicted_concepts: Iterable[dict[str, Any]],
    actual_concepts: Iterable[dict[str, Any]],
    cue_concepts: Iterable[dict[str, Any]] = (),
) -> dict[str, Any]:
    """Compute recall error after cue-variant removal and conservative matching."""

    cues = _valid_concepts(cue_concepts)
    predicted = _valid_concepts(predicted_concepts)
    actual = _valid_concepts(actual_concepts)

    def is_cue_variant(item: dict[str, Any]) -> bool:
        return any(
            item["id"] == cue["id"]
            or is_cue_surface_variant(item["name"], cue["name"])
            for cue in cues
        )

    scored_predicted = [item for item in predicted if not is_cue_variant(item)]
    scored_actual = [item for item in actual if not is_cue_variant(item)]
    excluded_predicted = [item for item in predicted if is_cue_variant(item)]
    excluded_actual = [item for item in actual if is_cue_variant(item)]

    if not scored_actual:
        error = None
        matches: list[dict[str, Any]] = []
    else:
        matches = []
        for actual_item in scored_actual:
            match = next((
                predicted_item
                for predicted_item in scored_predicted
                if predicted_item["id"] == actual_item["id"]
                or conservative_name_match(
                    predicted_item["name"], actual_item["name"]
                )
            ), None)
            if match:
                matches.append({
                    "predicted_id": match["id"],
                    "predicted_name": match["name"],
                    "actual_id": actual_item["id"],
                    "actual_name": actual_item["name"],
                })
        error = round(1.0 - len(matches) / len(scored_actual), 6)

    return {
        "prediction_error": error,
        "matches": matches,
        "scored_predicted": scored_predicted,
        "scored_actual": scored_actual,
        "excluded_predicted_cue_variants": excluded_predicted,
        "excluded_actual_cue_variants": excluded_actual,
    }


def replay_experience(record: dict[str, Any]) -> dict[str, Any]:
    cues = _valid_concepts(record.get("cue_concepts") or [])
    predicted = _valid_concepts(record.get("predicted_concepts") or [])
    actual = _valid_concepts(record.get("actual_concepts") or [])
    exact_error = compute_prediction_error(
        (item["id"] for item in predicted),
        (item["id"] for item in actual),
        (item["id"] for item in cues),
    )
    canonical = compute_canonical_prediction_error(predicted, actual, cues)
    availability = [
        (item, concept_existed_before_turn(
            item, record.get("experience_created_at")
        ))
        for item in canonical["scored_actual"]
    ]
    preexisting_actual = [item for item, existed in availability if existed is True]
    new_actual = [item for item, existed in availability if existed is False]
    unknown_actual = [item for item, existed in availability if existed is None]
    preexisting_canonical = compute_canonical_prediction_error(
        predicted,
        preexisting_actual,
        cues,
    )
    return {
        "experience_id": record["experience_id"],
        "experience_created_at": record.get("experience_created_at"),
        "stored_exact_error": record.get("stored_exact_error"),
        "recomputed_exact_error": exact_error,
        "canonical_error": canonical["prediction_error"],
        "preexisting_canonical_error": preexisting_canonical["prediction_error"],
        "matches": canonical["matches"],
        "preexisting_matches": preexisting_canonical["matches"],
        "excluded_predicted_cue_variants": canonical[
            "excluded_predicted_cue_variants"
        ],
        "excluded_actual_cue_variants": canonical[
            "excluded_actual_cue_variants"
        ],
        "scored_actual_count": len(canonical["scored_actual"]),
        "preexisting_actual_count": len(preexisting_actual),
        "new_actual_count": len(new_actual),
        "unknown_age_actual_count": len(unknown_actual),
    }


def summarize_replay(records: Iterable[dict[str, Any]]) -> dict[str, Any]:
    turns = [replay_experience(record) for record in records]
    exact_values = [
        float(item["recomputed_exact_error"])
        for item in turns
        if item["recomputed_exact_error"] is not None
    ]
    canonical_values = [
        float(item["canonical_error"])
        for item in turns
        if item["canonical_error"] is not None
    ]
    preexisting_values = [
        float(item["preexisting_canonical_error"])
        for item in turns
        if item["preexisting_canonical_error"] is not None
    ]
    improved = [
        item["experience_id"]
        for item in turns
        if item["recomputed_exact_error"] is not None
        and item["canonical_error"] is not None
        and item["canonical_error"] < item["recomputed_exact_error"]
    ]
    return {
        "database_writes": False,
        "turn_count": len(turns),
        "exact_mean_error": (
            round(sum(exact_values) / len(exact_values), 6) if exact_values else None
        ),
        "canonical_mean_error": (
            round(sum(canonical_values) / len(canonical_values), 6)
            if canonical_values else None
        ),
        "preexisting_canonical_mean_error": (
            round(sum(preexisting_values) / len(preexisting_values), 6)
            if preexisting_values else None
        ),
        "preexisting_scorable_turn_count": len(preexisting_values),
        "preexisting_actual_count": sum(
            item["preexisting_actual_count"] for item in turns
        ),
        "new_actual_count": sum(item["new_actual_count"] for item in turns),
        "unknown_age_actual_count": sum(
            item["unknown_age_actual_count"] for item in turns
        ),
        "improved_turn_count": len(improved),
        "improved_experience_ids": improved,
        "turns": turns,
    }


async def fetch_experiences(
    driver: Any,
    *,
    database: str,
    experience_ids: list[str],
) -> list[dict[str, Any]]:
    async with driver.session(database=database) as session:
        result = await session.run(
            EXPERIENCE_QUERY,
            experience_ids=experience_ids,
        )
        records = await result.fetch(len(experience_ids))
    by_id = {record["experience_id"]: dict(record) for record in records}
    return [by_id[item] for item in experience_ids if item in by_id]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read-only B4 canonical scoring replay",
    )
    parser.add_argument(
        "--experience-id",
        action="append",
        help="Experience ID; defaults to all 12 preserved B3 turns",
    )
    return parser.parse_args()


async def _run(experience_ids: list[str]) -> dict[str, Any]:
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
        records = await fetch_experiences(
            driver,
            database=required["NEO4J_DATABASE"],
            experience_ids=experience_ids,
        )
    finally:
        await driver.close()

    report = summarize_replay(records)
    report["requested_count"] = len(experience_ids)
    report["missing_experience_ids"] = [
        item for item in experience_ids
        if item not in {record["experience_id"] for record in records}
    ]
    return report


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = _parse_args()
    experience_ids = list(dict.fromkeys(
        args.experience_id or B3_EXPERIENCE_IDS
    ))
    report = asyncio.run(_run(experience_ids))
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
