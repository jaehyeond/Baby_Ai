"""Read-only B5.2 ablation for external-outcome graph predictions.

The live predictor ranks the union of cue neighbours by one maximum mutable
edge strength.  Replaying that ranking after the pilot would leak later graph
updates because RELATES_TO does not retain historical strength versions.

This diagnostic therefore uses only immutable conversation Experiences that
were created strictly before each source turn.  It compares three exploratory
association rankers with the stored live prediction and B5 frequency/random
baselines.  The same six B5.1 pairs are used for model selection, so even a
passing exploratory candidate requires a new preregistered held-out pilot
before production promotion.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from dotenv import load_dotenv
from neo4j import AsyncGraphDatabase

from neural.baby.live_curiosity import filter_curiosity_cue_terms
from scripts.research import b5_external_outcome_evaluation as b5


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE_ARTIFACT = (
    PROJECT_ROOT
    / "claudedocs"
    / "research"
    / "b5_1_external_outcome_pilot_v2_1_20260715.json"
)
DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "claudedocs"
    / "research"
    / "b5_2_graph_predictor_ablation_20260715.json"
)
VARIANTS = (
    "historical_cooccurrence",
    "historical_cosine",
    "historical_multi_cue_cosine",
)

ASSOCIATION_HISTORY_QUERY = """
MATCH (e:Experience)
WHERE e.task_type = 'conversation' AND e.created_at IS NOT NULL
OPTIONAL MATCH (e)-[:INVOLVES]->(concept:Concept)
RETURN e.id AS experience_id,
       e.task AS task,
       toString(e.created_at) AS created_at,
       collect(DISTINCT {
         id: concept.id,
         name: concept.name,
         created_at: toString(concept.created_at)
       }) AS concepts
ORDER BY created_at
"""

TRANSITION_COVERAGE_QUERY = """
CALL () {
  MATCH (e:Experience)
  WHERE e.task_type = 'conversation'
  WITH e, properties(e) AS props
  RETURN count(e) AS conversation_count,
         sum(CASE WHEN props[$session_key] IS NOT NULL THEN 1 ELSE 0 END)
           AS with_session_id,
         sum(CASE WHEN props[$speaker_key] IS NOT NULL THEN 1 ELSE 0 END)
           AS with_speaker_id,
         sum(CASE WHEN props[$user_key] IS NOT NULL THEN 1 ELSE 0 END)
           AS with_user_id
}
CALL () {
  MATCH (:Experience)-[link]->(:Experience)
  WHERE type(link) = $next_turn_type
  RETURN count(link) AS next_turn_link_count
}
RETURN conversation_count,
       with_session_id,
       with_speaker_id,
       with_user_id,
       next_turn_link_count
