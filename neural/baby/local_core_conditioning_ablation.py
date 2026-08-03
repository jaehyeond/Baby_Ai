"""Read-only diagnostics for Local-Core question conditioning.

The diagnostic compares the sealed question prompt against an empty-question
control and a deterministic cyclic question shuffle on the same candidate set.
It does not fit, calibrate, or promote a model.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from itertools import combinations
import json
import unicodedata
from typing import Any, Iterable, Mapping

from neural.baby.candidate_universe import (
    DEFAULT_TOP_K,
    classify_candidate_vocabulary,
    exclude_question_cue_surfaces,
)
from neural.baby.exploratory_question_probe import (
    EXPLORATORY_EVIDENCE_SCOPE,
    EXPLORATORY_PHASE,
    validate_exploratory_pre_answer_capture,
    validate_exploratory_question_manifest,
)
from neural.baby.exploratory_signal_audit import (
    validate_exploratory_answer_pack,
)
from neural.baby.pending_question_semantics import canonical_json_sha256
from neural.baby.question_calibration import rank_raw_scores


ABLATION_VERSION = 1
ABLATION_STATUS = "local_core_conditioning_ablation_completed_not_for_claim"
CONTENT_FREE_CONTROL = "empty_question_text_same_chat_template"
SHUFFLE_CONTROL = "cyclic_next_question_text_same_candidate_scope"
PRIOR_WARNING_SPEARMAN_THRESHOLD = 0.90
PRIOR_WARNING_TOP_K_JACCARD_THRESHOLD = 0.75

_FALSE_GATES = (
    "database_writes",
    "learning_enabled",
    "gradient_enabled",
    "optimizer_enabled",
    "model_save_allowed",
    "probabilities_computed",
    "calibrator_fit_allowed",
    "heldout_gate",
    "performance_claim_gate",
    "production_promotion_gate",
    "confirmatory_reuse_allowed",
)


def _clone(value: Mapping[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(value, ensure_ascii=False))


def _require_zoned(value: Any, field: str) -> str:
    text = str(value or "")
    if not text:
        raise ValueError(f"{field} must be a non-empty ISO timestamp")
    parsed = datetime.fromisoformat(
        text[:-1] + "+00:00" if text.endswith("Z") else text
    )
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} must include a timezone offset")
    return text


def _require_sha256(value: Any, field: str) -> str:
    text = str(value or "")
    if len(text) != 64 or any(char not in "0123456789abcdef" for char in text):
        raise ValueError(f"{field} must be lowercase hex sha256")
    return text


def _normalize_name(value: Any) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).strip().casefold()
    return " ".join(text.split())


def _ranked_scores(
    rows: Iterable[Mapping[str, Any]],
    expected_ids: set[str],
    label: str,
) -> list[dict[str, Any]]:
    ranked = rank_raw_scores(rows)
    actual_ids = {item["concept_id"] for item in ranked}
    if actual_ids != expected_ids:
        missing = sorted(expected_ids - actual_ids)
        extra = sorted(actual_ids - expected_ids)
        raise ValueError(
            f"{label} candidate IDs mismatch: missing={missing[:3]} extra={extra[:3]}"
        )
    return ranked


def _compact_top(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "concept_id": str(item["concept_id"]),
            "concept_name": str(item["concept_name"]),
            "rank": int(item["rank"]),
            "raw_score": float(item["raw_score"]),
        }
        for item in list(rows)[:DEFAULT_TOP_K]
    ]


def _rank_map(rows: Iterable[Mapping[str, Any]]) -> dict[str, int]:
    return {str(item["concept_id"]): int(item["rank"]) for item in rows}


def _score_map(rows: Iterable[Mapping[str, Any]]) -> dict[str, float]:
    return {str(item["concept_id"]): float(item["raw_score"]) for item in rows}


def _spearman_rank_correlation(
    left: Iterable[Mapping[str, Any]],
    right: Iterable[Mapping[str, Any]],
) -> float:
    left_ranks = _rank_map(left)
    right_ranks = _rank_map(right)
    if set(left_ranks) != set(right_ranks):
        raise ValueError("Spearman inputs must cover the same candidate IDs")
    count = len(left_ranks)
    if count < 2:
        return 1.0
    squared_difference = sum(
        (left_ranks[concept_id] - right_ranks[concept_id]) ** 2
        for concept_id in left_ranks
    )
    return 1.0 - (
        6.0 * squared_difference / (count * (count * count - 1))
    )


def _comparison(
    actual: list[dict[str, Any]],
    control: list[dict[str, Any]],
) -> dict[str, Any]:
    actual_ids = {item["concept_id"] for item in actual[:DEFAULT_TOP_K]}
    control_ids = {item["concept_id"] for item in control[:DEFAULT_TOP_K]}
    actual_scores = _score_map(actual)
    control_scores = _score_map(control)
    absolute_deltas = [
        abs(actual_scores[concept_id] - control_scores[concept_id])
        for concept_id in actual_scores
    ]
    union = actual_ids | control_ids
    return {
        "full_rank_spearman": _spearman_rank_correlation(actual, control),
        "top_k_overlap_count": len(actual_ids & control_ids),
        "top_k_jaccard": len(actual_ids & control_ids) / len(union) if union else 1.0,
        "mean_absolute_score_delta": sum(absolute_deltas) / len(absolute_deltas),
        "max_absolute_score_delta": max(absolute_deltas),
    }


def _delta_ranking(
    actual: list[dict[str, Any]],
    control: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    control_scores = _score_map(control)
    return rank_raw_scores([
        {
            "concept_id": item["concept_id"],
            "concept_name": item["concept_name"],
            "raw_score": float(item["raw_score"])
            - control_scores[item["concept_id"]],
        }
        for item in actual
    ])


def _mean_pairwise_jaccard(top_sets: list[set[str]]) -> float:
    values = [
        len(left & right) / len(left | right) if left | right else 1.0
        for left, right in combinations(top_sets, 2)
    ]
    return sum(values) / len(values) if values else 1.0


def _ranking_summary(
    question_results: Iterable[Mapping[str, Any]],
    ranking_key: str,
) -> dict[str, Any]:
    results = list(question_results)
    top_sets: list[set[str]] = []
    unique_ids: set[str] = set()
    target_hits = 0
    questions_with_hit = 0
    for result in results:
        top_ids = {
            str(item["concept_id"])
            for item in result["rankings"][ranking_key]
        }
        target_ids = {
            str(item["concept_id"])
            for item in result["target_diagnostics"]
            if item["available_in_candidate_scope"]
        }
        hits = top_ids & target_ids
        target_hits += len(hits)
        questions_with_hit += int(bool(hits))
        top_sets.append(top_ids)
        unique_ids.update(top_ids)
    return {
        "top_k_slots": len(results) * DEFAULT_TOP_K,
        "unique_top_k_concept_count": len(unique_ids),
        "mean_pairwise_top_k_jaccard": _mean_pairwise_jaccard(top_sets),
        "exact_target_hit_count": target_hits,
        "questions_with_exact_target_hit": questions_with_hit,
    }


def _target_diagnostics(
    targets: Iterable[str],
    concepts: Iterable[Mapping[str, Any]],
    actual: list[dict[str, Any]],
    content_free: list[dict[str, Any]],
    shuffled: list[dict[str, Any]],
    content_free_delta: list[dict[str, Any]],
    shuffle_delta: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_name = {
        _normalize_name(item["concept_name"]): dict(item)
        for item in concepts
    }
    rankings = {
        "actual": actual,
        "content_free": content_free,
        "shuffled": shuffled,
        "content_free_delta": content_free_delta,
        "shuffle_delta": shuffle_delta,
    }
    rank_maps = {key: _rank_map(rows) for key, rows in rankings.items()}
    score_maps = {key: _score_map(rows) for key, rows in rankings.items()}
    diagnostics = []
    for target in targets:
        concept = by_name.get(_normalize_name(target))
        if concept is None:
            diagnostics.append({
                "target_concept": target,
                "available_in_candidate_scope": False,
                "concept_id": None,
                "concept_name": None,
                "ranks": None,
                "scores": None,
            })
            continue
        concept_id = str(concept["concept_id"])
        diagnostics.append({
            "target_concept": target,
            "available_in_candidate_scope": True,
            "concept_id": concept_id,
            "concept_name": concept["concept_name"],
            "ranks": {
                key: rank_map[concept_id] for key, rank_map in rank_maps.items()
            },
            "scores": {
                "actual": score_maps["actual"][concept_id],
                "content_free": score_maps["content_free"][concept_id],
                "shuffled": score_maps["shuffled"][concept_id],
                "actual_minus_content_free": score_maps["content_free_delta"][concept_id],
                "actual_minus_shuffled": score_maps["shuffle_delta"][concept_id],
            },
        })
    return diagnostics


def build_local_core_conditioning_ablation(
    manifest: Mapping[str, Any],
    capture: Mapping[str, Any],
    answer_pack: Mapping[str, Any],
    source_concepts: Iterable[Mapping[str, Any]],
    actual_scores_by_order: Mapping[int, Iterable[Mapping[str, Any]]],
    content_free_scores_by_order: Mapping[int, Iterable[Mapping[str, Any]]],
    shuffled_scores_by_order: Mapping[int, Iterable[Mapping[str, Any]]],
    *,
    predictor_metadata: Mapping[str, Any],
    audited_at: str,
) -> dict[str, Any]:
    """Build a compact conditioning diagnostic from full-vocabulary scores."""

    normalized_manifest = validate_exploratory_question_manifest(manifest)
    normalized_capture = validate_exploratory_pre_answer_capture(
        capture, normalized_manifest
    )
    normalized_answers = validate_exploratory_answer_pack(
        answer_pack, normalized_manifest, normalized_capture
    )
    metadata = _clone(predictor_metadata)
    if metadata.get("adapter_sha256") != normalized_capture[
        "local_core_predictor"
    ]["adapter_sha256"]:
        raise ValueError("Local-Core adapter does not match exploratory capture")
    if metadata.get("model_snapshot_sha256") != normalized_capture[
        "local_core_predictor"
    ]["model_snapshot_sha256"]:
        raise ValueError("Local-Core model snapshot does not match exploratory capture")
    if metadata.get("trainable_parameter_count") != 0:
        raise ValueError("conditioning ablation must keep Local-Core frozen")
    for field in ("score_implementation_sha256", "ablation_implementation_sha256"):
        _require_sha256(metadata.get(field), field)

    concepts = sorted(
        [
            {"id": str(item.get("id") or ""), "name": str(item.get("name") or "")}
            for item in source_concepts
        ],
        key=lambda item: (item["id"], item["name"]),
    )
    graph_snapshot_sha256 = canonical_json_sha256({"concepts": concepts})
    if graph_snapshot_sha256 != normalized_capture["graph_snapshot_sha256"]:
        raise ValueError("graph snapshot does not match exploratory capture")
    eligible, _ = classify_candidate_vocabulary(concepts)

    expected_orders = {item["order"] for item in normalized_manifest["questions"]}
    for label, score_map in (
        ("actual", actual_scores_by_order),
        ("content-free", content_free_scores_by_order),
        ("shuffled", shuffled_scores_by_order),
    ):
        if {int(order) for order in score_map} != expected_orders:
            raise ValueError(f"{label} score orders do not match manifest")

    question_count = len(normalized_manifest["questions"])
    question_results = []
    actual_digest_match_count = 0
    for question, captured, answers in zip(
        normalized_manifest["questions"],
        normalized_capture["questions"],
        normalized_answers["questions"],
    ):
        order = int(question["order"])
        shuffled_order = (order + 1) % question_count
        shuffled_question = normalized_manifest["questions"][shuffled_order]
        scoped, _ = exclude_question_cue_surfaces(eligible, question["cue_terms"])
        expected_ids = {item["concept_id"] for item in scoped}
        actual = _ranked_scores(actual_scores_by_order[order], expected_ids, "actual")
        content_free = _ranked_scores(
            content_free_scores_by_order[order], expected_ids, "content-free"
        )
        shuffled = _ranked_scores(
            shuffled_scores_by_order[order], expected_ids, "shuffled"
        )
        actual_digest = canonical_json_sha256(actual)
        if actual_digest != captured["local_core_full_scores_sha256"]:
            raise ValueError(f"actual Local-Core score digest drift at order {order}")
        actual_digest_match_count += 1

        content_free_delta = _delta_ranking(actual, content_free)
        shuffle_delta = _delta_ranking(actual, shuffled)
        diagnostics = _target_diagnostics(
            answers["target_concepts"],
            scoped,
            actual,
            content_free,
            shuffled,
            content_free_delta,
            shuffle_delta,
        )
        question_results.append({
            "order": order,
            "question_id": question["question_id"],
            "question": question["question"],
            "question_sha256": question["question_sha256"],
            "candidate_count": len(scoped),
            "content_free_control": CONTENT_FREE_CONTROL,
            "shuffled_question_order": shuffled_order,
            "shuffled_question_id": shuffled_question["question_id"],
            "shuffled_question_sha256": shuffled_question["question_sha256"],
            "score_digests": {
                "actual": actual_digest,
                "content_free": canonical_json_sha256(content_free),
                "shuffled": canonical_json_sha256(shuffled),
            },
            "actual_vs_content_free": _comparison(actual, content_free),
            "actual_vs_shuffled": _comparison(actual, shuffled),
            "target_diagnostics": diagnostics,
            "rankings": {
                "actual": _compact_top(actual),
                "content_free": _compact_top(content_free),
                "shuffled": _compact_top(shuffled),
                "content_free_delta": _compact_top(content_free_delta),
                "shuffle_delta": _compact_top(shuffle_delta),
            },
        })

    mean_content_free_spearman = sum(
        item["actual_vs_content_free"]["full_rank_spearman"]
        for item in question_results
    ) / question_count
    mean_content_free_jaccard = sum(
        item["actual_vs_content_free"]["top_k_jaccard"]
        for item in question_results
    ) / question_count
    mean_shuffle_spearman = sum(
        item["actual_vs_shuffled"]["full_rank_spearman"]
        for item in question_results
    ) / question_count
    mean_shuffle_jaccard = sum(
        item["actual_vs_shuffled"]["top_k_jaccard"]
        for item in question_results
    ) / question_count

    result = {
        "local_core_conditioning_ablation_version": ABLATION_VERSION,
        "phase": EXPLORATORY_PHASE,
        "status": ABLATION_STATUS,
        "evidence_scope": EXPLORATORY_EVIDENCE_SCOPE,
        "audited_at": _require_zoned(audited_at, "audited_at"),
        "manifest_snapshot_sha256": normalized_manifest[
            "manifest_snapshot_sha256"
        ],
        "exploratory_pre_answer_capture_sha256": normalized_capture[
            "exploratory_pre_answer_capture_sha256"
        ],
        "exploratory_answer_pack_sha256": normalized_answers[
            "exploratory_answer_pack_sha256"
        ],
        "graph_snapshot_sha256": graph_snapshot_sha256,
        "predictor_metadata": metadata,
        "control_contract": {
            "content_free_control": CONTENT_FREE_CONTROL,
            "content_free_question_text": "",
            "shuffle_control": SHUFFLE_CONTROL,
            "shuffle_offset": 1,
            "same_candidate_scope_per_question": True,
            "warning_spearman_threshold": PRIOR_WARNING_SPEARMAN_THRESHOLD,
            "warning_top_k_jaccard_threshold": PRIOR_WARNING_TOP_K_JACCARD_THRESHOLD,
        },
        "question_count": question_count,
        "actual_digest_match_count": actual_digest_match_count,
        "questions": question_results,
        "ranking_summaries": {
            key: _ranking_summary(question_results, key)
            for key in (
                "actual",
                "content_free",
                "shuffled",
                "content_free_delta",
                "shuffle_delta",
            )
        },
        "aggregate_comparisons": {
            "mean_actual_vs_content_free_spearman": mean_content_free_spearman,
            "mean_actual_vs_content_free_top_k_jaccard": mean_content_free_jaccard,
            "mean_actual_vs_shuffled_spearman": mean_shuffle_spearman,
            "mean_actual_vs_shuffled_top_k_jaccard": mean_shuffle_jaccard,
        },
        "diagnostic_warnings": {
            "content_free_prior_dominance": (
                mean_content_free_spearman >= PRIOR_WARNING_SPEARMAN_THRESHOLD
                and mean_content_free_jaccard >= PRIOR_WARNING_TOP_K_JACCARD_THRESHOLD
            ),
            "question_shuffle_insensitivity": (
                mean_shuffle_spearman >= PRIOR_WARNING_SPEARMAN_THRESHOLD
                and mean_shuffle_jaccard >= PRIOR_WARNING_TOP_K_JACCARD_THRESHOLD
            ),
        },
        "actual_score_reproduction_gate": True,
        "conditioning_ablation_gate": True,
        "exploratory_only_not_for_claim": True,
        "database_writes": False,
        "learning_enabled": False,
        "gradient_enabled": False,
        "optimizer_enabled": False,
        "model_save_allowed": False,
        "probabilities_computed": False,
        "calibrator_fit_allowed": False,
        "heldout_gate": False,
        "performance_claim_gate": False,
        "production_promotion_gate": False,
        "confirmatory_reuse_allowed": False,
        "block_reasons": [
            "exploratory_questions_were_public_before_capture",
            "controls_are_diagnostic_not_a_heldout_benchmark",
            "warning_thresholds_are_engineering_heuristics_not_inferential_tests",
        ],
        "next_step": (
            "separate_prompt_prior_correction_from_training_then_address_"
            "vocabulary_coverage_and_wake_behavior_wiring"
        ),
    }
    result["local_core_conditioning_ablation_sha256"] = canonical_json_sha256(
        result
    )
    return validate_local_core_conditioning_ablation(
        result, normalized_manifest, normalized_capture, normalized_answers
    )


def validate_local_core_conditioning_ablation(
    payload: Mapping[str, Any],
    manifest: Mapping[str, Any],
    capture: Mapping[str, Any],
    answer_pack: Mapping[str, Any],
) -> dict[str, Any]:
    normalized_manifest = validate_exploratory_question_manifest(manifest)
    normalized_capture = validate_exploratory_pre_answer_capture(
        capture, normalized_manifest
    )
    normalized_answers = validate_exploratory_answer_pack(
        answer_pack, normalized_manifest, normalized_capture
    )
    normalized = _clone(payload)
    if normalized.get("local_core_conditioning_ablation_version") != ABLATION_VERSION:
        raise ValueError("unsupported Local-Core conditioning ablation version")
    if normalized.get("phase") != EXPLORATORY_PHASE:
        raise ValueError("Local-Core conditioning ablation phase mismatch")
    if normalized.get("status") != ABLATION_STATUS:
        raise ValueError("Local-Core conditioning ablation status mismatch")
    if normalized.get("evidence_scope") != EXPLORATORY_EVIDENCE_SCOPE:
        raise ValueError("Local-Core conditioning ablation evidence scope mismatch")
    _require_zoned(normalized.get("audited_at"), "audited_at")
    bindings = {
        "manifest_snapshot_sha256": normalized_manifest[
            "manifest_snapshot_sha256"
        ],
        "exploratory_pre_answer_capture_sha256": normalized_capture[
            "exploratory_pre_answer_capture_sha256"
        ],
        "exploratory_answer_pack_sha256": normalized_answers[
            "exploratory_answer_pack_sha256"
        ],
        "graph_snapshot_sha256": normalized_capture["graph_snapshot_sha256"],
    }
    for field, expected in bindings.items():
        if normalized.get(field) != expected:
            raise ValueError(f"Local-Core conditioning ablation {field} mismatch")
    metadata = dict(normalized.get("predictor_metadata") or {})
    if metadata.get("adapter_sha256") != normalized_capture[
        "local_core_predictor"
    ]["adapter_sha256"]:
        raise ValueError("Local-Core conditioning ablation adapter mismatch")
    if metadata.get("model_snapshot_sha256") != normalized_capture[
        "local_core_predictor"
    ]["model_snapshot_sha256"]:
        raise ValueError("Local-Core conditioning ablation model snapshot mismatch")
    if metadata.get("trainable_parameter_count") != 0:
        raise ValueError("Local-Core conditioning ablation must remain frozen")
    for field in ("score_implementation_sha256", "ablation_implementation_sha256"):
        _require_sha256(metadata.get(field), field)
    control = dict(normalized.get("control_contract") or {})
    if control.get("content_free_control") != CONTENT_FREE_CONTROL:
        raise ValueError("content-free control contract mismatch")
    if control.get("content_free_question_text") != "":
        raise ValueError("content-free question must remain empty")
    if control.get("shuffle_control") != SHUFFLE_CONTROL:
        raise ValueError("shuffle control contract mismatch")
    if control.get("shuffle_offset") != 1:
        raise ValueError("shuffle offset mismatch")

    question_count = len(normalized_manifest["questions"])
    questions = list(normalized.get("questions") or [])
    if normalized.get("question_count") != question_count or len(questions) != question_count:
        raise ValueError("Local-Core conditioning ablation question count mismatch")
    if normalized.get("actual_digest_match_count") != question_count:
        raise ValueError("Local-Core actual score reproduction is incomplete")
    for result, expected, captured in zip(
        questions, normalized_manifest["questions"], normalized_capture["questions"]
    ):
        for field in ("order", "question_id", "question", "question_sha256"):
            if result.get(field) != expected[field]:
                raise ValueError(f"Local-Core conditioning ablation {field} mismatch")
        if result.get("score_digests", {}).get("actual") != captured[
            "local_core_full_scores_sha256"
        ]:
            raise ValueError("Local-Core actual score digest binding mismatch")
        for ranking in (
            "actual",
            "content_free",
            "shuffled",
            "content_free_delta",
            "shuffle_delta",
        ):
            if len(result.get("rankings", {}).get(ranking) or []) != DEFAULT_TOP_K:
                raise ValueError("Local-Core conditioning top-k count mismatch")
    if normalized.get("actual_score_reproduction_gate") is not True:
        raise ValueError("Local-Core actual reproduction gate must be true")
    if normalized.get("conditioning_ablation_gate") is not True:
        raise ValueError("Local-Core conditioning ablation gate must be true")
    if normalized.get("exploratory_only_not_for_claim") is not True:
        raise ValueError("Local-Core conditioning ablation must remain exploratory")
    if any(normalized.get(field) is not False for field in _FALSE_GATES):
        raise ValueError("Local-Core conditioning ablation false gates mismatch")

    supplied = _require_sha256(
        normalized.get("local_core_conditioning_ablation_sha256"),
        "local_core_conditioning_ablation_sha256",
    )
    unhashed = _clone(normalized)
    unhashed.pop("local_core_conditioning_ablation_sha256", None)
    if supplied != canonical_json_sha256(unhashed):
        raise ValueError("Local-Core conditioning ablation sha256 mismatch")
    return normalized
