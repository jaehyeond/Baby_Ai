"""Pure, fail-closed contract for a task-aligned relevance scorer.

The contract separates training labels, graph-vocabulary generalization, and
future question holdouts.  It does not import a model runtime, access Neo4j,
fit weights, or convert exploratory results into performance evidence.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from typing import Any, Mapping

from neural.baby.candidate_universe import (
    validate_candidate_vocabulary,
    validate_independent_score_capture,
    validate_union_label_pack,
)
from neural.baby.pending_question_semantics import canonical_json_sha256


RELEVANCE_SCORER_CONTRACT_VERSION = 1
PHASE = "J1-R1"
STATUS = "task_aligned_relevance_scorer_contract_defined_future_data_blocked"
VOCABULARY_PARTITION_SALT = "j1-r1-graph-vocabulary-v1"
VOCABULARY_PARTITIONS = (
    ("fit_pool", 0, 79),
    ("development_challenge_pool", 80, 89),
    ("lockbox_challenge_pool", 90, 99),
)
BASELINE_ORDER = (
    "lexical_char_ngram_tfidf_v1",
    "frozen_local_embedding_cosine_v1",
    "task_aligned_relevance_head_v1",
)
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _clone(value: Mapping[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(value, ensure_ascii=False))


def _validate_zoned_timestamp(value: Any, field: str) -> str:
    raw = str(value or "").strip()
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} must include a timezone")
    return raw


def _require_sha256(value: Any, field: str) -> str:
    raw = str(value or "")
    if not _SHA256_RE.fullmatch(raw):
        raise ValueError(f"{field} must be a lowercase SHA-256")
    return raw


def graph_vocabulary_partition(concept_id: str) -> str:
    """Assign a concept ID to an immutable 80/10/10 challenge partition."""

    normalized = str(concept_id or "").strip()
    if not normalized:
        raise ValueError("concept_id is required for vocabulary partitioning")
    digest = hashlib.sha256(
        f"{VOCABULARY_PARTITION_SALT}\0{normalized}".encode("utf-8")
    ).hexdigest()
    bucket = int(digest[:8], 16) % 100
    for name, lower, upper in VOCABULARY_PARTITIONS:
        if lower <= bucket <= upper:
            return name
    raise AssertionError("vocabulary partition ranges must cover every bucket")


def _partition_summary(concepts: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, str]]] = {
        name: [] for name, _, _ in VOCABULARY_PARTITIONS
    }
    normalized_names: dict[str, set[str]] = defaultdict(set)
    for concept in concepts:
        concept_id = str(concept["concept_id"])
        concept_name = str(concept["concept_name"])
        partition = graph_vocabulary_partition(concept_id)
        grouped[partition].append({
            "concept_id": concept_id,
            "concept_name": concept_name,
        })
        normalized_names[concept_name.strip().casefold()].add(concept_id)

    partitions = []
    for name, lower, upper in VOCABULARY_PARTITIONS:
        rows = sorted(grouped[name], key=lambda item: item["concept_id"])
        partitions.append({
            "partition": name,
            "bucket_range_inclusive": [lower, upper],
            "concept_count": len(rows),
            "concept_snapshot_sha256": canonical_json_sha256(rows),
        })
    return {
        "partition_count": len(partitions),
        "partitions": partitions,
        "exact_normalized_name_collision_count": sum(
            len(ids) > 1 for ids in normalized_names.values()
        ),
        "semantic_alias_audit_completed": False,
        "semantic_disjoint_claim_gate": False,
    }


def _legacy_label_summary(
    vocabulary: Mapping[str, Any],
    labels: Mapping[str, Any],
) -> dict[str, Any]:
    vocabulary_by_id = {
        str(item["concept_id"]): str(item["concept_name"])
        for item in vocabulary["eligible_concepts"]
    }
    decision_counts: Counter[str] = Counter()
    questions_by_concept: dict[str, set[str]] = defaultdict(set)
    rows_by_partition: Counter[str] = Counter()
    fit_decisions: Counter[str] = Counter()
    question_ids: list[str] = []

    for entry in labels["entries"]:
        question_id = str(entry["question_id"])
        question_ids.append(question_id)
        for label in entry["labels"]:
            concept_id = str(label["concept_id"])
            concept_name = str(label["concept_name"])
            if vocabulary_by_id.get(concept_id) != concept_name:
                raise ValueError("reviewed label is outside the sealed graph vocabulary")
            decision = str(label["decision"])
            decision_counts[decision] += 1
            questions_by_concept[concept_id].add(question_id)
            partition = graph_vocabulary_partition(concept_id)
            rows_by_partition[partition] += 1
            if partition == "fit_pool" and decision in {"approved", "rejected"}:
                fit_decisions[decision] += 1

    question_ids_sorted = sorted(question_ids)
    fit_row_count = fit_decisions["approved"] + fit_decisions["rejected"]
    if not question_ids_sorted or len(question_ids_sorted) != len(set(question_ids_sorted)):
        raise ValueError("legacy label questions must be unique")
    if not fit_decisions["approved"] or not fit_decisions["rejected"]:
        raise ValueError("fit_pool requires reviewed positive and negative rows")
    return {
        "scope": "legacy_exploratory_train_only",
        "question_count": len(question_ids_sorted),
        "question_set_sha256": canonical_json_sha256(question_ids_sorted),
        "label_row_count": sum(decision_counts.values()),
        "positive_count": decision_counts["approved"],
        "negative_count": decision_counts["rejected"],
        "excluded_uncertain_count": decision_counts["uncertain"],
        "binary_row_count": decision_counts["approved"] + decision_counts["rejected"],
        "unique_labeled_concept_count": len(questions_by_concept),
        "concepts_repeated_across_questions": sum(
            len(question_ids) > 1 for question_ids in questions_by_concept.values()
        ),
        "labeled_rows_by_vocabulary_partition": {
            name: rows_by_partition[name] for name, _, _ in VOCABULARY_PARTITIONS
        },
        "supervised_fit_pool": {
            "row_count": fit_row_count,
            "positive_count": fit_decisions["approved"],
            "negative_count": fit_decisions["rejected"],
        },
        "reserved_partition_binary_rows_excluded_from_fit": (
            decision_counts["approved"]
            + decision_counts["rejected"]
            - fit_row_count
        ),
        "heldout_use_allowed": False,
        "performance_claim_allowed": False,
    }


def _build_contract_body(
    vocabulary: Mapping[str, Any],
    capture: Mapping[str, Any],
    answer_pack: Mapping[str, Any],
    label_pack: Mapping[str, Any],
    *,
    created_at: str,
) -> dict[str, Any]:
    validated_vocabulary = validate_candidate_vocabulary(vocabulary)
    validated_capture = validate_independent_score_capture(
        validated_vocabulary, capture
    )
    validated_labels = validate_union_label_pack(
        validated_capture,
        answer_pack,
        label_pack,
        require_user_review=True,
    )
    created_at = _validate_zoned_timestamp(created_at, "created_at")
    vocabulary_summary = _partition_summary(
        list(validated_vocabulary["eligible_concepts"])
    )
    legacy_summary = _legacy_label_summary(
        validated_vocabulary, validated_labels
    )

    return {
        "relevance_scorer_contract_version": RELEVANCE_SCORER_CONTRACT_VERSION,
        "phase": PHASE,
        "status": STATUS,
        "created_at": created_at,
        "input_bindings": {
            "candidate_vocabulary_sha256": _require_sha256(
                validated_vocabulary["candidate_vocabulary_sha256"],
                "candidate_vocabulary_sha256",
            ),
            "independent_score_capture_sha256": _require_sha256(
                validated_capture["independent_score_capture_sha256"],
                "independent_score_capture_sha256",
            ),
            "reviewed_reference_answer_pack_sha256": _require_sha256(
                answer_pack["reference_answer_pack_sha256"],
                "reviewed_reference_answer_pack_sha256",
            ),
            "union_label_pack_sha256": _require_sha256(
                validated_labels["union_label_pack_sha256"],
                "union_label_pack_sha256",
            ),
        },
        "objective_contract": {
            "unit": "question_concept_pair",
            "objective": "binary_direct_answer_relevance_ranking",
            "positive_definition": (
                "user_reviewed_approved_direct_or_answer_bearing_concept"
            ),
            "negative_definition": "user_reviewed_rejected_candidate_only",
            "label_mapping": {
                "approved": 1,
                "rejected": 0,
                "uncertain": None,
            },
            "uncertain_policy": "exclude_from_fit_and_metrics",
            "unlabeled_graph_concept_policy": "never_assume_negative",
            "automatic_random_negative_labeling_allowed": False,
            "evaluation_candidate_scope": "full_eligible_graph_vocabulary",
            "probability_claim_scope": "forbidden_without_exhaustive_reviewed_pairs",
        },
        "legacy_data": legacy_summary,
        "graph_vocabulary_split": {
            "partition_key": "sha256(partition_salt_null_concept_id)_mod_100",
            "partition_salt": VOCABULARY_PARTITION_SALT,
            "assignment_precedes_labels_and_model_scores": True,
            "candidate_universe_constant_across_systems": True,
            "candidate_universe_filtered_by_partition_at_inference": False,
            "exact_concept_id_overlap_allowed_in_concept_disjoint_metric": False,
            "question_split_and_concept_split_are_separate_axes": True,
            **vocabulary_summary,
        },
        "split_contract": {
            "row_random_split_allowed": False,
            "primary_generalization_axis": "future_question_and_capture_time",
            "secondary_generalization_axis": "concept_partition_stratified_metrics",
            "legacy_train": {
                "question_scope": "existing_six_public_questions",
                "model_selection_allowed": True,
                "heldout_or_performance_use_allowed": False,
            },
            "future_development": {
                "manifest_required": True,
                "manifest_required_before_any_baseline_execution": True,
                "question_hash_overlap_with_legacy_allowed": False,
                "capture_after_contract_required": True,
                "answers_and_labels_fixed_before_predictor_output_reveal": True,
                "model_selection_allowed": True,
                "performance_claim_allowed": False,
                "sample_size_plan_required": True,
            },
            "future_lockbox": {
                "manifest_required_before_any_baseline_execution": True,
                "manifest_required_before_first_supervised_relevance_fit": True,
                "question_hash_overlap_with_train_or_development_allowed": False,
                "answers_and_labels_hidden_until_model_and_baselines_frozen": True,
                "model_selection_allowed": False,
                "one_time_open_required": True,
                "sample_size_plan_required": True,
            },
        },
        "baseline_ladder": {
            "execution_order": list(BASELINE_ORDER),
            "lexical_char_ngram_tfidf_v1": {
                "supervised_label_fit": False,
                "features": "unicode_normalized_character_ngrams_2_to_5",
                "idf_corpus": "sealed_candidate_text_only",
                "concept_text": "canonical_concept_name_v1",
                "external_api_allowed": False,
                "legacy_exploratory_execution_allowed": True,
            },
            "frozen_local_embedding_cosine_v1": {
                "requires_lexical_artifact": True,
                "provider": "local_only_no_paid_api",
                "model_id_required": True,
                "model_revision_required": True,
                "weight_snapshot_sha256_required": True,
                "prompt_template_hash_required": True,
                "supervised_label_fit": False,
            },
            "task_aligned_relevance_head_v1": {
                "requires_lexical_and_embedding_artifacts": True,
                "training_rows": "reviewed_binary_rows_in_fit_pool_only",
                "negative_source": "reviewed_rejected_only",
                "preferred_first_architecture": "frozen_encoder_plus_small_projection_head",
                "full_causal_lm_replay_allowed": False,
                "checkpoint_versioning_and_rollback_required": True,
            },
        },
        "evaluation_contract": {
            "primary_metrics": [
                "macro_question_recall_at_8",
                "macro_question_ndcg_at_8",
            ],
            "secondary_metrics": [
                "macro_question_mrr",
                "reviewed_pool_average_precision",
            ],
            "calibration_metrics": ["brier", "log_loss", "ece"],
            "calibration_metrics_gate": False,
            "calibration_gate_reason": "exhaustive_reviewed_pair_labels_missing",
            "resampling_unit": "question",
            "paired_system_comparison_required": True,
            "micro_row_only_claim_allowed": False,
            "report_seen_and_concept_challenge_strata_separately": True,
        },
        "readiness": {
            "reviewed_binary_label_gate": True,
            "graph_vocabulary_split_gate": True,
            "legacy_train_only_gate": True,
            "future_development_manifest_gate": False,
            "future_lockbox_manifest_gate": False,
            "lexical_baseline_implementation_gate": True,
            "lexical_baseline_execution_gate": False,
            "embedding_baseline_execution_gate": False,
            "learned_head_fit_gate": False,
            "heldout_gate": False,
            "performance_claim_gate": False,
            "production_promotion_gate": False,
            "block_reasons": [
                "future_development_manifest_missing",
                "future_lockbox_manifest_missing",
                "lexical_baseline_artifact_missing",
                "local_embedding_model_snapshot_missing",
                "semantic_alias_audit_missing_for_semantic_disjoint_claim",
            ],
        },
        "database_writes": False,
        "learning_enabled": False,
        "model_downloads": False,
        "model_weights_changed": False,
        "next_step": (
            "prepare_future_development_and_lockbox_manifests_then_run_"
            "legacy_train_only_lexical_baseline"
        ),
    }


def build_relevance_scorer_contract(
    vocabulary: Mapping[str, Any],
    capture: Mapping[str, Any],
    answer_pack: Mapping[str, Any],
    label_pack: Mapping[str, Any],
    *,
    created_at: str,
) -> dict[str, Any]:
    body = _build_contract_body(
        vocabulary,
        capture,
        answer_pack,
        label_pack,
        created_at=created_at,
    )
    body["relevance_scorer_contract_sha256"] = canonical_json_sha256(body)
    return body


def validate_relevance_scorer_contract(
    artifact: Mapping[str, Any],
    vocabulary: Mapping[str, Any],
    capture: Mapping[str, Any],
    answer_pack: Mapping[str, Any],
    label_pack: Mapping[str, Any],
) -> dict[str, Any]:
    normalized = _clone(artifact)
    supplied_hash = _require_sha256(
        normalized.get("relevance_scorer_contract_sha256"),
        "relevance_scorer_contract_sha256",
    )
    unhashed = _clone(normalized)
    unhashed.pop("relevance_scorer_contract_sha256", None)
    if supplied_hash != canonical_json_sha256(unhashed):
        raise ValueError("relevance_scorer_contract_sha256 mismatch")
    expected = build_relevance_scorer_contract(
        vocabulary,
        capture,
        answer_pack,
        label_pack,
        created_at=str(normalized.get("created_at") or ""),
    )
    if normalized != expected:
        raise ValueError("relevance scorer contract does not match bound inputs")
    return normalized