"""


def _valid_concepts(items: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return [item for item in items if item and item.get("id") and item.get("name")]


def _eligible_candidate(name: str, cue_names: Iterable[str]) -> bool:
    if not filter_curiosity_cue_terms([name]):
        return False
    if b5.normalize_concept_name(name) in b5._EXTERNAL_INPUT_FUNCTION_TERMS:
        return False
    return not any(b5.is_cue_surface_variant(name, cue) for cue in cue_names)


def _history_before(
    history: Iterable[dict[str, Any]],
    source_created_at: Any,
) -> list[dict[str, Any]]:
    source_time = b5._parse_timestamp(source_created_at)
    if source_time is None:
        return []
    prior: list[dict[str, Any]] = []
    for record in history:
        record_time = b5._parse_timestamp(record.get("created_at"))
        if record_time is not None and record_time < source_time:
            prior.append(record)
    return prior


def rank_historical_associations(
    source: dict[str, Any],
    history: Iterable[dict[str, Any]],
    *,
    variant: str,
    limit: int,
) -> dict[str, Any]:
    """Rank without target input, mutable relationships, or future records."""

    if variant not in VARIANTS:
        raise ValueError(f"unknown variant: {variant}")
    if limit <= 0:
        return {"predicted_names": [], "candidates": [], "history_count": 0}

    cues = _valid_concepts(source.get("cue_concepts") or [])
    cue_ids = [str(item["id"]) for item in cues]
    cue_names = [str(item["name"]) for item in cues]
    prior = _history_before(history, source.get("created_at"))

    cue_document_frequency: Counter[str] = Counter()
    candidate_document_frequency: Counter[str] = Counter()
    cooccurrence: dict[str, Counter[str]] = defaultdict(Counter)
    surfaces: dict[str, str] = {}

    for record in prior:
        concepts = _valid_concepts(record.get("concepts") or [])
        present_ids = {str(item["id"]) for item in concepts}
        present_cues = [cue_id for cue_id in cue_ids if cue_id in present_ids]
        for cue_id in present_cues:
            cue_document_frequency[cue_id] += 1

        present_candidates: dict[str, str] = {}
        for concept in concepts:
            name = str(concept["name"])
            if not _eligible_candidate(name, cue_names):
                continue
            key = b5.canonical_bucket(name)
            if not key:
                continue
            previous = present_candidates.get(key)
            if previous is None or (len(name), name) < (len(previous), previous):
                present_candidates[key] = name

        for key, name in present_candidates.items():
            candidate_document_frequency[key] += 1
            previous = surfaces.get(key)
            if previous is None or (len(name), name) < (len(previous), previous):
                surfaces[key] = name
            for cue_id in present_cues:
                cooccurrence[key][cue_id] += 1

    candidates: list[dict[str, Any]] = []
    for key, by_cue in cooccurrence.items():
        total_cooccurrence = sum(by_cue.values())
        if total_cooccurrence <= 0:
            continue
        support_count = sum(count > 0 for count in by_cue.values())
        candidate_df = candidate_document_frequency[key]
        cosine_score = sum(
            count
            / math.sqrt(
                max(1, cue_document_frequency[cue_id]) * max(1, candidate_df)
            )
            for cue_id, count in by_cue.items()
        )
        candidates.append({
            "key": key,
            "name": surfaces[key],
            "cue_support_count": support_count,
            "cooccurrence_count": total_cooccurrence,
            "candidate_document_frequency": candidate_df,
            "cosine_score": round(cosine_score, 8),
        })

    if variant == "historical_cooccurrence":
        rank_key = lambda item: (
            -item["cooccurrence_count"],
            -item["cue_support_count"],
            item["candidate_document_frequency"],
            item["key"],
        )
    elif variant == "historical_cosine":
        rank_key = lambda item: (
            -item["cosine_score"],
            -item["cooccurrence_count"],
            item["candidate_document_frequency"],
            item["key"],
        )
    else:
        rank_key = lambda item: (
            -item["cue_support_count"],
            -item["cosine_score"],
            -item["cooccurrence_count"],
            item["candidate_document_frequency"],
            item["key"],
        )

    ranked = sorted(candidates, key=rank_key)[:limit]
    return {
        "predicted_names": [item["name"] for item in ranked],
        "candidates": ranked,
        "history_count": len(prior),
        "cue_document_frequency": {
            cue_id: cue_document_frequency[cue_id] for cue_id in cue_ids
        },
    }


def _hit_count(error: float | None, actual_count: int) -> int:
    if error is None or actual_count <= 0:
        return 0
    return int(round((1.0 - float(error)) * actual_count))


def summarize_variant(
    variant: str,
    evaluated_pairs: list[dict[str, Any]],
) -> dict[str, Any]:
    scorable = [item for item in evaluated_pairs if item["error"] is not None]
    errors = [float(item["error"]) for item in scorable]
    frequency_errors = [float(item["frequency_error"]) for item in scorable]
    random_errors = [float(item["random_expected_error"]) for item in scorable]
    mean_error = round(sum(errors) / len(errors), 6) if errors else None
    frequency_mean = (
        round(sum(frequency_errors) / len(frequency_errors), 6)
        if frequency_errors else None
    )
    random_mean = (
        round(sum(random_errors) / len(random_errors), 6) if random_errors else None
    )
    better = sum(item["error"] < item["frequency_error"] for item in scorable)
    tied = sum(item["error"] == item["frequency_error"] for item in scorable)
    worse = sum(item["error"] > item["frequency_error"] for item in scorable)
    hits = sum(
        _hit_count(item["error"], len(item["actual_names"])) for item in scorable
    )
    data_gate = len(scorable) >= b5.MIN_SCORABLE_PAIRS
    baseline_gate = (
        mean_error is not None
        and frequency_mean is not None
        and random_mean is not None
        and mean_error < frequency_mean
        and mean_error < random_mean
    )
    robustness_gate = (
        better >= b5.MIN_BASELINE_IMPROVED_PAIRS
        and hits >= b5.MIN_GRAPH_HITS
        and better > worse
    )
    exploratory_gate = data_gate and baseline_gate and robustness_gate
    return {
        "variant": variant,
        "mean_error": mean_error,
        "frequency_mean_error": frequency_mean,
        "random_expected_mean_error": random_mean,
        "hit_count": hits,
        "better_than_frequency_pair_count": better,
        "tied_with_frequency_pair_count": tied,
        "worse_than_frequency_pair_count": worse,
        "data_gate": data_gate,
        "baseline_gate": baseline_gate,
        "robustness_gate": robustness_gate,
        "exploratory_gate": exploratory_gate,
        "production_promotion_gate": False,
        "production_block_reason": "same_pairs_used_for_candidate_selection",
        "pairs": evaluated_pairs,
    }


def evaluate_variants(
    pairs: Iterable[dict[str, Any]],
    concepts: Iterable[dict[str, Any]],
    task_history: Iterable[dict[str, Any]],
    association_history: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    base_pairs = [b5.evaluate_pair(pair, concepts, task_history) for pair in pairs]
    pair_sources = [pair["source"] for pair in pairs]
    reports: dict[str, Any] = {}

    for variant in ("stored_live_graph", *VARIANTS):
        evaluated: list[dict[str, Any]] = []
        for source, base in zip(pair_sources, base_pairs):
            limit = max(1, len(base["predicted_names"]))
            if variant == "stored_live_graph":
                predicted_names = list(base["predicted_names"])
                rank_diagnostics: list[dict[str, Any]] = []
                history_count = None
            else:
                ranked = rank_historical_associations(
                    source,
                    association_history,
                    variant=variant,
                    limit=limit,
                )
                predicted_names = ranked["predicted_names"]
                rank_diagnostics = ranked["candidates"]
                history_count = ranked["history_count"]
            actual_names = list(base["preexisting_outcome_terms"])
            error = b5.compute_name_prediction_error(predicted_names, actual_names)
            random_error = (
                b5.expected_random_error(
                    vocabulary_size=base["available_vocabulary_size"],
                    prediction_count=len(predicted_names),
                )
                if actual_names else None
            )
            evaluated.append({
                "source_experience_id": base["source_experience_id"],
                "source_task": base["source_task"],
                "cue_names": base["cue_names"],
                "actual_names": actual_names,
                "predicted_names": predicted_names,
                "prediction_count": len(predicted_names),
                "error": error,
                "frequency_error": base["frequency_error"],
                "random_expected_error": random_error,
                "history_count": history_count,
                "rank_diagnostics": rank_diagnostics,
            })
        reports[variant] = summarize_variant(variant, evaluated)

    candidates = [
        report for name, report in reports.items() if name != "stored_live_graph"
    ]
    best = min(
        candidates,
        key=lambda item: (
            float("inf") if item["mean_error"] is None else item["mean_error"],
            -item["hit_count"],
            item["variant"],
        ),
    )
    return {
        "variants": reports,
        "best_exploratory_variant": best["variant"],
        "best_exploratory_mean_error": best["mean_error"],
        "any_exploratory_gate_passed": any(
            report["exploratory_gate"] for report in candidates
        ),
        "production_promotion_gate": False,
        "production_block_reason": "no_preregistered_held_out_sequence",
    }


async def fetch_inputs(
    driver: Any,
    *,
    database: str,
    experience_ids: list[str],
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    dict[str, Any],
]:
    async with driver.session(database=database) as session:
        result = await session.run(b5.SEQUENCE_QUERY, experience_ids=experience_ids)
        sequence_records = [dict(record) for record in await result.fetch(len(experience_ids))]
        result = await session.run(b5.HISTORY_QUERY)
        task_history = [dict(record) async for record in result]
        result = await session.run(b5.CONCEPT_QUERY)
        concepts = [dict(record) async for record in result]
        result = await session.run(ASSOCIATION_HISTORY_QUERY)
        association_history = [dict(record) async for record in result]
        result = await session.run(
            TRANSITION_COVERAGE_QUERY,
            session_key="session_id",
            speaker_key="speaker_id",
            user_key="user_id",
            next_turn_type="NEXT_TURN",
        )
        coverage_record = await result.single()
    return (
        sequence_records,
        task_history,
        concepts,
        association_history,
        dict(coverage_record) if coverage_record else {},
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read-only B5.2 graph predictor ablation",
    )
    parser.add_argument("--artifact", type=Path, default=DEFAULT_SOURCE_ARTIFACT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--compact", action="store_true")
    return parser.parse_args()


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

    source_path = args.artifact.resolve()
    source_report = json.loads(source_path.read_text(encoding="utf-8"))
    experience_ids = list(source_report.get("experience_ids") or [])
    if len(experience_ids) < 2:
        raise RuntimeError("source artifact has fewer than two Experience IDs")

    driver = AsyncGraphDatabase.driver(
        required["NEO4J_URI"],
        auth=(required["NEO4J_USERNAME"], required["NEO4J_PASSWORD"]),
    )
    try:
        await driver.verify_connectivity()
        records, task_history, concepts, association_history, coverage = (
            await fetch_inputs(
                driver,
                database=str(required["NEO4J_DATABASE"]),
                experience_ids=experience_ids,
            )
        )
    finally:
        await driver.close()

    pilot_name = str(source_report.get("pilot_name") or "b5_1_sequence")
    pairs, missing_ids = b5.build_sequence_pairs(
        records,
        sequences=((pilot_name, tuple(experience_ids)),),
    )
    if missing_ids:
        raise RuntimeError(f"missing Experience IDs: {missing_ids}")

    transition_eligible = bool(
        int(coverage.get("next_turn_link_count") or 0) > 0
        or int(coverage.get("with_session_id") or 0) >= 2
    )
    evaluation = evaluate_variants(
        pairs,
        concepts,
        task_history,
        association_history,
    )
    return {
        "status": "completed",
        "phase": "B5.2",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_artifact": str(source_path),
        "source_contract_sha256": source_report.get("contract_sha256"),
        "experience_ids": experience_ids,
        "database_writes": False,
        "temporal_integrity": {
            "history_strictly_before_source": True,
            "mutable_relationship_strength_used": False,
            "target_input_used_for_ranking": False,
        },
        "current_predictor_diagnosis": {
            "candidate_union": "all RELATES_TO neighbours of selected cues",
            "aggregation": "max mutable edge strength across cues",
            "candidate_degree_penalty": False,
            "multi_cue_support_reward": False,
            "historical_strength_replay_safe": False,
        },
        "transition_route": {
            **coverage,
            "eligible": transition_eligible,
            "reason": (
                "session_or_next_turn_boundary_available"
                if transition_eligible
                else "no_session_id_or_NEXT_TURN_boundary"
            ),
        },
        "evaluation": evaluation,
    }


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = _parse_args()
    report = asyncio.run(_run(args))
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    output.write_text(f"{rendered}\n", encoding="utf-8")

    printed = report
    if args.compact:
        evaluation = report["evaluation"]
        printed = {
            "status": report["status"],
            "database_writes": report["database_writes"],
            "temporal_integrity": report["temporal_integrity"],
            "transition_route": report["transition_route"],
            "best_exploratory_variant": evaluation["best_exploratory_variant"],
            "best_exploratory_mean_error": evaluation["best_exploratory_mean_error"],
            "any_exploratory_gate_passed": evaluation["any_exploratory_gate_passed"],
            "production_promotion_gate": evaluation["production_promotion_gate"],
            "variants": {
                name: {
                    key: variant[key]
                    for key in (
                        "mean_error",
                        "hit_count",
                        "better_than_frequency_pair_count",
                        "tied_with_frequency_pair_count",
                        "worse_than_frequency_pair_count",
                        "exploratory_gate",
                    )
                }
                for name, variant in evaluation["variants"].items()
            },
            "output": str(output),
        }
    print(json.dumps(printed, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
