"""Evaluation-epoch lifecycle contracts for a continually growing Baby AI.

J1-R2 supersedes the permanent-holdout interpretation of J1-R1 without
rewriting its sealed artifact.  Cohorts constrain evaluation evidence, never
the live experience stream or graph learning.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any, Iterable, Mapping

from neural.baby.pending_question_semantics import canonical_json_sha256


COHORT_LIFECYCLE_CONTRACT_VERSION = 1
COHORT_MANIFEST_VERSION = 1
COHORT_READINESS_VERSION = 1
PHASE = "J1-R2"
EVALUATION_EPOCH_ID = "j1-r2-evaluation-epoch-0001"
LIFECYCLE_STATUS = "rotating_cohort_lifecycle_defined_manifests_pending"
COHORT_ROLES = (
    "anchor_regression",
    "rolling_development",
    "one_time_lockbox",
)
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _clone(value: Mapping[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(value, ensure_ascii=False))


def _require_sha256(value: Any, field: str) -> str:
    raw = str(value or "")
    if not _SHA256_RE.fullmatch(raw):
        raise ValueError(f"{field} must be a lowercase SHA-256")
    return raw


def _optional_sha256(value: Any, field: str) -> str | None:
    if value is None:
        return None
    return _require_sha256(value, field)


def _zoned_timestamp(value: Any, field: str) -> str:
    raw = str(value or "").strip()
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} must include a timezone")
    return raw


def _validate_r1_self_hash(r1_artifact: Mapping[str, Any]) -> dict[str, Any]:
    normalized = _clone(r1_artifact)
    if normalized.get("phase") != "J1-R1":
        raise ValueError("J1-R2 must supersede a J1-R1 artifact")
    supplied = _require_sha256(
        normalized.get("relevance_scorer_contract_sha256"),
        "relevance_scorer_contract_sha256",
    )
    unhashed = _clone(normalized)
    unhashed.pop("relevance_scorer_contract_sha256", None)
    if supplied != canonical_json_sha256(unhashed):
        raise ValueError("J1-R1 relevance scorer contract hash mismatch")
    return normalized


def _validate_lifecycle_self_hash(
    lifecycle: Mapping[str, Any],
) -> dict[str, Any]:
    normalized = _clone(lifecycle)
    if normalized.get("cohort_lifecycle_contract_version") != (
        COHORT_LIFECYCLE_CONTRACT_VERSION
    ):
        raise ValueError("unsupported cohort_lifecycle_contract_version")
    if normalized.get("phase") != PHASE:
        raise ValueError("cohort lifecycle phase must be J1-R2")
    supplied = _require_sha256(
        normalized.get("cohort_lifecycle_contract_sha256"),
        "cohort_lifecycle_contract_sha256",
    )
    unhashed = _clone(normalized)
    unhashed.pop("cohort_lifecycle_contract_sha256", None)
    if supplied != canonical_json_sha256(unhashed):
        raise ValueError("cohort_lifecycle_contract_sha256 mismatch")
    return normalized


def _normalized_question_hashes(values: Iterable[Any]) -> list[str]:
    hashes = sorted(_require_sha256(value, "question_sha256") for value in values)
    if not hashes or len(hashes) != len(set(hashes)):
        raise ValueError("legacy question hashes must be non-empty and unique")
    return hashes


def _build_lifecycle_body(
    r1_artifact: Mapping[str, Any],
    *,
    graph_snapshot_sha256: str,
    legacy_question_hashes: Iterable[str],
    created_at: str,
) -> dict[str, Any]:
    r1 = _validate_r1_self_hash(r1_artifact)
    graph_snapshot_sha256 = _require_sha256(
        graph_snapshot_sha256, "graph_snapshot_sha256"
    )
    question_hashes = _normalized_question_hashes(legacy_question_hashes)
    created_at = _zoned_timestamp(created_at, "created_at")
    r1_hash = r1["relevance_scorer_contract_sha256"]
    r1_vocabulary_hash = r1["input_bindings"]["candidate_vocabulary_sha256"]

    return {
        "cohort_lifecycle_contract_version": COHORT_LIFECYCLE_CONTRACT_VERSION,
        "phase": PHASE,
        "status": LIFECYCLE_STATUS,
        "created_at": created_at,
        "supersedes": {
            "phase": "J1-R1",
            "relevance_scorer_contract_sha256": r1_hash,
            "reason": "replace_permanent_holdout_interpretation_with_rotating_evaluation_epochs",
            "r1_artifact_mutated": False,
        },
        "research_goal": {
            "system": "source_aware_grounded_developmental_self_improvement",
            "purpose": (
                "learn_from_quest_tool_and_environment_outcomes_while_"
                "preserving_auditable_promotion_and_rollback"
            ),
            "relevance_scorer_role": "memory_retrieval_instrument_not_the_whole_agent",
            "static_benchmark_optimization_is_the_goal": False,
        },
        "learning_evaluation_boundary": {
            "cohort_scope": "evaluation_evidence_only",
            "live_growth_stream_blocked_by_contract": False,
            "live_graph_updates_blocked_by_contract": False,
            "live_memory_consolidation_blocked_by_contract": False,
            "live_curiosity_generation_blocked_by_contract": False,
            "evaluation_uses_frozen_graph_snapshot": True,
            "reserved_item": "supervised_benchmark_label_not_live_concept",
            "reserved_labels_release_after_consumption": True,
            "released_labels_may_train_only_next_generation": True,
        },
        "evaluation_epoch": {
            "evaluation_epoch_id": EVALUATION_EPOCH_ID,
            "graph_snapshot_sha256": graph_snapshot_sha256,
            "candidate_vocabulary_sha256": r1_vocabulary_hash,
            "partition_contract_sha256": canonical_json_sha256(
                r1["graph_vocabulary_split"]
            ),
            "partition_scope": "this_evaluation_epoch_only",
            "new_concepts_after_snapshot_policy": "temporal_novelty_stratum_next_epoch",
            "model_cutoff_sha256": None,
            "model_cutoff_gate": False,
            "renewal_trigger": (
                "lockbox_consumed_or_graph_snapshot_invalidated_or_epoch_expired"
            ),
        },
        "cohort_roles": {
            "live_growth_stream": {
                "is_evaluation_cohort": False,
                "frozen": False,
                "eligible_for_learning": True,
                "performance_claim_source": False,
            },
            "anchor_regression": {
                "question_set_sha256": r1["legacy_data"]["question_set_sha256"],
                "question_hashes": question_hashes,
                "reusable": True,
                "known_to_developers": True,
                "model_selection_allowed": False,
                "heldout_claim_allowed": False,
                "purpose": "retention_and_regression_detection",
            },
            "rolling_development": {
                "reusable_within_generation": True,
                "replace_on_new_generation": True,
                "model_selection_allowed": True,
                "heldout_claim_allowed": False,
                "exact_questions_fixed_before_baseline_output": True,
            },
            "one_time_lockbox": {
                "reusable": False,
                "model_selection_allowed": False,
                "one_time_open": True,
                "generator_contract_fixed_before_baseline_output": True,
                "instances_generated_after_model_freeze": True,
                "hidden_seed_required": True,
                "plaintext_questions_in_repository_allowed": False,
            },
        },
        "generator_governance": {
            "freeze_generator_distribution_not_permanent_question_instances": True,
            "subject_model_may_generate_evaluation_questions": False,
            "subject_model_may_grade_itself": False,
            "independent_ground_truth_required": True,
            "allowed_sources": [
                "public_knowledge_with_fixed_reference",
                "deterministic_synthetic_environment",
                "instrumented_quest_or_tool_outcome",
            ],
            "personal_user_memory_allowed": False,
            "generator_implementation_sha256_required": True,
            "generator_specification_sha256_required": True,
            "sample_size_plan_sha256_required": True,
            "lockbox_hidden_seed_commitment_required_at_materialization": True,
        },
        "lifecycle_state_machine": {
            "anchor": ["materialized", "active", "superseded"],
            "development": [
                "planned",
                "materialized",
                "active",
                "consumed",
                "released",
                "superseded",
            ],
            "lockbox": [
                "planned",
                "generator_frozen",
                "model_frozen",
                "materialized",
                "opened",
                "consumed",
                "released",
                "expired",
            ],
            "lockbox_reopen_allowed": False,
            "release_semantics": (
                "benchmark_labels_become_next_generation_train_eligible_"
                "while_live_learning_was_never_blocked"
            ),
        },
        "continual_evaluation_metrics": {
            "retrieval": ["macro_recall_at_8", "macro_ndcg_at_8", "macro_mrr"],
            "development": [
                "pre_update_to_post_update_learning_progress",
                "forward_transfer_to_temporally_new_concepts",
                "backward_retention_on_anchor",
                "forgetting_delta_on_prior_anchor_generations",
            ],
            "promotion_unit": "versioned_model_and_memory_snapshot",
            "rollback_required": True,
        },
        "readiness": {
            "lifecycle_contract_gate": True,
            "live_learning_isolation_gate": True,
            "anchor_manifest_gate": False,
            "development_generator_manifest_gate": False,
            "lockbox_generator_manifest_gate": False,
            "model_cutoff_gate": False,
            "lexical_baseline_execution_gate": False,
            "heldout_gate": False,
            "performance_claim_gate": False,
            "production_promotion_gate": False,
            "block_reasons": [
                "anchor_manifest_missing",
                "rolling_development_generator_manifest_missing",
                "one_time_lockbox_generator_manifest_missing",
                "model_cutoff_snapshot_missing",
            ],
        },
        "database_writes": False,
        "learning_enabled": False,
        "model_weights_changed": False,
        "next_step": "seal_anchor_and_reviewable_development_lockbox_generator_manifests",
    }


def build_relevance_cohort_lifecycle_contract(
    r1_artifact: Mapping[str, Any],
    *,
    graph_snapshot_sha256: str,
    legacy_question_hashes: Iterable[str],
    created_at: str,
) -> dict[str, Any]:
    body = _build_lifecycle_body(
        r1_artifact,
        graph_snapshot_sha256=graph_snapshot_sha256,
        legacy_question_hashes=legacy_question_hashes,
        created_at=created_at,
    )
    body["cohort_lifecycle_contract_sha256"] = canonical_json_sha256(body)
    return body


def validate_relevance_cohort_lifecycle_contract(
    artifact: Mapping[str, Any],
    r1_artifact: Mapping[str, Any],
    *,
    graph_snapshot_sha256: str,
    legacy_question_hashes: Iterable[str],
) -> dict[str, Any]:
    normalized = _clone(artifact)
    supplied = _require_sha256(
        normalized.get("cohort_lifecycle_contract_sha256"),
        "cohort_lifecycle_contract_sha256",
    )
    unhashed = _clone(normalized)
    unhashed.pop("cohort_lifecycle_contract_sha256", None)
    if supplied != canonical_json_sha256(unhashed):
        raise ValueError("cohort_lifecycle_contract_sha256 mismatch")
    expected = build_relevance_cohort_lifecycle_contract(
        r1_artifact,
        graph_snapshot_sha256=graph_snapshot_sha256,
        legacy_question_hashes=legacy_question_hashes,
        created_at=str(normalized.get("created_at") or ""),
    )
    if normalized != expected:
        raise ValueError("cohort lifecycle contract does not match bound inputs")
    return normalized


def _base_manifest(
    lifecycle: Mapping[str, Any],
    *,
    cohort_id: str,
    cohort_generation_id: str,
    role: str,
    created_at: str,
) -> dict[str, Any]:
    if role not in COHORT_ROLES:
        raise ValueError(f"unsupported cohort role: {role}")
    return {
        "cohort_manifest_version": COHORT_MANIFEST_VERSION,
        "phase": PHASE,
        "cohort_id": cohort_id,
        "cohort_generation_id": cohort_generation_id,
        "evaluation_epoch_id": lifecycle["evaluation_epoch"]["evaluation_epoch_id"],
        "role": role,
        "created_at": _zoned_timestamp(created_at, "created_at"),
        "cohort_lifecycle_contract_sha256": lifecycle[
            "cohort_lifecycle_contract_sha256"
        ],
        "graph_snapshot_sha256": lifecycle["evaluation_epoch"][
            "graph_snapshot_sha256"
        ],
        "candidate_vocabulary_sha256": lifecycle["evaluation_epoch"][
            "candidate_vocabulary_sha256"
        ],
        "evaluation_only_not_live_learning_block": True,
        "live_learning_blocked": False,
        "database_writes": False,
        "learning_enabled": False,
        "heldout_gate": False,
        "performance_claim_gate": False,
        "production_promotion_gate": False,
    }


def build_anchor_manifest(
    lifecycle: Mapping[str, Any],
    *,
    created_at: str,
) -> dict[str, Any]:
    anchor = lifecycle["cohort_roles"]["anchor_regression"]
    payload = {
        **_base_manifest(
            lifecycle,
            cohort_id="j1-r2-anchor-regression-legacy-six",
            cohort_generation_id="anchor-generation-0001",
            role="anchor_regression",
            created_at=created_at,
        ),
        "status": "materialized_known_regression_not_heldout",
        "lifecycle_state": "active",
        "review_status": "historical_user_reviewed",
        "generator": {
            "mode": "historical_fixed_questions",
            "subject_model_generated_questions": False,
            "independent_ground_truth_required": True,
            "personal_user_memory_allowed": False,
            "implementation_sha256": None,
            "specification_sha256": lifecycle["supersedes"][
                "relevance_scorer_contract_sha256"
            ],
            "sample_size_plan_sha256": None,
            "hidden_seed_commitment_sha256": None,
        },
        "materialization": {
            "materialized": True,
            "question_count": len(anchor["question_hashes"]),
            "question_hashes": anchor["question_hashes"],
            "question_set_sha256": canonical_json_sha256(anchor["question_hashes"]),
            "plaintext_questions_in_repository": True,
        },
        "usage": {
            "reusable": True,
            "model_selection_allowed": False,
            "heldout_claim_allowed": False,
            "performance_claim_allowed": False,
            "release_after_consumption": False,
        },
        "execution_gate": True,
        "block_reasons": [],
        "next_step": "use_only_for_regression_and_retention_tracking",
    }
    return seal_cohort_manifest(payload)


def build_planned_generator_manifest(
    lifecycle: Mapping[str, Any],
    *,
    role: str,
    cohort_id: str,
    cohort_generation_id: str,
    created_at: str,
) -> dict[str, Any]:
    if role not in {"rolling_development", "one_time_lockbox"}:
        raise ValueError("planned generator role must be development or lockbox")
    is_lockbox = role == "one_time_lockbox"
    payload = {
        **_base_manifest(
            lifecycle,
            cohort_id=cohort_id,
            cohort_generation_id=cohort_generation_id,
            role=role,
            created_at=created_at,
        ),
        "status": "planned_generator_contract_awaiting_user_review",
        "lifecycle_state": "planned",
        "review_status": "awaiting_user_review",
        "generator": {
            "mode": "independent_deterministic_generator",
            "subject_model_generated_questions": False,
            "subject_model_grades_itself": False,
            "independent_ground_truth_required": True,
            "allowed_sources": lifecycle["generator_governance"]["allowed_sources"],
            "personal_user_memory_allowed": False,
            "implementation_sha256": None,
            "specification_sha256": None,
            "sample_size_plan_sha256": None,
            "seed_policy": (
                "hidden_seed_sampled_after_model_freeze"
                if is_lockbox
                else "development_seed_recorded_at_materialization"
            ),
            "hidden_seed_commitment_sha256": None,
        },
        "materialization": {
            "materialized": False,
            "question_count": 0,
            "question_hashes": [],
            "question_set_sha256": None,
            "plaintext_questions_in_repository": not is_lockbox,
        },
        "usage": {
            "reusable": not is_lockbox,
            "model_selection_allowed": not is_lockbox,
            "heldout_claim_allowed": is_lockbox,
            "performance_claim_allowed": False,
            "one_time_open": is_lockbox,
            "release_after_consumption": True,
            "released_labels_train_generation": "next_generation_only",
        },
        "execution_gate": False,
        "block_reasons": [
            "explicit_user_review_missing",
            "generator_implementation_snapshot_missing",
            "generator_specification_missing",
            "sample_size_plan_missing",
            "cohort_not_materialized",
        ],
        "next_step": (
            "review_and_freeze_lockbox_generator_before_baseline_execution"
            if is_lockbox
            else "review_generator_then_materialize_development_questions_before_baseline_execution"
        ),
    }
    return seal_cohort_manifest(payload)


def seal_cohort_manifest(payload: Mapping[str, Any]) -> dict[str, Any]:
    normalized = _clone(payload)
    normalized.pop("cohort_manifest_sha256", None)
    normalized["cohort_manifest_sha256"] = canonical_json_sha256(normalized)
    return normalized


def validate_cohort_manifest(
    payload: Mapping[str, Any],
    lifecycle: Mapping[str, Any],
) -> dict[str, Any]:
    lifecycle = _validate_lifecycle_self_hash(lifecycle)
    normalized = _clone(payload)
    if normalized.get("cohort_manifest_version") != COHORT_MANIFEST_VERSION:
        raise ValueError("unsupported cohort_manifest_version")
    if normalized.get("phase") != PHASE:
        raise ValueError("cohort manifest phase must be J1-R2")
    if normalized.get("role") not in COHORT_ROLES:
        raise ValueError("invalid cohort role")
    _zoned_timestamp(normalized.get("created_at"), "created_at")
    if normalized.get("cohort_lifecycle_contract_sha256") != lifecycle.get(
        "cohort_lifecycle_contract_sha256"
    ):
        raise ValueError("cohort lifecycle binding mismatch")
    for field in (
        "graph_snapshot_sha256",
        "candidate_vocabulary_sha256",
    ):
        _require_sha256(normalized.get(field), field)
        if normalized.get(field) != lifecycle["evaluation_epoch"].get(field):
            raise ValueError(f"{field} does not match evaluation epoch")
    if normalized.get("evaluation_epoch_id") != lifecycle["evaluation_epoch"].get(
        "evaluation_epoch_id"
    ):
        raise ValueError("evaluation_epoch_id mismatch")
    if normalized.get("evaluation_only_not_live_learning_block") is not True:
        raise ValueError("cohort must remain evaluation-only")
    if normalized.get("live_learning_blocked") is not False:
        raise ValueError("cohort cannot block the live learning stream")
    for field in (
        "database_writes",
        "learning_enabled",
        "heldout_gate",
        "performance_claim_gate",
        "production_promotion_gate",
    ):
        if normalized.get(field) is not False:
            raise ValueError(f"cohort manifest must keep {field}=false")

    generator = dict(normalized.get("generator") or {})
    if generator.get("subject_model_generated_questions") is not False:
        raise ValueError("subject model cannot generate evaluation questions")
    if generator.get("independent_ground_truth_required") is not True:
        raise ValueError("independent ground truth is required")
    if generator.get("personal_user_memory_allowed") is not False:
        raise ValueError("personal user memory is outside this benchmark")
    for field in (
        "implementation_sha256",
        "specification_sha256",
        "sample_size_plan_sha256",
        "hidden_seed_commitment_sha256",
    ):
        _optional_sha256(generator.get(field), f"generator.{field}")

    materialization = dict(normalized.get("materialization") or {})
    question_hashes = list(materialization.get("question_hashes") or [])
    if materialization.get("materialized") is False:
        if materialization.get("question_count") != 0 or question_hashes:
            raise ValueError("planned cohort cannot contain materialized questions")
        if materialization.get("question_set_sha256") is not None:
            raise ValueError("planned cohort cannot expose a question set hash")
    else:
        normalized_hashes = _normalized_question_hashes(question_hashes)
        if materialization.get("question_count") != len(normalized_hashes):
            raise ValueError("materialized question_count mismatch")
        if materialization.get("question_set_sha256") != canonical_json_sha256(
            normalized_hashes
        ):
            raise ValueError("materialized question_set_sha256 mismatch")

    role = normalized["role"]
    usage = dict(normalized.get("usage") or {})
    if role == "anchor_regression":
        if normalized.get("lifecycle_state") != "active":
            raise ValueError("anchor must be active")
        if materialization.get("materialized") is not True:
            raise ValueError("anchor must be materialized")
        if usage.get("heldout_claim_allowed") is not False:
            raise ValueError("anchor is not held-out evidence")
        if usage.get("reusable") is not True:
            raise ValueError("anchor must be reusable for regression")
    elif role == "rolling_development":
        if usage.get("model_selection_allowed") is not True:
            raise ValueError("development cohort must permit model selection")
        if usage.get("heldout_claim_allowed") is not False:
            raise ValueError("development cohort is not final held-out evidence")
    else:
        if materialization.get("plaintext_questions_in_repository") is not False:
            raise ValueError("lockbox plaintext cannot be stored in the repository")
        if usage.get("reusable") is not False or usage.get("one_time_open") is not True:
            raise ValueError("lockbox must be one-time and non-reusable")
        if usage.get("model_selection_allowed") is not False:
            raise ValueError("lockbox cannot select models")
        if generator.get("seed_policy") != "hidden_seed_sampled_after_model_freeze":
            raise ValueError("lockbox requires a hidden post-freeze seed")

    if usage.get("release_after_consumption") is True and usage.get(
        "released_labels_train_generation"
    ) != "next_generation_only":
        raise ValueError("released labels may train only the next generation")
    supplied = _require_sha256(
        normalized.get("cohort_manifest_sha256"), "cohort_manifest_sha256"
    )
    unhashed = _clone(normalized)
    unhashed.pop("cohort_manifest_sha256", None)
    if supplied != canonical_json_sha256(unhashed):
        raise ValueError("cohort_manifest_sha256 mismatch")
    return normalized


def build_cohort_manifest_readiness(
    lifecycle: Mapping[str, Any],
    manifests: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    lifecycle = _validate_lifecycle_self_hash(lifecycle)
    validated = [validate_cohort_manifest(item, lifecycle) for item in manifests]
    by_role: dict[str, dict[str, Any]] = {}
    cohort_ids: set[str] = set()
    for manifest in validated:
        role = str(manifest["role"])
        cohort_id = str(manifest.get("cohort_id") or "")
        if role in by_role or not cohort_id or cohort_id in cohort_ids:
            raise ValueError("cohort bundle requires one unique manifest per role")
        by_role[role] = manifest
        cohort_ids.add(cohort_id)
    if set(by_role) != set(COHORT_ROLES):
        raise ValueError("cohort bundle must include anchor, development, and lockbox")

    materialized_hashes: dict[str, set[str]] = {}
    for role, manifest in by_role.items():
        materialized_hashes[role] = set(
            manifest["materialization"].get("question_hashes") or []
        )
    roles = list(COHORT_ROLES)
    for index, left in enumerate(roles):
        for right in roles[index + 1:]:
            if materialized_hashes[left] & materialized_hashes[right]:
                raise ValueError("cohort question hashes overlap across roles")

    anchor_gate = by_role["anchor_regression"].get("execution_gate") is True
    development = by_role["rolling_development"]
    lockbox = by_role["one_time_lockbox"]
    development_gate = (
        development.get("review_status") == "user_reviewed"
        and development.get("execution_gate") is True
        and development["materialization"].get("materialized") is True
    )
    lockbox_generator_gate = (
        lockbox.get("review_status") == "user_reviewed"
        and lockbox.get("lifecycle_state") == "generator_frozen"
        and lockbox["generator"].get("implementation_sha256") is not None
        and lockbox["generator"].get("specification_sha256") is not None
        and lockbox["generator"].get("sample_size_plan_sha256") is not None
    )
    lexical_gate = anchor_gate and development_gate and lockbox_generator_gate
    block_reasons = []
    if not anchor_gate:
        block_reasons.append("anchor_manifest_not_executable")
    if not development_gate:
        block_reasons.append("rolling_development_cohort_not_reviewed_and_materialized")
    if not lockbox_generator_gate:
        block_reasons.append("one_time_lockbox_generator_not_reviewed_and_frozen")
    readiness = {
        "cohort_readiness_version": COHORT_READINESS_VERSION,
        "phase": PHASE,
        "status": (
            "cohort_manifests_ready_for_lexical_baseline"
            if lexical_gate
            else "cohort_manifest_drafts_incomplete_baseline_blocked"
        ),
        "cohort_lifecycle_contract_sha256": lifecycle[
            "cohort_lifecycle_contract_sha256"
        ],
        "manifest_hashes": {
            role: by_role[role]["cohort_manifest_sha256"] for role in COHORT_ROLES
        },
        "anchor_manifest_gate": anchor_gate,
        "development_manifest_gate": development_gate,
        "lockbox_generator_manifest_gate": lockbox_generator_gate,
        "lexical_baseline_execution_gate": lexical_gate,
        "live_learning_blocked": False,
        "database_writes": False,
        "learning_enabled": False,
        "heldout_gate": False,
        "performance_claim_gate": False,
        "production_promotion_gate": False,
        "block_reasons": block_reasons,
        "next_step": (
            "run_lexical_baseline"
            if lexical_gate
            else "review_and_materialize_development_then_freeze_lockbox_generator"
        ),
    }
    readiness["cohort_readiness_sha256"] = canonical_json_sha256(readiness)
    return readiness


def validate_cohort_manifest_readiness(
    payload: Mapping[str, Any],
    lifecycle: Mapping[str, Any],
    manifests: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    normalized = _clone(payload)
    if normalized.get("cohort_readiness_version") != COHORT_READINESS_VERSION:
        raise ValueError("unsupported cohort_readiness_version")
    supplied = _require_sha256(
        normalized.get("cohort_readiness_sha256"),
        "cohort_readiness_sha256",
    )
    unhashed = _clone(normalized)
    unhashed.pop("cohort_readiness_sha256", None)
    if supplied != canonical_json_sha256(unhashed):
        raise ValueError("cohort_readiness_sha256 mismatch")
    expected = build_cohort_manifest_readiness(lifecycle, manifests)
    if normalized != expected:
        raise ValueError("cohort readiness does not match bound manifests")
    return normalized
