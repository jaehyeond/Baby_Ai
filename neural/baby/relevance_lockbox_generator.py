"""One-time lockbox generator contracts for J1-R2 relevance evaluation.

This module fixes the generator distribution without exposing question
instances. Exact questions are sampled only after a model cutoff is sealed,
from an independently reviewed source bank stored outside the repository.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from typing import Any, Mapping

from neural.baby.pending_question_semantics import canonical_json_sha256
from neural.baby.relevance_cohort_lifecycle import (
    PHASE,
    seal_cohort_manifest,
    validate_cohort_manifest,
)


LOCKBOX_SAMPLE_SIZE_PLAN_VERSION = 1
LOCKBOX_GENERATOR_SPEC_VERSION = 1
LOCKBOX_REVIEW_PACKET_VERSION = 1
LOCKBOX_REVIEW_DECISIONS_VERSION = 1
LOCKBOX_GENERATOR_ID = "j1-r2-private-source-hidden-seed-v1"
EXPECTED_QUESTION_COUNT = 24
EXPLICIT_NEGATIVES_PER_QUESTION = 3
MINIMUM_PRIVATE_SOURCE_BANK_SIZE = 48
MINIMUM_PRIVATE_SOURCE_ITEMS_PER_PARTITION = 16
EXPECTED_PARTITION_COUNTS = {
    "fit_pool": 8,
    "development_challenge_pool": 8,
    "lockbox_challenge_pool": 8,
}
REVIEW_ITEM_IDS = (
    "sample_size_and_partition_balance",
    "private_source_bank_and_independent_truth",
    "post_cutoff_hidden_seed_and_commitment",
    "one_time_non_reusable_usage",
)
SEED_COMMITMENT_DOMAIN = "j1-r2-lockbox-v1"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _clone(value: Mapping[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(value, ensure_ascii=False))


def _require_sha256(value: Any, field: str) -> str:
    raw = str(value or "")
    if not _SHA256_RE.fullmatch(raw):
        raise ValueError(f"{field} must be a lowercase SHA-256")
    return raw


def _zoned_timestamp(value: Any, field: str) -> str:
    raw = str(value or "").strip()
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} must include a timezone")
    return raw


def _validate_lifecycle(lifecycle: Mapping[str, Any]) -> dict[str, Any]:
    normalized = _clone(lifecycle)
    if normalized.get("phase") != PHASE:
        raise ValueError("lockbox lifecycle phase must be J1-R2")
    supplied = _require_sha256(
        normalized.get("cohort_lifecycle_contract_sha256"),
        "cohort_lifecycle_contract_sha256",
    )
    unhashed = _clone(normalized)
    unhashed.pop("cohort_lifecycle_contract_sha256", None)
    if supplied != canonical_json_sha256(unhashed):
        raise ValueError("cohort lifecycle contract hash mismatch")
    role = dict(normalized.get("cohort_roles") or {}).get("one_time_lockbox")
    if not isinstance(role, dict):
        raise ValueError("lifecycle is missing the one-time lockbox role")
    required_role_policies = {
        "generator_contract_fixed_before_baseline_output": True,
        "hidden_seed_required": True,
        "instances_generated_after_model_freeze": True,
        "model_selection_allowed": False,
        "one_time_open": True,
        "plaintext_questions_in_repository_allowed": False,
        "reusable": False,
    }
    if any(role.get(key) is not value for key, value in required_role_policies.items()):
        raise ValueError("lifecycle lockbox policies do not match this generator")
    return normalized


def build_lockbox_sample_size_plan(
    lifecycle: Mapping[str, Any],
    *,
    created_at: str,
) -> dict[str, Any]:
    lifecycle = _validate_lifecycle(lifecycle)
    plan = {
        "lockbox_sample_size_plan_version": LOCKBOX_SAMPLE_SIZE_PLAN_VERSION,
        "phase": PHASE,
        "role": "one_time_lockbox",
        "status": "proposed_descriptive_lockbox_plan_awaiting_user_review",
        "created_at": _zoned_timestamp(created_at, "created_at"),
        "cohort_lifecycle_contract_sha256": lifecycle[
            "cohort_lifecycle_contract_sha256"
        ],
        "evaluation_epoch_id": lifecycle["evaluation_epoch"][
            "evaluation_epoch_id"
        ],
        "question_count": EXPECTED_QUESTION_COUNT,
        "positive_label_count": EXPECTED_QUESTION_COUNT,
        "explicit_negative_label_count": (
            EXPECTED_QUESTION_COUNT * EXPLICIT_NEGATIVES_PER_QUESTION
        ),
        "explicit_negatives_per_question": EXPLICIT_NEGATIVES_PER_QUESTION,
        "target_partition_counts": EXPECTED_PARTITION_COUNTS,
        "sampling_without_replacement": True,
        "minimum_private_source_bank_size": MINIMUM_PRIVATE_SOURCE_BANK_SIZE,
        "minimum_private_source_items_per_partition": (
            MINIMUM_PRIVATE_SOURCE_ITEMS_PER_PARTITION
        ),
        "unlabeled_graph_concept_policy": "ignore_never_assume_negative",
        "usage": {
            "one_time_open": True,
            "reusable": False,
            "model_selection_allowed": False,
            "heldout_diagnostic_allowed": True,
            "inferential_claim_allowed": False,
            "performance_claim_allowed": False,
            "sample_size_interpretation": (
                "balanced_implementation_diagnostic_not_statistical_power"
            ),
        },
        "database_writes": False,
        "learning_enabled": False,
        "heldout_gate": False,
        "performance_claim_gate": False,
        "production_promotion_gate": False,
    }
    plan["lockbox_sample_size_plan_sha256"] = canonical_json_sha256(plan)
    return plan


def validate_lockbox_sample_size_plan(
    payload: Mapping[str, Any],
    lifecycle: Mapping[str, Any],
) -> dict[str, Any]:
    normalized = _clone(payload)
    supplied = _require_sha256(
        normalized.get("lockbox_sample_size_plan_sha256"),
        "lockbox_sample_size_plan_sha256",
    )
    unhashed = _clone(normalized)
    unhashed.pop("lockbox_sample_size_plan_sha256", None)
    if supplied != canonical_json_sha256(unhashed):
        raise ValueError("lockbox_sample_size_plan_sha256 mismatch")
    expected = build_lockbox_sample_size_plan(
        lifecycle,
        created_at=str(normalized.get("created_at") or ""),
    )
    if normalized != expected:
        raise ValueError("lockbox sample-size plan does not match contract")
    return normalized


def build_lockbox_generator_spec(
    lifecycle: Mapping[str, Any],
    sample_size_plan: Mapping[str, Any],
    *,
    candidate_vocabulary_sha256: str,
    implementation_sha256: str,
    created_at: str,
) -> dict[str, Any]:
    lifecycle = _validate_lifecycle(lifecycle)
    plan = validate_lockbox_sample_size_plan(sample_size_plan, lifecycle)
    vocabulary_hash = _require_sha256(
        candidate_vocabulary_sha256, "candidate_vocabulary_sha256"
    )
    if vocabulary_hash != lifecycle["evaluation_epoch"][
        "candidate_vocabulary_sha256"
    ]:
        raise ValueError("candidate vocabulary does not match evaluation epoch")
    implementation_hash = _require_sha256(
        implementation_sha256, "implementation_sha256"
    )
    spec = {
        "lockbox_generator_spec_version": LOCKBOX_GENERATOR_SPEC_VERSION,
        "phase": PHASE,
        "role": "one_time_lockbox",
        "generator_id": LOCKBOX_GENERATOR_ID,
        "status": "generator_distribution_defined_awaiting_user_review",
        "created_at": _zoned_timestamp(created_at, "created_at"),
        "input_bindings": {
            "cohort_lifecycle_contract_sha256": lifecycle[
                "cohort_lifecycle_contract_sha256"
            ],
            "evaluation_epoch_id": lifecycle["evaluation_epoch"][
                "evaluation_epoch_id"
            ],
            "graph_snapshot_sha256": lifecycle["evaluation_epoch"][
                "graph_snapshot_sha256"
            ],
            "candidate_vocabulary_sha256": vocabulary_hash,
            "lockbox_sample_size_plan_sha256": plan[
                "lockbox_sample_size_plan_sha256"
            ],
            "implementation_sha256": implementation_hash,
        },
        "source_bank_contract": {
            "storage": "access_controlled_outside_repository",
            "plaintext_in_repository_allowed": False,
            "allowed_fact_sources": [
                "public_knowledge_with_fixed_reference",
                "deterministic_synthetic_environment",
            ],
            "minimum_entry_count": MINIMUM_PRIVATE_SOURCE_BANK_SIZE,
            "minimum_entries_per_target_partition": (
                MINIMUM_PRIVATE_SOURCE_ITEMS_PER_PARTITION
            ),
            "required_entry_fields": [
                "source_item_id",
                "source_type",
                "source_reference",
                "question_text",
                "positive_concept_id",
                "positive_concept_name",
                "target_partition",
                "context_concepts_unscored",
                "explicit_negative_concepts",
                "independent_truth_rationale",
            ],
            "positive_count_per_entry": 1,
            "explicit_negative_count_per_entry": (
                EXPLICIT_NEGATIVES_PER_QUESTION
            ),
            "independent_human_or_rule_review_required": True,
            "subject_model_access_allowed": False,
            "subject_model_generated_questions": False,
            "subject_model_grades_itself": False,
            "live_graph_relations_used_as_ground_truth": False,
            "personal_user_memory_allowed": False,
            "external_api_required": False,
            "content_sha256_required_before_seed_sampling": True,
            "review_provenance_contract": {
                "required_bank_manifest_fields": [
                    "private_source_bank_sha256",
                    "reviewed_at",
                    "review_method",
                    "reviewer_role",
                    "reviewer_or_validator_id",
                    "validator_implementation_sha256",
                    "review_provenance_sha256",
                    "anchor_question_set_sha256",
                    "development_question_set_sha256",
                    "anchor_overlap_count",
                    "development_overlap_count",
                    "overlap_audit_sha256",
                ],
                "allowed_review_methods": [
                    "independent_human_review",
                    "deterministic_rule_validation",
                ],
                "subject_model_as_reviewer_allowed": False,
                "validator_implementation_sha256_required_for_rule_validation": (
                    True
                ),
                "anchor_overlap_count_required": 0,
                "development_overlap_count_required": 0,
            },
        },
        "generation_contract": {
            "exact_instances_generated_after_model_cutoff": True,
            "hidden_seed_sampled_after_model_cutoff": True,
            "hidden_seed_commitment_required_before_open": True,
            "seed_commitment_domain": SEED_COMMITMENT_DOMAIN,
            "seed_commitment_formula": (
                "sha256(utf8(domain + newline + seed + newline + "
                "model_cutoff_sha256 + newline + private_source_bank_sha256))"
            ),
            "sampling_without_replacement": True,
            "target_partition_counts": EXPECTED_PARTITION_COUNTS,
            "duplicate_question_hashes_allowed": False,
            "anchor_or_development_question_overlap_allowed": False,
            "all_other_graph_concepts": "unlabeled",
            "repository_receipt_before_open": [
                "model_cutoff_sha256",
                "private_source_bank_sha256",
                "hidden_seed_commitment_sha256",
                "question_set_sha256",
            ],
            "hidden_until_consumption": [
                "seed",
                "question_text",
                "reference_answer",
                "label_rows",
            ],
        },
        "opening_contract": {
            "one_time_open": True,
            "reopen_allowed": False,
            "model_selection_allowed": False,
            "release_labels_after_consumption": True,
            "released_labels_train_generation": "next_generation_only",
            "current_generation_training_allowed": False,
        },
        "claim_boundary": {
            "descriptive_heldout_diagnostic_only": True,
            "inferential_claim_allowed": False,
            "performance_claim_allowed": False,
            "production_promotion_allowed": False,
        },
        "question_instances_in_spec": False,
        "private_source_bank_in_repository": False,
        "database_writes": False,
        "learning_enabled": False,
        "heldout_gate": False,
        "performance_claim_gate": False,
        "production_promotion_gate": False,
    }
    spec["lockbox_generator_spec_sha256"] = canonical_json_sha256(spec)
    return spec


def validate_lockbox_generator_spec(
    payload: Mapping[str, Any],
    lifecycle: Mapping[str, Any],
    sample_size_plan: Mapping[str, Any],
    *,
    implementation_sha256: str,
) -> dict[str, Any]:
    normalized = _clone(payload)
    supplied = _require_sha256(
        normalized.get("lockbox_generator_spec_sha256"),
        "lockbox_generator_spec_sha256",
    )
    unhashed = _clone(normalized)
    unhashed.pop("lockbox_generator_spec_sha256", None)
    if supplied != canonical_json_sha256(unhashed):
        raise ValueError("lockbox_generator_spec_sha256 mismatch")
    expected = build_lockbox_generator_spec(
        lifecycle,
        sample_size_plan,
        candidate_vocabulary_sha256=str(
            dict(normalized.get("input_bindings") or {}).get(
                "candidate_vocabulary_sha256"
            )
            or ""
        ),
        implementation_sha256=implementation_sha256,
        created_at=str(normalized.get("created_at") or ""),
    )
    if normalized != expected:
        raise ValueError("lockbox generator spec does not match implementation")
    return normalized


def build_lockbox_review_packet(
    generator_spec: Mapping[str, Any],
    sample_size_plan: Mapping[str, Any],
    *,
    created_at: str,
) -> dict[str, Any]:
    packet = {
        "lockbox_review_packet_version": LOCKBOX_REVIEW_PACKET_VERSION,
        "phase": PHASE,
        "role": "one_time_lockbox",
        "status": "awaiting_explicit_user_review",
        "created_at": _zoned_timestamp(created_at, "created_at"),
        "lockbox_generator_spec_sha256": generator_spec[
            "lockbox_generator_spec_sha256"
        ],
        "lockbox_sample_size_plan_sha256": sample_size_plan[
            "lockbox_sample_size_plan_sha256"
        ],
        "proposal": {
            "question_count": sample_size_plan["question_count"],
            "target_partition_counts": sample_size_plan[
                "target_partition_counts"
            ],
            "positive_labels_per_question": 1,
            "explicit_negatives_per_question": (
                EXPLICIT_NEGATIVES_PER_QUESTION
            ),
            "minimum_private_source_bank_size": (
                MINIMUM_PRIVATE_SOURCE_BANK_SIZE
            ),
            "minimum_private_source_items_per_partition": (
                MINIMUM_PRIVATE_SOURCE_ITEMS_PER_PARTITION
            ),
            "source_bank_review_provenance_required": True,
            "zero_anchor_and_development_overlap_required": True,
            "plaintext_questions_in_repository": False,
            "exact_instances_generated_after_model_cutoff": True,
            "hidden_seed_sampled_after_model_cutoff": True,
            "one_time_open": True,
            "performance_claim_allowed": False,
        },
        "review_items": [
            {"review_item_id": item_id, "decision": "pending"}
            for item_id in REVIEW_ITEM_IDS
        ],
        "reviewer_role_required": "user",
        "review_gate": False,
        "generator_freeze_gate": False,
        "question_materialization_gate": False,
        "lexical_baseline_execution_gate": False,
        "block_reasons": [
            "explicit_user_review_missing",
            "generator_not_frozen",
            "model_cutoff_snapshot_missing",
            "private_source_bank_missing",
            "hidden_seed_not_sampled",
        ],
        "next_step": "review_lockbox_distribution_then_freeze_generator",
        "database_writes": False,
        "learning_enabled": False,
        "heldout_gate": False,
        "performance_claim_gate": False,
        "production_promotion_gate": False,
    }
    packet["lockbox_review_packet_sha256"] = canonical_json_sha256(packet)
    return packet


def validate_lockbox_review_packet(
    payload: Mapping[str, Any],
    generator_spec: Mapping[str, Any],
    sample_size_plan: Mapping[str, Any],
) -> dict[str, Any]:
    normalized = _clone(payload)
    supplied = _require_sha256(
        normalized.get("lockbox_review_packet_sha256"),
        "lockbox_review_packet_sha256",
    )
    unhashed = _clone(normalized)
    unhashed.pop("lockbox_review_packet_sha256", None)
    if supplied != canonical_json_sha256(unhashed):
        raise ValueError("lockbox_review_packet_sha256 mismatch")
    expected = build_lockbox_review_packet(
        generator_spec,
        sample_size_plan,
        created_at=str(normalized.get("created_at") or ""),
    )
    if normalized != expected:
        raise ValueError("lockbox review packet does not match generator inputs")
    return normalized


def validate_lockbox_review_decisions(
    payload: Mapping[str, Any],
    review_packet: Mapping[str, Any],
) -> dict[str, Any]:
    normalized = _clone(payload)
    if normalized.get("lockbox_review_decisions_version") != (
        LOCKBOX_REVIEW_DECISIONS_VERSION
    ):
        raise ValueError("unsupported lockbox_review_decisions_version")
    if normalized.get("phase") != PHASE:
        raise ValueError("lockbox review decisions phase must be J1-R2")
    if normalized.get("lockbox_review_packet_sha256") != review_packet.get(
        "lockbox_review_packet_sha256"
    ):
        raise ValueError("lockbox decisions are not bound to review packet")
    if normalized.get("reviewer_role") != "user":
        raise ValueError("lockbox review requires reviewer_role=user")
    _zoned_timestamp(normalized.get("reviewed_at"), "reviewed_at")
    supplied = _require_sha256(
        normalized.get("lockbox_review_decisions_sha256"),
        "lockbox_review_decisions_sha256",
    )
    unhashed = _clone(normalized)
    unhashed.pop("lockbox_review_decisions_sha256", None)
    if supplied != canonical_json_sha256(unhashed):
        raise ValueError("lockbox_review_decisions_sha256 mismatch")
    decisions = list(normalized.get("decisions") or [])
    ids = [str(item.get("review_item_id") or "") for item in decisions]
    if ids != list(REVIEW_ITEM_IDS):
        raise ValueError("lockbox decisions must cover every review item in order")
    if any(item.get("decision") != "approved" for item in decisions):
        raise ValueError("all lockbox policies require explicit approval")
    if normalized.get("overall_decision") != "approved":
        raise ValueError("overall lockbox review must be approved")
    return normalized


def freeze_lockbox_generator_manifest(
    lifecycle: Mapping[str, Any],
    planned_manifest: Mapping[str, Any],
    generator_spec: Mapping[str, Any],
    sample_size_plan: Mapping[str, Any],
    review_packet: Mapping[str, Any],
    review_decisions: Mapping[str, Any],
    *,
    implementation_sha256: str,
    created_at: str,
) -> dict[str, Any]:
    lifecycle = _validate_lifecycle(lifecycle)
    planned = validate_cohort_manifest(planned_manifest, lifecycle)
    if planned["role"] != "one_time_lockbox":
        raise ValueError("planned manifest must be a one-time lockbox")
    plan = validate_lockbox_sample_size_plan(sample_size_plan, lifecycle)
    spec = validate_lockbox_generator_spec(
        generator_spec,
        lifecycle,
        plan,
        implementation_sha256=implementation_sha256,
    )
    packet = validate_lockbox_review_packet(review_packet, spec, plan)
    decisions = validate_lockbox_review_decisions(
        review_decisions, packet
    )
    manifest = _clone(planned)
    manifest.update({
        "status": "generator_contract_frozen_questions_not_materialized",
        "lifecycle_state": "generator_frozen",
        "review_status": "user_reviewed",
        "created_at": _zoned_timestamp(created_at, "created_at"),
        "generator": {
            **manifest["generator"],
            "implementation_sha256": spec["input_bindings"][
                "implementation_sha256"
            ],
            "specification_sha256": spec[
                "lockbox_generator_spec_sha256"
            ],
            "sample_size_plan_sha256": plan[
                "lockbox_sample_size_plan_sha256"
            ],
            "review_packet_sha256": packet[
                "lockbox_review_packet_sha256"
            ],
            "review_decisions_sha256": decisions[
                "lockbox_review_decisions_sha256"
            ],
        },
        "materialization": {
            **manifest["materialization"],
            "materialized": False,
            "question_count": 0,
            "question_hashes": [],
            "question_set_sha256": None,
            "plaintext_questions_in_repository": False,
        },
        "execution_gate": False,
        "block_reasons": [
            "model_cutoff_snapshot_missing",
            "private_source_bank_missing",
            "hidden_seed_not_sampled",
            "cohort_not_materialized",
        ],
        "next_step": (
            "run_baselines_then_freeze_model_before_lockbox_materialization"
        ),
    })
    return validate_cohort_manifest(seal_cohort_manifest(manifest), lifecycle)


def hidden_seed_commitment_sha256(
    *,
    seed: str,
    model_cutoff_sha256: str,
    private_source_bank_sha256: str,
) -> str:
    if not seed:
        raise ValueError("seed must be non-empty")
    cutoff_hash = _require_sha256(model_cutoff_sha256, "model_cutoff_sha256")
    source_hash = _require_sha256(
        private_source_bank_sha256, "private_source_bank_sha256"
    )
    payload = "\n".join(
        (SEED_COMMITMENT_DOMAIN, seed, cutoff_hash, source_hash)
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
