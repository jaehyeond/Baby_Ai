from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from neural.baby.pending_question_semantics import canonical_json_sha256
from neural.baby.relevance_cohort_lifecycle import (
    build_cohort_manifest_readiness,
    validate_cohort_manifest,
    validate_cohort_manifest_readiness,
)
from neural.baby.relevance_lockbox_generator import (
    EXPECTED_PARTITION_COUNTS,
    REVIEW_ITEM_IDS,
    build_lockbox_generator_spec,
    build_lockbox_review_packet,
    build_lockbox_sample_size_plan,
    freeze_lockbox_generator_manifest,
    hidden_seed_commitment_sha256,
    validate_lockbox_generator_spec,
    validate_lockbox_review_decisions,
    validate_lockbox_review_packet,
    validate_lockbox_sample_size_plan,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TIMESTAMP = "2026-07-23T07:00:00+00:00"
IMPLEMENTATION_SHA256 = "a" * 64


def _load(relative_path: str) -> dict:
    return json.loads(
        (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")
    )


def _lifecycle() -> dict:
    return _load(
        "claudedocs/research/j1_r2_relevance_cohort_lifecycle_20260722.json"
    )


def _bundle() -> tuple[dict, dict, dict]:
    lifecycle = _lifecycle()
    plan = build_lockbox_sample_size_plan(
        lifecycle, created_at=TIMESTAMP
    )
    spec = build_lockbox_generator_spec(
        lifecycle,
        plan,
        candidate_vocabulary_sha256=lifecycle["evaluation_epoch"][
            "candidate_vocabulary_sha256"
        ],
        implementation_sha256=IMPLEMENTATION_SHA256,
        created_at=TIMESTAMP,
    )
    packet = build_lockbox_review_packet(
        spec, plan, created_at=TIMESTAMP
    )
    return plan, spec, packet


def _approved_decisions(packet: dict) -> dict:
    decisions = {
        "lockbox_review_decisions_version": 1,
        "phase": "J1-R2",
        "lockbox_review_packet_sha256": packet[
            "lockbox_review_packet_sha256"
        ],
        "reviewer_role": "user",
        "reviewed_at": TIMESTAMP,
        "overall_decision": "approved",
        "decisions": [
            {"review_item_id": item_id, "decision": "approved"}
            for item_id in REVIEW_ITEM_IDS
        ],
    }
    decisions["lockbox_review_decisions_sha256"] = canonical_json_sha256(
        decisions
    )
    return decisions


def _reseal_spec(payload: dict) -> dict:
    payload = deepcopy(payload)
    payload.pop("lockbox_generator_spec_sha256", None)
    payload["lockbox_generator_spec_sha256"] = canonical_json_sha256(payload)
    return payload


def _reseal_decisions(payload: dict) -> dict:
    payload = deepcopy(payload)
    payload.pop("lockbox_review_decisions_sha256", None)
    payload["lockbox_review_decisions_sha256"] = canonical_json_sha256(payload)
    return payload


def test_lockbox_plan_is_balanced_and_descriptive_only() -> None:
    lifecycle = _lifecycle()
    plan = build_lockbox_sample_size_plan(
        lifecycle, created_at=TIMESTAMP
    )

    assert plan["question_count"] == 24
    assert plan["target_partition_counts"] == EXPECTED_PARTITION_COUNTS
    assert plan["positive_label_count"] == 24
    assert plan["explicit_negative_label_count"] == 72
    assert plan["usage"]["inferential_claim_allowed"] is False
    assert plan["usage"]["performance_claim_allowed"] is False
    validate_lockbox_sample_size_plan(plan, lifecycle)


def test_lockbox_spec_contains_no_question_instances_or_private_bank() -> None:
    plan, spec, _ = _bundle()
    source = spec["source_bank_contract"]

    assert spec["question_instances_in_spec"] is False
    assert spec["private_source_bank_in_repository"] is False
    assert source["storage"] == "access_controlled_outside_repository"
    assert source["subject_model_access_allowed"] is False
    assert source["subject_model_generated_questions"] is False
    assert source["subject_model_grades_itself"] is False
    assert source["live_graph_relations_used_as_ground_truth"] is False
    assert source["personal_user_memory_allowed"] is False
    review = source["review_provenance_contract"]
    assert review["subject_model_as_reviewer_allowed"] is False
    assert review["anchor_overlap_count_required"] == 0
    assert review["development_overlap_count_required"] == 0
    assert review[
        "validator_implementation_sha256_required_for_rule_validation"
    ] is True
    validate_lockbox_generator_spec(
        spec,
        _lifecycle(),
        plan,
        implementation_sha256=IMPLEMENTATION_SHA256,
    )


def test_lockbox_review_packet_stays_blocked_before_user_review() -> None:
    plan, spec, packet = _bundle()

    validated = validate_lockbox_review_packet(packet, spec, plan)
    assert validated["review_gate"] is False
    assert validated["generator_freeze_gate"] is False
    assert validated["question_materialization_gate"] is False
    assert validated["proposal"][
        "source_bank_review_provenance_required"
    ] is True
    assert validated["proposal"][
        "zero_anchor_and_development_overlap_required"
    ] is True
    assert all(
        item["decision"] == "pending"
        for item in validated["review_items"]
    )


def test_hidden_seed_commitment_binds_cutoff_and_private_source_bank() -> None:
    first = hidden_seed_commitment_sha256(
        seed="secret-seed",
        model_cutoff_sha256="a" * 64,
        private_source_bank_sha256="b" * 64,
    )
    same = hidden_seed_commitment_sha256(
        seed="secret-seed",
        model_cutoff_sha256="a" * 64,
        private_source_bank_sha256="b" * 64,
    )
    changed_cutoff = hidden_seed_commitment_sha256(
        seed="secret-seed",
        model_cutoff_sha256="c" * 64,
        private_source_bank_sha256="b" * 64,
    )
    changed_source = hidden_seed_commitment_sha256(
        seed="secret-seed",
        model_cutoff_sha256="a" * 64,
        private_source_bank_sha256="d" * 64,
    )

    assert first == same
    assert len(first) == 64
    assert first != changed_cutoff
    assert first != changed_source


def test_validator_rejects_resealed_subject_model_question_generation() -> None:
    plan, spec, _ = _bundle()
    spec["source_bank_contract"]["subject_model_generated_questions"] = True
    spec = _reseal_spec(spec)

    with pytest.raises(
        ValueError, match="does not match implementation"
    ):
        validate_lockbox_generator_spec(
            spec,
            _lifecycle(),
            plan,
            implementation_sha256=IMPLEMENTATION_SHA256,
        )


def test_lockbox_freeze_requires_every_explicit_user_approval() -> None:
    _, _, packet = _bundle()
    decisions = _approved_decisions(packet)
    decisions["decisions"][0]["decision"] = "rejected"
    decisions = _reseal_decisions(decisions)

    with pytest.raises(ValueError, match="explicit approval"):
        validate_lockbox_review_decisions(decisions, packet)


def test_lockbox_freeze_revalidates_bound_implementation() -> None:
    lifecycle = _lifecycle()
    plan, spec, packet = _bundle()
    decisions = _approved_decisions(packet)

    with pytest.raises(ValueError, match="does not match implementation"):
        freeze_lockbox_generator_manifest(
            lifecycle,
            _load(
                "scripts/research/manifests/"
                "j1_r2_one_time_lockbox_manifest_draft_20260722.json"
            ),
            spec,
            plan,
            packet,
            decisions,
            implementation_sha256="b" * 64,
            created_at=TIMESTAMP,
        )


def test_generator_freeze_enables_baseline_not_lockbox_materialization() -> None:
    lifecycle = _lifecycle()
    plan, spec, packet = _bundle()
    decisions = _approved_decisions(packet)
    frozen = freeze_lockbox_generator_manifest(
        lifecycle,
        _load(
            "scripts/research/manifests/"
            "j1_r2_one_time_lockbox_manifest_draft_20260722.json"
        ),
        spec,
        plan,
        packet,
        decisions,
        implementation_sha256=IMPLEMENTATION_SHA256,
        created_at=TIMESTAMP,
    )
    anchor = validate_cohort_manifest(
        _load(
            "scripts/research/manifests/"
            "j1_r2_anchor_regression_manifest_20260722.json"
        ),
        lifecycle,
    )
    development = validate_cohort_manifest(
        _load(
            "scripts/research/manifests/"
            "j1_r2_rolling_development_manifest_reviewed_20260723.json"
        ),
        lifecycle,
    )
    readiness = build_cohort_manifest_readiness(
        lifecycle, [anchor, development, frozen]
    )

    assert frozen["lifecycle_state"] == "generator_frozen"
    assert frozen["review_status"] == "user_reviewed"
    assert frozen["materialization"]["materialized"] is False
    assert frozen["execution_gate"] is False
    assert readiness["lockbox_generator_manifest_gate"] is True
    assert readiness["lexical_baseline_execution_gate"] is True


def test_repository_lockbox_review_bundle_validates() -> None:
    lifecycle = _lifecycle()
    plan = validate_lockbox_sample_size_plan(
        _load(
            "scripts/research/specs/"
            "j1_r2_one_time_lockbox_sample_size_plan_draft_20260723.json"
        ),
        lifecycle,
    )
    implementation_hash = hashlib.sha256(
        (
            PROJECT_ROOT
            / "neural"
            / "baby"
            / "relevance_lockbox_generator.py"
        ).read_bytes()
    ).hexdigest()
    spec = validate_lockbox_generator_spec(
        _load(
            "scripts/research/specs/"
            "j1_r2_one_time_lockbox_generator_spec_draft_20260723.json"
        ),
        lifecycle,
        plan,
        implementation_sha256=implementation_hash,
    )
    packet = validate_lockbox_review_packet(
        _load(
            "scripts/research/inputs/"
            "j1_r2_one_time_lockbox_review_packet_20260723.json"
        ),
        spec,
        plan,
    )

    assert plan["lockbox_sample_size_plan_sha256"] == (
        "3607e14ee99b314a6fb75a957cc4c6e49c17311b08f9662e3e3042997a67b9fb"
    )
    assert spec["input_bindings"]["implementation_sha256"] == (
        "0feb151c93095d54af83700a57248cf2b592d81fb510c2d0e782867b3db360b9"
    )
    assert spec["lockbox_generator_spec_sha256"] == (
        "dde0ffefedd05b7e20f02ac903f55718315eaa403d68f1f78f4c7ba1a18c0898"
    )
    assert packet["lockbox_review_packet_sha256"] == (
        "01bed5589077472f377aa1aa402d83db2e06c785459a3b34137bd0717fb86ffd"
    )
    assert packet["review_gate"] is False
    assert packet["generator_freeze_gate"] is False
    assert plan["question_count"] == 24


def test_repository_approved_lockbox_generator_freeze_validates() -> None:
    lifecycle = _lifecycle()
    plan = validate_lockbox_sample_size_plan(
        _load(
            "scripts/research/specs/"
            "j1_r2_one_time_lockbox_sample_size_plan_draft_20260723.json"
        ),
        lifecycle,
    )
    implementation_hash = hashlib.sha256(
        (
            PROJECT_ROOT
            / "neural"
            / "baby"
            / "relevance_lockbox_generator.py"
        ).read_bytes()
    ).hexdigest()
    spec = validate_lockbox_generator_spec(
        _load(
            "scripts/research/specs/"
            "j1_r2_one_time_lockbox_generator_spec_draft_20260723.json"
        ),
        lifecycle,
        plan,
        implementation_sha256=implementation_hash,
    )
    packet = validate_lockbox_review_packet(
        _load(
            "scripts/research/inputs/"
            "j1_r2_one_time_lockbox_review_packet_20260723.json"
        ),
        spec,
        plan,
    )
    decisions = validate_lockbox_review_decisions(
        _load(
            "scripts/research/inputs/"
            "j1_r2_one_time_lockbox_review_decisions_20260723.json"
        ),
        packet,
    )
    frozen = _load(
        "scripts/research/manifests/"
        "j1_r2_one_time_lockbox_manifest_generator_frozen_20260723.json"
    )
    expected_frozen = freeze_lockbox_generator_manifest(
        lifecycle,
        _load(
            "scripts/research/manifests/"
            "j1_r2_one_time_lockbox_manifest_draft_20260722.json"
        ),
        spec,
        plan,
        packet,
        decisions,
        implementation_sha256=implementation_hash,
        created_at=frozen["created_at"],
    )
    anchor = validate_cohort_manifest(
        _load(
            "scripts/research/manifests/"
            "j1_r2_anchor_regression_manifest_20260722.json"
        ),
        lifecycle,
    )
    development = validate_cohort_manifest(
        _load(
            "scripts/research/manifests/"
            "j1_r2_rolling_development_manifest_reviewed_20260723.json"
        ),
        lifecycle,
    )
    readiness = validate_cohort_manifest_readiness(
        _load(
            "claudedocs/research/"
            "j1_r2_relevance_cohort_readiness_after_lockbox_freeze_20260723.json"
        ),
        lifecycle,
        [anchor, frozen, development],
    )

    assert decisions["approval_basis"]["content_modifications"] == [
        "clarified_24_question_distribution_not_exact_question_approval",
        "required_source_bank_review_provenance_and_zero_overlap_audit",
    ]
    assert frozen == expected_frozen
    assert decisions["lockbox_review_decisions_sha256"] == (
        "bdd4b58fe362edb734785b73b0e0a00f27fcfdbf4551f69ff024bd2fa3d19fb3"
    )
    assert frozen["cohort_manifest_sha256"] == (
        "0b5bc0cf40edb8826e1ef4f2cc705c243a02de458f182c93d153ad79a471b46f"
    )
    assert readiness["cohort_readiness_sha256"] == (
        "2954f13283c593857e7de70b7352f247438971a9b3e0f8405b59826e659f04f4"
    )
    assert readiness["lexical_baseline_execution_gate"] is True
    assert frozen["execution_gate"] is False
