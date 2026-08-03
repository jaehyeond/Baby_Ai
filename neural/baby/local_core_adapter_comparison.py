"""Compare the frozen Local-Core adapter with its adapter-disabled base model."""

from __future__ import annotations

from datetime import datetime
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
from neural.baby.local_core_conditioning_ablation import (
    _compact_top,
    _comparison,
    _delta_ranking,
    _rank_map,
    _ranked_scores,
    _ranking_summary,
    _score_map,
    _target_diagnostics,
    validate_local_core_conditioning_ablation,
)
from neural.baby.pending_question_semantics import canonical_json_sha256


COMPARISON_VERSION = 1
COMPARISON_STATUS = "local_core_adapter_disabled_comparison_completed_not_for_claim"

_FALSE_GATES = (
    "database_writes",
    "learning_enabled",
    "gradient_enabled",
    "optimizer_enabled",
    "model_save_allowed",
    "calibrator_fit_allowed",
    "heldout_gate",
    "root_cause_claim_gate",
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


def _direct_target_diagnostics(
    targets: Iterable[str],
    concepts: Iterable[Mapping[str, Any]],
    adapter_actual: list[dict[str, Any]],
    base_actual: list[dict[str, Any]],
    base_content_free: list[dict[str, Any]],
    base_shuffled: list[dict[str, Any]],
    base_content_free_delta: list[dict[str, Any]],
    base_shuffle_delta: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_name = {
        _normalize_name(item["concept_name"]): dict(item)
        for item in concepts
    }
    rankings = {
        "adapter_actual": adapter_actual,
        "base_actual": base_actual,
        "base_content_free": base_content_free,
        "base_shuffled": base_shuffled,
        "base_content_free_delta": base_content_free_delta,
        "base_shuffle_delta": base_shuffle_delta,
    }
    rank_maps = {key: _rank_map(rows) for key, rows in rankings.items()}
    score_maps = {key: _score_map(rows) for key, rows in rankings.items()}
    result = []
    for target in targets:
        concept = by_name.get(_normalize_name(target))
        if concept is None:
            result.append({
                "target_concept": target,
                "available_in_candidate_scope": False,
                "concept_id": None,
                "concept_name": None,
                "ranks": None,
                "scores": None,
            })
            continue
        concept_id = str(concept["concept_id"])
        result.append({
            "target_concept": target,
            "available_in_candidate_scope": True,
            "concept_id": concept_id,
            "concept_name": concept["concept_name"],
            "ranks": {
                key: ranks[concept_id] for key, ranks in rank_maps.items()
            },
            "scores": {
                key: scores[concept_id] for key, scores in score_maps.items()
            },
        })
    return result


def _base_target_diagnostics(
    direct: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    diagnostics = []
    for item in direct:
        if not item["available_in_candidate_scope"]:
            diagnostics.append({
                "target_concept": item["target_concept"],
                "available_in_candidate_scope": False,
                "concept_id": None,
            })
            continue
        diagnostics.append({
            "target_concept": item["target_concept"],
            "available_in_candidate_scope": True,
            "concept_id": item["concept_id"],
        })
    return diagnostics


def build_local_core_adapter_comparison(
    manifest: Mapping[str, Any],
    capture: Mapping[str, Any],
    answer_pack: Mapping[str, Any],
    conditioning_ablation: Mapping[str, Any],
    source_concepts: Iterable[Mapping[str, Any]],
    adapter_actual_scores_by_order: Mapping[int, Iterable[Mapping[str, Any]]],
    base_actual_scores_by_order: Mapping[int, Iterable[Mapping[str, Any]]],
    base_content_free_scores_by_order: Mapping[int, Iterable[Mapping[str, Any]]],
    base_shuffled_scores_by_order: Mapping[int, Iterable[Mapping[str, Any]]],
    *,
    predictor_metadata: Mapping[str, Any],
    audited_at: str,
) -> dict[str, Any]:
    """Build a compact base-versus-adapter conditioning comparison."""

    normalized_manifest = validate_exploratory_question_manifest(manifest)
    normalized_capture = validate_exploratory_pre_answer_capture(
        capture, normalized_manifest
    )
    normalized_answers = validate_exploratory_answer_pack(
        answer_pack, normalized_manifest, normalized_capture
    )
    normalized_conditioning = validate_local_core_conditioning_ablation(
        conditioning_ablation,
        normalized_manifest,
        normalized_capture,
        normalized_answers,
    )
    metadata = _clone(predictor_metadata)
    if metadata.get("adapter_sha256") != normalized_capture[
        "local_core_predictor"
    ]["adapter_sha256"]:
        raise ValueError("adapter comparison checkpoint mismatch")
    if metadata.get("adapter_model_snapshot_sha256") != normalized_capture[
        "local_core_predictor"
    ]["model_snapshot_sha256"]:
        raise ValueError("adapter comparison model snapshot mismatch")
    if metadata.get("trainable_parameter_count") != 0:
        raise ValueError("adapter comparison must keep all parameters frozen")
    if metadata.get("adapter_disable_method") != "peft_disable_adapter_context":
        raise ValueError("adapter-disabled base must use the PEFT context manager")
    for field in (
        "base_model_snapshot_sha256",
        "score_implementation_sha256",
        "comparison_implementation_sha256",
    ):
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
        raise ValueError("adapter comparison graph snapshot mismatch")
    eligible, _ = classify_candidate_vocabulary(concepts)

    expected_orders = {item["order"] for item in normalized_manifest["questions"]}
    for label, score_map in (
        ("adapter-actual", adapter_actual_scores_by_order),
        ("base-actual", base_actual_scores_by_order),
        ("base-content-free", base_content_free_scores_by_order),
        ("base-shuffled", base_shuffled_scores_by_order),
    ):
        if {int(order) for order in score_map} != expected_orders:
            raise ValueError(f"{label} score orders do not match manifest")

    question_count = len(normalized_manifest["questions"])
    question_results = []
    base_summary_inputs = []
    adapter_digest_match_count = 0
    for question, captured, answers in zip(
        normalized_manifest["questions"],
        normalized_capture["questions"],
        normalized_answers["questions"],
    ):
        order = int(question["order"])
        shuffled_question = normalized_manifest["questions"][(order + 1) % question_count]
        scoped, _ = exclude_question_cue_surfaces(eligible, question["cue_terms"])
        expected_ids = {item["concept_id"] for item in scoped}
        adapter_actual = _ranked_scores(
            adapter_actual_scores_by_order[order], expected_ids, "adapter-actual"
        )
        base_actual = _ranked_scores(
            base_actual_scores_by_order[order], expected_ids, "base-actual"
        )
        base_content_free = _ranked_scores(
            base_content_free_scores_by_order[order],
            expected_ids,
            "base-content-free",
        )
        base_shuffled = _ranked_scores(
            base_shuffled_scores_by_order[order], expected_ids, "base-shuffled"
        )
        adapter_digest = canonical_json_sha256(adapter_actual)
        if adapter_digest != captured["local_core_full_scores_sha256"]:
            raise ValueError(f"adapter actual score digest drift at order {order}")
        adapter_digest_match_count += 1

        base_content_free_delta = _delta_ranking(base_actual, base_content_free)
        base_shuffle_delta = _delta_ranking(base_actual, base_shuffled)
        direct_targets = _direct_target_diagnostics(
            answers["target_concepts"],
            scoped,
            adapter_actual,
            base_actual,
            base_content_free,
            base_shuffled,
            base_content_free_delta,
            base_shuffle_delta,
        )
        rankings = {
            "base_actual": _compact_top(base_actual),
            "base_content_free": _compact_top(base_content_free),
            "base_shuffled": _compact_top(base_shuffled),
            "base_content_free_delta": _compact_top(base_content_free_delta),
            "base_shuffle_delta": _compact_top(base_shuffle_delta),
            "adapter_actual": _compact_top(adapter_actual),
        }
        question_results.append({
            "order": order,
            "question_id": question["question_id"],
            "question_sha256": question["question_sha256"],
            "candidate_count": len(scoped),
            "shuffled_question_id": shuffled_question["question_id"],
            "score_digests": {
                "adapter_actual": adapter_digest,
                "base_actual": canonical_json_sha256(base_actual),
                "base_content_free": canonical_json_sha256(base_content_free),
                "base_shuffled": canonical_json_sha256(base_shuffled),
            },
            "adapter_vs_base_actual": _comparison(adapter_actual, base_actual),
            "base_actual_vs_content_free": _comparison(
                base_actual, base_content_free
            ),
            "base_actual_vs_shuffled": _comparison(base_actual, base_shuffled),
            "target_diagnostics": direct_targets,
            "rankings": rankings,
        })
        base_summary_inputs.append({
            "question_id": question["question_id"],
            "target_diagnostics": _base_target_diagnostics(direct_targets),
            "rankings": {
                "actual": rankings["base_actual"],
                "content_free": rankings["base_content_free"],
                "shuffled": rankings["base_shuffled"],
                "content_free_delta": rankings["base_content_free_delta"],
                "shuffle_delta": rankings["base_shuffle_delta"],
            },
        })

    base_ranking_summaries = {
        key: _ranking_summary(base_summary_inputs, key)
        for key in (
            "actual",
            "content_free",
            "shuffled",
            "content_free_delta",
            "shuffle_delta",
        )
    }
    base_aggregate = {
        "mean_actual_vs_content_free_spearman": sum(
            item["base_actual_vs_content_free"]["full_rank_spearman"]
            for item in question_results
        ) / question_count,
        "mean_actual_vs_content_free_top_k_jaccard": sum(
            item["base_actual_vs_content_free"]["top_k_jaccard"]
            for item in question_results
        ) / question_count,
        "mean_actual_vs_shuffled_spearman": sum(
            item["base_actual_vs_shuffled"]["full_rank_spearman"]
            for item in question_results
        ) / question_count,
        "mean_actual_vs_shuffled_top_k_jaccard": sum(
            item["base_actual_vs_shuffled"]["top_k_jaccard"]
            for item in question_results
        ) / question_count,
    }
    direct_aggregate = {
        "mean_adapter_vs_base_actual_spearman": sum(
            item["adapter_vs_base_actual"]["full_rank_spearman"]
            for item in question_results
        ) / question_count,
        "mean_adapter_vs_base_actual_top_k_jaccard": sum(
            item["adapter_vs_base_actual"]["top_k_jaccard"]
            for item in question_results
        ) / question_count,
    }

    result = {
        "local_core_adapter_comparison_version": COMPARISON_VERSION,
        "phase": EXPLORATORY_PHASE,
        "status": COMPARISON_STATUS,
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
        "conditioning_ablation_sha256": normalized_conditioning[
            "local_core_conditioning_ablation_sha256"
        ],
        "graph_snapshot_sha256": graph_snapshot_sha256,
        "predictor_metadata": metadata,
        "comparison_contract": {
            "adapter_variant": "current_peft_adapter_enabled",
            "base_variant": "same_loaded_model_with_peft_adapter_disabled",
            "adapter_disable_method": "peft_disable_adapter_context",
            "same_tokenizer": True,
            "same_base_weights": True,
            "same_candidate_scope_per_question": True,
            "same_actual_content_free_shuffle_prompts": True,
            "automatic_winner_selection": False,
        },
        "question_count": question_count,
        "adapter_actual_digest_match_count": adapter_digest_match_count,
        "questions": question_results,
        "adapter_reference": {
            "ranking_summaries": normalized_conditioning["ranking_summaries"],
            "aggregate_comparisons": normalized_conditioning[
                "aggregate_comparisons"
            ],
        },
        "base_ranking_summaries": base_ranking_summaries,
        "base_aggregate_comparisons": base_aggregate,
        "direct_adapter_vs_base": direct_aggregate,
        "adapter_disable_control_gate": True,
        "adapter_actual_reproduction_gate": True,
        "comparison_gate": True,
        "exploratory_only_not_for_claim": True,
        "database_writes": False,
        "learning_enabled": False,
        "gradient_enabled": False,
        "optimizer_enabled": False,
        "model_save_allowed": False,
        "calibrator_fit_allowed": False,
        "heldout_gate": False,
        "root_cause_claim_gate": False,
        "performance_claim_gate": False,
        "production_promotion_gate": False,
        "confirmatory_reuse_allowed": False,
        "block_reasons": [
            "exploratory_questions_were_public_before_capture",
            "target_vocabulary_coverage_is_13_of_32",
            "base_adapter_comparison_is_diagnostic_not_a_heldout_benchmark",
            "no_automatic_winner_rule_was_predeclared",
        ],
        "next_step": (
            "choose_task_aligned_distill_if_base_is_better_or_separate_"
            "relevance_head_if_both_are_weak_without_training_in_this_step"
        ),
    }
    result["local_core_adapter_comparison_sha256"] = canonical_json_sha256(result)
    return validate_local_core_adapter_comparison(
        result,
        normalized_manifest,
        normalized_capture,
        normalized_answers,
        normalized_conditioning,
    )


def validate_local_core_adapter_comparison(
    payload: Mapping[str, Any],
    manifest: Mapping[str, Any],
    capture: Mapping[str, Any],
    answer_pack: Mapping[str, Any],
    conditioning_ablation: Mapping[str, Any],
) -> dict[str, Any]:
    normalized_manifest = validate_exploratory_question_manifest(manifest)
    normalized_capture = validate_exploratory_pre_answer_capture(
        capture, normalized_manifest
    )
    normalized_answers = validate_exploratory_answer_pack(
        answer_pack, normalized_manifest, normalized_capture
    )
    normalized_conditioning = validate_local_core_conditioning_ablation(
        conditioning_ablation,
        normalized_manifest,
        normalized_capture,
        normalized_answers,
    )
    normalized = _clone(payload)
    if normalized.get("local_core_adapter_comparison_version") != COMPARISON_VERSION:
        raise ValueError("unsupported Local-Core adapter comparison version")
    if normalized.get("phase") != EXPLORATORY_PHASE:
        raise ValueError("Local-Core adapter comparison phase mismatch")
    if normalized.get("status") != COMPARISON_STATUS:
        raise ValueError("Local-Core adapter comparison status mismatch")
    if normalized.get("evidence_scope") != EXPLORATORY_EVIDENCE_SCOPE:
        raise ValueError("Local-Core adapter comparison evidence scope mismatch")
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
        "conditioning_ablation_sha256": normalized_conditioning[
            "local_core_conditioning_ablation_sha256"
        ],
        "graph_snapshot_sha256": normalized_capture["graph_snapshot_sha256"],
    }
    for field, expected in bindings.items():
        if normalized.get(field) != expected:
            raise ValueError(f"Local-Core adapter comparison {field} mismatch")
    metadata = dict(normalized.get("predictor_metadata") or {})
    if metadata.get("adapter_sha256") != normalized_capture[
        "local_core_predictor"
    ]["adapter_sha256"]:
        raise ValueError("Local-Core adapter comparison adapter mismatch")
    if metadata.get("adapter_model_snapshot_sha256") != normalized_capture[
        "local_core_predictor"
    ]["model_snapshot_sha256"]:
        raise ValueError("Local-Core adapter comparison snapshot mismatch")
    if metadata.get("trainable_parameter_count") != 0:
        raise ValueError("Local-Core adapter comparison must remain frozen")
    contract = dict(normalized.get("comparison_contract") or {})
    if contract.get("adapter_disable_method") != "peft_disable_adapter_context":
        raise ValueError("Local-Core adapter disable method mismatch")
    if contract.get("automatic_winner_selection") is not False:
        raise ValueError("Local-Core adapter comparison cannot select a winner")

    question_count = len(normalized_manifest["questions"])
    questions = list(normalized.get("questions") or [])
    if normalized.get("question_count") != question_count or len(questions) != question_count:
        raise ValueError("Local-Core adapter comparison question count mismatch")
    if normalized.get("adapter_actual_digest_match_count") != question_count:
        raise ValueError("Local-Core adapter reproduction is incomplete")
    for result, expected, captured in zip(
        questions, normalized_manifest["questions"], normalized_capture["questions"]
    ):
        for field in ("order", "question_id", "question_sha256"):
            if result.get(field) != expected[field]:
                raise ValueError(f"Local-Core adapter comparison {field} mismatch")
        if result.get("score_digests", {}).get("adapter_actual") != captured[
            "local_core_full_scores_sha256"
        ]:
            raise ValueError("Local-Core adapter score digest binding mismatch")
        for ranking in (
            "adapter_actual",
            "base_actual",
            "base_content_free",
            "base_shuffled",
            "base_content_free_delta",
            "base_shuffle_delta",
        ):
            if len(result.get("rankings", {}).get(ranking) or []) != DEFAULT_TOP_K:
                raise ValueError("Local-Core adapter comparison top-k count mismatch")
    for field in (
        "adapter_disable_control_gate",
        "adapter_actual_reproduction_gate",
        "comparison_gate",
        "exploratory_only_not_for_claim",
    ):
        if normalized.get(field) is not True:
            raise ValueError(f"Local-Core adapter comparison {field} must be true")
    if any(normalized.get(field) is not False for field in _FALSE_GATES):
        raise ValueError("Local-Core adapter comparison false gates mismatch")

    supplied = _require_sha256(
        normalized.get("local_core_adapter_comparison_sha256"),
        "local_core_adapter_comparison_sha256",
    )
    unhashed = _clone(normalized)
    unhashed.pop("local_core_adapter_comparison_sha256", None)
    if supplied != canonical_json_sha256(unhashed):
        raise ValueError("Local-Core adapter comparison sha256 mismatch")
    return normalized
