"""B5.8 post-hoc measurement audit and source-aware offline ranker.

The six B5.7 questions are train diagnostics only.  This module never mutates
Neo4j, never changes the live predictor, and always blocks production
promotion because candidate design and inspection used the same six answers.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from neural.baby.live_curiosity import filter_curiosity_cue_terms
from neural.baby.pending_question_outcome import (
    audit_pending_question_terms,
    build_pending_question_terms,
)
from scripts.research.b4_canonical_scoring import is_cue_surface_variant


DEFAULT_B5_7_ARTIFACT = (
    PROJECT_ROOT / "claudedocs" / "research"
    / "b5_7_pending_question_train_a_20260716.json"
)
DEFAULT_MANIFEST = (
    PROJECT_ROOT / "scripts" / "research" / "manifests"
    / "b5_7_pending_question_train_a_20260716.json"
)
DEFAULT_ANSWERS = (
    PROJECT_ROOT / "scripts" / "research" / "inputs"
    / "b5_7_pending_question_train_a_20260716_answers.json"
)
DEFAULT_OUTPUT = (
    PROJECT_ROOT / "claudedocs" / "research"
    / "b5_8_measurement_validity_ranker_20260716.json"
)

QUESTION_QUERY = """
MATCH (cl:CuriosityLog)-[:GENERATED]->(pq:PendingQuestion)
WHERE pq.question_outcome_contract_sha256 = $contract_sha256
RETURN cl.id AS curiosity_log_id,
       pq.id AS question_id,
       pq.question AS question,
       pq.curiosity_cue_ids AS cue_ids,
       pq.predicted_concept_ids AS predicted_ids,
       pq.external_outcome_concept_ids AS outcome_ids,
       pq.prediction_captured_at AS prediction_captured_at,
       pq.asked_at AS asked_at,
       pq.answered_at AS answered_at
ORDER BY curiosity_log_id
"""

CONCEPT_NAMES_QUERY = """
MATCH (concept:Concept)
WHERE concept.id IN $concept_ids
RETURN concept.id AS id, concept.name AS name
ORDER BY id
"""

OUTCOME_RESOLUTION_QUERY = """
UNWIND $outcome_terms AS outcome_term
MATCH (concept:Concept)
WHERE concept.name IS NOT NULL
  AND toLower(trim(toString(concept.name))) = outcome_term
  AND concept.created_at IS NOT NULL
  AND datetime(toString(concept.created_at)) <= datetime($prediction_captured_at)
  AND NOT concept.id IN $cue_ids
RETURN concept.id AS id, concept.name AS name
ORDER BY id
"""

NEIGHBOR_QUERY = """
UNWIND $source_ids AS source_id
CALL (source_id) {
  MATCH (source:Concept {id: source_id})-[rel:RELATES_TO]-(neighbor:Concept)
  OPTIONAL MATCH (neighbor)-[degree_rel:RELATES_TO]-()
  WITH source, neighbor, rel, count(degree_rel) AS neighbor_degree,
       coalesce(rel.hebb_strength, rel.strength, 0.0) AS strength
  ORDER BY strength DESC, neighbor.id ASC
  LIMIT $per_source_limit
  RETURN neighbor.id AS neighbor_id,
         neighbor.name AS neighbor_name,
         neighbor_degree,
         strength,
         coalesce(rel.source, '') AS relation_source,
         coalesce(rel.relation_type, '') AS relation_type,
         CASE WHEN startNode(rel) = source THEN 'outbound' ELSE 'inbound' END
           AS direction
}
RETURN source_id, neighbor_id, neighbor_name, neighbor_degree, strength,
       relation_source, relation_type, direction
