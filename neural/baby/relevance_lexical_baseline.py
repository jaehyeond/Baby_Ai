"""Deterministic character n-gram TF-IDF relevance baseline for J1-R2.

The scorer sees only question text and the sealed candidate names. Labels are
used after ranking for evaluation and never affect IDF fitting or scores.
"""

from __future__ import annotations

import hashlib
import math
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime
from typing import Any, Iterable, Mapping

from neural.baby.pending_question_semantics import canonical_json_sha256


LEXICAL_BASELINE_ARTIFACT_VERSION = 1
BASELINE_ID = "lexical_char_ngram_tfidf_v1"
PHASE = "J1-R2"
MIN_N = 2
MAX_N = 5
EVALUATION_K = 8
DISPLAY_K = 20
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def normalize_lexical_text(value: str) -> str:
    """Apply the frozen lexical normalization contract."""

    normalized = unicodedata.normalize("NFKC", str(value)).casefold()
    return " ".join(normalized.split())


def character_ngram_counts(
    value: str,
    *,
    min_n: int = MIN_N,
    max_n: int = MAX_N,
) -> Counter[str]:
    """Return raw character n-gram counts after lexical normalization."""

    if min_n < 1 or max_n < min_n:
        raise ValueError("invalid character n-gram range")
    text = normalize_lexical_text(value)
    counts: Counter[str] = Counter()
    for n in range(min_n, max_n + 1):
        for start in range(max(0, len(text) - n + 1)):
            counts[text[start : start + n]] += 1
    return counts


def _l2_normalized_tfidf(
    counts: Mapping[str, int],
    idf: Mapping[str, float],
) -> dict[str, float]:
    weights = {
        gram: float(count) * idf[gram]
        for gram, count in counts.items()
        if gram in idf and count > 0
    }
    norm = math.sqrt(sum(weight * weight for weight in weights.values()))
    if norm == 0.0:
        return {}
    return {gram: weight / norm for gram, weight in weights.items()}