ORDER BY source_id, strength DESC, neighbor_id
"""

DIRECT_NEIGHBOR_LIMIT = 48
SECOND_HOP_SOURCE_LIMIT = 12
SECOND_NEIGHBOR_LIMIT = 48


def _bounded_strength(value: Any) -> float:
    try:
        return max(0.0, min(1.0, float(value or 0.0)))
    except (TypeError, ValueError):
        return 0.0


def _edge_evidence(edge: dict[str, Any]) -> float:
    strength = _bounded_strength(edge.get("strength"))
    relation_type = str(edge.get("relation_type") or "").strip().casefold()
    source = str(edge.get("source") or "").strip().casefold()
    direction = str(edge.get("direction") or "").strip().casefold()

    if source == "visual_cooc":
        source_weight = 0.35
    elif source == "hebbian":
        source_weight = 0.55
    elif relation_type:
        source_weight = 1.0
    else:
        source_weight = 0.65

    if relation_type:
        direction_weight = 1.0 if direction == "outbound" else 0.25
    else:
        direction_weight = 0.8
    return strength * source_weight * direction_weight


def _path_evidence(path: dict[str, Any]) -> float:
    edges = [dict(edge) for edge in (path.get("edges") or [])]
    if not edges or len(edges) > 2:
        return 0.0
    edge_values = [_edge_evidence(edge) for edge in edges]
    if any(value <= 0.0 for value in edge_values):
        return 0.0
    geometric_mean = math.prod(edge_values) ** (1.0 / len(edge_values))
    path_decay = 1.0 if len(edge_values) == 1 else 0.55
    return geometric_mean * path_decay


def _eligible_candidate(name: str, cue_names: Iterable[str]) -> bool:
    if not filter_curiosity_cue_terms([name]):
        return False
    return not any(is_cue_surface_variant(name, cue) for cue in cue_names)


def rank_source_aware_candidates(
    candidates: Iterable[dict[str, Any]],
    *,
    cue_names: Iterable[str],
    limit: int = 8,
) -> list[dict[str, Any]]:
    """Rank post-hoc paths with source, direction, support, and degree evidence."""

    normalized_cues = [str(item) for item in cue_names if str(item).strip()]
    ranked: list[dict[str, Any]] = []
    for candidate in candidates:
        candidate_id = str(candidate.get("id") or "").strip()
        name = str(candidate.get("name") or "").strip()
        if not candidate_id or not name or not _eligible_candidate(name, normalized_cues):
            continue

        best_by_cue: dict[str, float] = {}
        path_count = 0
        for raw_path in candidate.get("paths") or []:
            path = dict(raw_path)
            cue_id = str(path.get("cue_id") or "").strip()
            evidence = _path_evidence(path)
            if not cue_id or evidence <= 0.0:
                continue
            path_count += 1
            best_by_cue[cue_id] = max(best_by_cue.get(cue_id, 0.0), evidence)
        if not best_by_cue:
            continue

        support_count = len(best_by_cue)
        support_bonus = 0.2 * max(0, support_count - 1)
        try:
            degree = max(0, int(candidate.get("degree") or 0))
        except (TypeError, ValueError):
            degree = 0
        degree_penalty = math.log2(degree + 2)
        score = (sum(best_by_cue.values()) + support_bonus) / degree_penalty
        ranked.append({
            "id": candidate_id,
            "name": name,
            "score": round(score, 8),
            "cue_support_count": support_count,
            "degree": degree,
            "path_count": path_count,
            "best_evidence_by_cue": {
                key: round(best_by_cue[key], 8) for key in sorted(best_by_cue)
            },
        })

    ranked.sort(key=lambda item: (
        -item["score"],
        -item["cue_support_count"],
        item["degree"],
        item["name"].casefold(),
        item["id"],
    ))
    return ranked[:max(0, int(limit))]


def summarize_train_diagnostic(
    questions: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    baseline_hits = 0
    source_aware_hits = 0
    reachable_outcomes = 0
    outcome_count = 0
    for question in questions:
        outcomes = {str(item) for item in question.get("outcome_ids") or [] if item}
        baseline = {
            str(item) for item in question.get("baseline_predicted_ids") or [] if item
        }
        ranked = list(question.get("ranked_candidates") or [])
        source_aware = {str(item.get("id")) for item in ranked if item.get("id")}
        candidate_pool = {
            str(item) for item in question.get("candidate_pool_ids") or [] if item
        }
        if not candidate_pool:
            candidate_pool = source_aware
        baseline_match = len(outcomes & baseline)
        source_match = len(outcomes & source_aware)
        reachable = len(outcomes & candidate_pool)
        baseline_hits += baseline_match
        source_aware_hits += source_match
        reachable_outcomes += reachable
        outcome_count += len(outcomes)
        rows.append({
            "question_id": question.get("question_id"),
            "outcome_count": len(outcomes),
            "reachable_outcome_count": reachable,
            "baseline_hit_count": baseline_match,
            "source_aware_hit_count": source_match,
            "source_aware_prediction_ids": [item["id"] for item in ranked],
        })
    return {
        "train_only": True,
        "question_count": len(rows),
        "outcome_count": outcome_count,
        "two_hop_reachable_outcome_count": reachable_outcomes,
        "stored_live_hit_count": baseline_hits,
        "source_aware_hit_count": source_aware_hits,
        "production_promotion_gate": False,
        "production_block_reason": "post_hoc_same_six_train_questions",
        "heldout_required": True,
        "questions": rows,
    }


def _record_edge(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "strength": record.get("strength"),
        "source": record.get("relation_source"),
        "relation_type": record.get("relation_type"),
        "direction": record.get("direction"),
    }


def _group_bounded_paths(
    direct_records: Iterable[dict[str, Any]],
    second_records: Iterable[dict[str, Any]],
    *,
    cue_ids: Iterable[str],
) -> list[dict[str, Any]]:
    cues = {str(item) for item in cue_ids if item}
    candidates: dict[str, dict[str, Any]] = {}

    def add_candidate(
        candidate_id: str,
        name: str,
        degree: int,
        path: dict[str, Any],
    ) -> None:
        if not candidate_id or candidate_id in cues:
            return
        item = candidates.setdefault(candidate_id, {
            "id": candidate_id,
            "name": name,
            "degree": degree,
            "paths": [],
        })
        item["paths"].append(path)

    direct = [dict(record) for record in direct_records]
    second_by_source: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in second_records:
        second_by_source[str(record.get("source_id") or "")].append(dict(record))

    for record in direct:
        cue_id = str(record.get("source_id") or "").strip()
        candidate_id = str(record.get("neighbor_id") or "").strip()
        if not candidate_id:
            continue
        first_edge = _record_edge(record)
        add_candidate(
            candidate_id,
            str(record.get("neighbor_name") or "").strip(),
            int(record.get("neighbor_degree") or 0),
            {"cue_id": cue_id, "path_length": 1, "edges": [first_edge]},
        )
        for second in second_by_source.get(candidate_id, []):
            second_id = str(second.get("neighbor_id") or "").strip()
            add_candidate(
                second_id,
                str(second.get("neighbor_name") or "").strip(),
                int(second.get("neighbor_degree") or 0),
                {
                    "cue_id": cue_id,
                    "path_length": 2,
                    "edges": [first_edge, _record_edge(second)],
                },
            )
    return list(candidates.values())


def _select_second_hop_sources(
    records: Iterable[dict[str, Any]],
) -> list[str]:
    by_cue: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        by_cue[str(record.get("source_id") or "")].append(dict(record))
    selected: list[str] = []
    for cue_id in sorted(by_cue):
        ranked = sorted(by_cue[cue_id], key=lambda item: (
            -_edge_evidence(_record_edge(item)),
            int(item.get("neighbor_degree") or 0),
            str(item.get("neighbor_id") or ""),
        ))
        selected.extend(
            str(item.get("neighbor_id"))
            for item in ranked[:SECOND_HOP_SOURCE_LIMIT]
            if item.get("neighbor_id")
        )
    return list(dict.fromkeys(selected))


async def _fetch_report_inputs(
    *,
    contract_sha256: str,
    outcome_terms_by_curiosity: dict[str, list[str]],
) -> list[dict[str, Any]]:
    from dotenv import load_dotenv
    from neo4j import AsyncGraphDatabase

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
        async with driver.session(database=required["NEO4J_DATABASE"]) as session:
            result = await session.run(
                QUESTION_QUERY,
                contract_sha256=contract_sha256,
            )
            questions = [dict(record) async for record in result]
            for question in questions:
                question["stored_outcome_ids"] = list(
                    question.get("outcome_ids") or []
                )
                outcome_result = await session.run(
                    OUTCOME_RESOLUTION_QUERY,
                    outcome_terms=outcome_terms_by_curiosity.get(
                        str(question.get("curiosity_log_id")),
                        [],
                    ),
                    prediction_captured_at=question.get("prediction_captured_at"),
                    cue_ids=question.get("cue_ids") or [],
                )
                recomputed_outcomes = [dict(record) async for record in outcome_result]
                question["outcome_ids"] = [
                    item["id"] for item in recomputed_outcomes
                ]
                concept_ids = list(dict.fromkeys([
                    *(question.get("cue_ids") or []),
                    *(question.get("outcome_ids") or []),
                    *(question.get("stored_outcome_ids") or []),
                ]))
                names_result = await session.run(
                    CONCEPT_NAMES_QUERY,
                    concept_ids=concept_ids,
                )
                names = {
                    str(record["id"]): str(record["name"])
                    async for record in names_result
                }
                direct_result = await session.run(
                    NEIGHBOR_QUERY,
                    source_ids=question.get("cue_ids") or [],
                    per_source_limit=DIRECT_NEIGHBOR_LIMIT,
                )
                direct_records = [dict(record) async for record in direct_result]
                second_source_ids = _select_second_hop_sources(direct_records)
                second_result = await session.run(
                    NEIGHBOR_QUERY,
                    source_ids=second_source_ids,
                    per_source_limit=SECOND_NEIGHBOR_LIMIT,
                )
                second_records = [dict(record) async for record in second_result]
                question["cue_names"] = [
                    names[item] for item in (question.get("cue_ids") or [])
                    if item in names
                ]
                question["outcome_names"] = [
                    names[item] for item in (question.get("outcome_ids") or [])
                    if item in names
                ]
                question["stored_outcome_names"] = [
                    names[item] for item in (question.get("stored_outcome_ids") or [])
                    if item in names
                ]
                question["candidates"] = _group_bounded_paths(
                    direct_records,
                    second_records,
                    cue_ids=question.get("cue_ids") or [],
                )
        return questions
    finally:
        await driver.close()


async def run(args: argparse.Namespace) -> dict[str, Any]:
    artifact = json.loads(args.b5_7_artifact.read_text(encoding="utf-8"))
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    answers = json.loads(args.answers.read_text(encoding="utf-8"))
    contract_sha256 = str(artifact.get("contract_sha256") or "")
    if not contract_sha256 or manifest.get("contract_sha256") != contract_sha256:
        raise RuntimeError("B5.7 artifact and manifest contract hashes differ")
    if answers.get("contract_sha256") != contract_sha256:
        raise RuntimeError("B5.7 answer pack contract hash differs")

    order_by_curiosity = {
        item["curiosity_log_id"]: item["order"] for item in manifest["questions"]
    }
    answer_by_order = {item["order"]: item for item in answers["answers"]}
    outcome_terms_by_curiosity = {
        item["curiosity_log_id"]: build_pending_question_terms(
            answer_by_order[item["order"]]["answer"]
        )
        for item in manifest["questions"]
    }
    questions = await _fetch_report_inputs(
        contract_sha256=contract_sha256,
        outcome_terms_by_curiosity=outcome_terms_by_curiosity,
    )
    evaluated: list[dict[str, Any]] = []
    for question in questions:
        order = order_by_curiosity.get(question.get("curiosity_log_id"))
        ranked = rank_source_aware_candidates(
            question.get("candidates") or [],
            cue_names=question.get("cue_names") or [],
            limit=max(1, len(question.get("predicted_ids") or [])),
        )
        evaluated.append({
            "question_id": question.get("question_id"),
            "curiosity_log_id": question.get("curiosity_log_id"),
            "order": order,
            "cue_ids": question.get("cue_ids") or [],
            "cue_names": question.get("cue_names") or [],
            "outcome_ids": question.get("outcome_ids") or [],
            "outcome_names": question.get("outcome_names") or [],
            "stored_outcome_ids": question.get("stored_outcome_ids") or [],
            "stored_outcome_names": question.get("stored_outcome_names") or [],
            "baseline_predicted_ids": question.get("predicted_ids") or [],
            "candidate_pool_ids": [
                item["id"] for item in (question.get("candidates") or [])
            ],
            "candidate_pool_count": len(question.get("candidates") or []),
            "ranked_candidates": ranked,
        })

    audits = []
    for entry in answers["answers"]:
        terms = build_pending_question_terms(entry["answer"])
        audits.append({
            "order": entry["order"],
            "terms": terms,
            **audit_pending_question_terms(entry["answer"], terms),
        })
    diagnostic = summarize_train_diagnostic(evaluated)
    return {
        "status": "completed",
        "phase": "B5.8",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "contract_sha256": contract_sha256,
        "database_writes": False,
        "live_predictor_changed": False,
        "conversation_handler_changed": False,
        "measurement_validity": {
            "structural_contract_gate": bool(
                artifact.get("evaluation", {}).get("target_validity_gate")
            ),
            "parser_measurement_gate": all(
                item["measurement_content_gate"] for item in audits
            ),
            "semantic_outcome_content_validity_gate": False,
            "semantic_block_reason": "reviewed_outcome_labels_not_supplied",
            "legacy_target_validity_reclassified": True,
            "outcome_term_audits": audits,
        },
        "ranker_contract": {
            "candidate_depth": 2,
            "direct_neighbor_limit_per_cue": DIRECT_NEIGHBOR_LIMIT,
            "second_hop_source_limit_per_cue": SECOND_HOP_SOURCE_LIMIT,
            "second_neighbor_limit_per_source": SECOND_NEIGHBOR_LIMIT,
            "relation_source_weighted": True,
            "semantic_direction_weighted": True,
            "multi_cue_support_rewarded": True,
            "candidate_degree_penalized": True,
            "deterministic_tie_break": True,
            "temporal_relationship_replay_safe": False,
        },
        "diagnostic": diagnostic,
        "questions": evaluated,
        "production_promotion_gate": False,
        "production_block_reasons": [
            "post_hoc_same_six_train_questions",
            "semantic_outcome_labels_not_independently_reviewed",
            "historical_relationship_state_not_replayable",
        ],
        "next_step": (
            "review_semantic_outcome_labels_and_represent_action_answer_relations_"
            "before_heldout"
        ),
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="B5.8 read-only measurement audit and offline ranker",
    )
    parser.add_argument("--b5-7-artifact", type=Path, default=DEFAULT_B5_7_ARTIFACT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--answers", type=Path, default=DEFAULT_ANSWERS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--compact", action="store_true")
    return parser.parse_args()


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = _parse_args()
    report = asyncio.run(run(args))
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    rendered: dict[str, Any] = report
    if args.compact:
        rendered = {
            "status": report["status"],
            "database_writes": report["database_writes"],
            "measurement_validity": report["measurement_validity"],
            "diagnostic": report["diagnostic"],
            "production_promotion_gate": report["production_promotion_gate"],
            "production_block_reasons": report["production_block_reasons"],
            "next_step": report["next_step"],
            "output": str(output),
        }
    print(json.dumps(rendered, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