def build_lexical_index(
    concepts: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    """Fit label-free IDF on sealed candidate names and index every concept."""

    records = sorted(
        (
            {
                "concept_id": str(item.get("concept_id") or ""),
                "concept_name": str(item.get("concept_name") or ""),
            }
            for item in concepts
        ),
        key=lambda item: item["concept_id"],
    )
    ids = [item["concept_id"] for item in records]
    if not records or any(not item for item in ids) or len(ids) != len(set(ids)):
        raise ValueError("concepts require unique non-empty IDs")
    if any(not item["concept_name"].strip() for item in records):
        raise ValueError("concepts require non-empty names")

    counts_by_id: dict[str, Counter[str]] = {}
    document_frequency: Counter[str] = Counter()
    for item in records:
        counts = character_ngram_counts(item["concept_name"])
        counts_by_id[item["concept_id"]] = counts
        document_frequency.update(counts.keys())

    document_count = len(records)
    idf = {
        gram: math.log((1.0 + document_count) / (1.0 + frequency)) + 1.0
        for gram, frequency in document_frequency.items()
    }
    vectors = {
        concept_id: _l2_normalized_tfidf(counts, idf)
        for concept_id, counts in counts_by_id.items()
    }
    return {
        "concepts": records,
        "idf": idf,
        "vectors": vectors,
    }


def score_lexical_question(
    index: Mapping[str, Any],
    question: str,
) -> list[dict[str, Any]]:
    """Rank the complete candidate vocabulary with deterministic tie-breaking."""

    query = _l2_normalized_tfidf(
        character_ngram_counts(question),
        index["idf"],
    )
    ranking = []
    for concept in index["concepts"]:
        candidate = index["vectors"][concept["concept_id"]]
        score = round(
            sum(weight * candidate.get(gram, 0.0) for gram, weight in query.items()),
            12,
        )
        ranking.append({**concept, "score": score})
    ranking.sort(key=lambda item: (-item["score"], item["concept_id"]))
    return ranking


def _ranking_metrics(
    ranking: list[Mapping[str, Any]],
    positive_ids: set[str],
    *,
    k: int = EVALUATION_K,
) -> dict[str, float]:
    if not positive_ids:
        raise ValueError("at least one reviewed positive is required")
    rank_by_id = {
        str(item["concept_id"]): rank
        for rank, item in enumerate(ranking, start=1)
    }
    if not positive_ids.issubset(rank_by_id):
        raise ValueError("reviewed positive is outside candidate vocabulary")
    positive_ranks = sorted(rank_by_id[item] for item in positive_ids)
    hits = sum(rank <= k for rank in positive_ranks)
    recall = hits / len(positive_ranks)
    dcg = sum(
        1.0 / math.log2(rank + 1.0)
        for rank in positive_ranks
        if rank <= k
    )
    ideal_hits = min(k, len(positive_ranks))
    ideal_dcg = sum(
        1.0 / math.log2(rank + 1.0)
        for rank in range(1, ideal_hits + 1)
    )
    return {
        f"recall_at_{k}": round(recall, 12),
        f"ndcg_at_{k}": round(dcg / ideal_dcg if ideal_dcg else 0.0, 12),
        "mrr": round(1.0 / positive_ranks[0], 12),
    }


def _average_precision_reviewed_pool(
    score_by_id: Mapping[str, float],
    labels: Iterable[Mapping[str, Any]],
) -> float:
    reviewed = sorted(
        (
            {
                "concept_id": str(item.get("concept_id") or ""),
                "label": int(item.get("label")),
                "score": score_by_id[str(item.get("concept_id") or "")],
            }
            for item in labels
        ),
        key=lambda item: (-item["score"], item["concept_id"]),
    )
    positive_count = sum(item["label"] == 1 for item in reviewed)
    if positive_count == 0:
        raise ValueError("reviewed pool requires a positive label")
    hits = 0
    precision_sum = 0.0
    for rank, item in enumerate(reviewed, start=1):
        if item["label"] == 1:
            hits += 1
            precision_sum += hits / rank
    return round(precision_sum / positive_count, 12)


def _mean(values: Iterable[float]) -> float:
    materialized = list(values)
    return round(sum(materialized) / len(materialized), 12) if materialized else 0.0


def _require_sha256(value: Any, field: str) -> str:
    normalized = str(value or "")
    if not _SHA256_RE.fullmatch(normalized):
        raise ValueError(f"{field} must be a lowercase SHA-256")
    return normalized


def _validate_created_at(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("created_at must be an ISO timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("created_at must include a timezone")
    return str(value)


def _question_sha256(question: str) -> str:
    return hashlib.sha256(question.encode("utf-8")).hexdigest()


def build_lexical_baseline_artifact(
    vocabulary: Mapping[str, Any],
    generator_spec: Mapping[str, Any],
    label_pack: Mapping[str, Any],
    *,
    bindings: Mapping[str, Any],
    created_at: str,
) -> dict[str, Any]:
    """Build a self-hashed, development-only lexical evaluation artifact."""

    candidate_hash = _require_sha256(
        vocabulary.get("candidate_vocabulary_sha256"),
        "candidate_vocabulary_sha256",
    )
    if bindings.get("candidate_vocabulary_sha256") != candidate_hash:
        raise ValueError("binding does not match candidate vocabulary")
    for field, value in bindings.items():
        if field == "input_file_sha256s":
            for path, digest in dict(value).items():
                _require_sha256(digest, f"input_file_sha256s.{path}")
        else:
            _require_sha256(value, f"bindings.{field}")

    concepts = list(vocabulary.get("eligible_concepts") or [])
    questions = list(generator_spec.get("questions") or [])
    label_entries = list(label_pack.get("entries") or [])
    labels_by_question = {
        str(item.get("question_id") or ""): item for item in label_entries
    }
    if len(questions) != len(labels_by_question):
        raise ValueError("question and reviewed-label counts differ")

    index = build_lexical_index(concepts)
    concept_ids = {item["concept_id"] for item in index["concepts"]}
    question_results = []
    for question_item in sorted(questions, key=lambda item: int(item["order"])):
        question_id = str(question_item.get("question_id") or "")
        question = str(question_item.get("question") or "")
        question_hash = _question_sha256(question)
        if question_hash != question_item.get("question_sha256"):
            raise ValueError(f"question hash mismatch: {question_id}")
        label_entry = labels_by_question.get(question_id)
        if not label_entry or label_entry.get("question_sha256") != question_hash:
            raise ValueError(f"reviewed labels do not bind question: {question_id}")

        labels = list(label_entry.get("labels") or [])
        if any(int(item.get("label")) not in (0, 1) for item in labels):
            raise ValueError("reviewed labels must be binary")
        reviewed_ids = {str(item.get("concept_id") or "") for item in labels}
        if not reviewed_ids.issubset(concept_ids):
            raise ValueError("reviewed label is outside candidate vocabulary")
        positive_labels = [item for item in labels if int(item["label"]) == 1]
        positive_ids = {str(item["concept_id"]) for item in positive_labels}

        ranking = score_lexical_question(index, question)
        rank_by_id = {
            str(item["concept_id"]): rank
            for rank, item in enumerate(ranking, start=1)
        }
        score_by_id = {
            str(item["concept_id"]): float(item["score"]) for item in ranking
        }
        metrics = _ranking_metrics(ranking, positive_ids)
        metrics["reviewed_pool_average_precision"] = _average_precision_reviewed_pool(
            score_by_id,
            labels,
        )
        target_partitions = sorted(
            {str(item.get("partition") or "") for item in positive_labels}
        )
        partition = target_partitions[0] if len(target_partitions) == 1 else "mixed"
        full_score_rows = [
            {"concept_id": item["concept_id"], "score": item["score"]}
            for item in ranking
        ]
        question_results.append(
            {
                "question_id": question_id,
                "question_sha256": question_hash,
                "target_partition": partition,
                "positive_concept_ids": sorted(positive_ids),
                "positive_ranks": {
                    concept_id: rank_by_id[concept_id]
                    for concept_id in sorted(positive_ids)
                },
                "positive_scores": {
                    concept_id: score_by_id[concept_id]
                    for concept_id in sorted(positive_ids)
                },
                "reviewed_pool": [
                    {
                        "concept_id": str(item["concept_id"]),
                        "label": int(item["label"]),
                        "score": score_by_id[str(item["concept_id"])],
                        "full_vocabulary_rank": rank_by_id[str(item["concept_id"])],
                    }
                    for item in labels
                ],
                "metrics": metrics,
                "nonzero_candidate_count": sum(
                    float(item["score"]) > 0.0 for item in ranking
                ),
                "full_ranking_sha256": canonical_json_sha256(full_score_rows),
                "top_ranked_concepts": ranking[:DISPLAY_K],
            }
        )

    metric_names = (
        f"recall_at_{EVALUATION_K}",
        f"ndcg_at_{EVALUATION_K}",
        "mrr",
        "reviewed_pool_average_precision",
    )
    aggregate = {
        f"macro_{name}": _mean(
            float(item["metrics"][name]) for item in question_results
        )
        for name in metric_names
    }
    partition_groups: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for item in question_results:
        partition_groups[str(item["target_partition"])].append(item)
    partition_metrics = {
        partition: {
            "question_count": len(items),
            **{
                f"macro_{name}": _mean(
                    float(item["metrics"][name]) for item in items
                )
                for name in metric_names
            },
        }
        for partition, items in sorted(partition_groups.items())
    }
    positive_top_k_count = sum(
        any(rank <= EVALUATION_K for rank in item["positive_ranks"].values())
        for item in question_results
    )
    positive_nonzero_count = sum(
        any(score > 0.0 for score in item["positive_scores"].values())
        for item in question_results
    )
    all_zero_question_count = sum(
        item["nonzero_candidate_count"] == 0 for item in question_results
    )

    artifact = {
        "lexical_baseline_artifact_version": LEXICAL_BASELINE_ARTIFACT_VERSION,
        "phase": PHASE,
        "baseline_id": BASELINE_ID,
        "status": "development_lexical_baseline_completed_not_for_claim",
        "created_at": _validate_created_at(created_at),
        "configuration": {
            "normalization": "unicode_nfkc_casefold_whitespace_collapse",
            "analyzer": "character_ngrams",
            "ngram_range": [MIN_N, MAX_N],
            "term_frequency": "raw_count",
            "idf": "log((1+n_documents)/(1+document_frequency))+1",
            "vector_normalization": "l2",
            "similarity": "cosine",
            "idf_corpus": "sealed_candidate_names_only_without_labels",
            "question_features": "question_text_only",
            "forbidden_question_features": [
                "closed_world_fact",
                "positive_concepts",
                "explicit_negative_concepts",
                "review_decisions",
            ],
            "candidate_scope": "all_eligible_concepts",
            "tie_breaker": "concept_id_ascending",
            "evaluation_k": EVALUATION_K,
            "display_k": DISPLAY_K,
        },
        "bindings": dict(bindings),
        "candidate_count": len(concepts),
        "question_count": len(question_results),
        "aggregate_metrics": aggregate,
        "partition_metrics": partition_metrics,
        "surface_overlap_diagnostic": {
            "positive_nonzero_score_question_count": positive_nonzero_count,
            f"positive_recall_at_{EVALUATION_K}_question_count": positive_top_k_count,
            "all_candidate_scores_zero_question_count": all_zero_question_count,
            "interpretation": (
                "surface_overlap_only_development_diagnostic_not_semantic_"
                "relevance_or_performance_evidence"
            ),
        },
        "questions": question_results,
        "unjudged_policy": (
            "unjudged_concepts_compete_in_full_ranking_but_are_never_supervised_"
            "as_negatives"
        ),
        "database_writes": False,
        "learning_enabled": False,
        "gpu_inference_executed": False,
        "external_api_used": False,
        "model_downloaded": False,
        "lockbox_materialized": False,
        "heldout_gate": False,
        "performance_claim_gate": False,
        "production_promotion_gate": False,
        "next_step": "review_result_then_select_and_pin_frozen_local_embedding_model",
    }
    artifact["lexical_baseline_artifact_sha256"] = canonical_json_sha256(artifact)
    return artifact


def validate_lexical_baseline_artifact(
    artifact: Mapping[str, Any],
    vocabulary: Mapping[str, Any],
    generator_spec: Mapping[str, Any],
    label_pack: Mapping[str, Any],
) -> dict[str, Any]:
    """Recompute the complete artifact and reject any drift or tampering."""

    normalized = dict(artifact)
    supplied = _require_sha256(
        normalized.get("lexical_baseline_artifact_sha256"),
        "lexical_baseline_artifact_sha256",
    )
    unhashed = dict(normalized)
    unhashed.pop("lexical_baseline_artifact_sha256", None)
    if supplied != canonical_json_sha256(unhashed):
        raise ValueError("lexical_baseline_artifact_sha256 mismatch")
    expected = build_lexical_baseline_artifact(
        vocabulary,
        generator_spec,
        label_pack,
        bindings=dict(normalized.get("bindings") or {}),
        created_at=str(normalized.get("created_at") or ""),
    )
    if normalized != expected:
        raise ValueError("lexical baseline artifact does not match bound inputs")
    return normalized

