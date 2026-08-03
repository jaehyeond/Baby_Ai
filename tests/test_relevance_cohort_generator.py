from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from neural.baby.pending_question_semantics import canonical_json_sha256
from neural.baby.relevance_cohort_generator import (
    build_development_generator_spec,
    build_development_review_packet,
    build_development_sample_size_plan,
    build_reviewed_development_label_pack,
    materialize_reviewed_development_manifest,
    validate_development_generator_spec,
    validate_development_review_decisions,
    validate_development_review_packet,
    validate_development_sample_size_plan,
)
from neural.baby.relevance_cohort_lifecycle import (
    build_cohort_manifest_readiness,
    validate_cohort_manifest,
    validate_cohort_manifest_readiness,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TIMESTAMP = "2026-07-23T01:00:00+00:00"
IMPLEMENTATION_SHA256 = "a" * 64


def _load(relative_path: str) -> dict:
    return json.loads(
        (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")
    )


def _inputs() -> tuple[dict, dict, list[str]]:
    lifecycle = _load(
        "claudedocs/research/j1_r2_relevance_cohort_lifecycle_20260722.json"
    )
    vocabulary = _load(
        "scripts/research/inputs/"
        "j1_1_candidate_vocabulary_v2_20260716.json"
    )
    train_manifest = _load(
        "scripts/research/manifests/j1_1_train_calibration_a_20260716.json"
    )
    legacy_hashes = [
        item["question_sha256"] for item in train_manifest["questions"]
    ]
    return lifecycle, vocabulary, legacy_hashes


def _bundle() -> tuple[dict, dict, dict]:
    lifecycle, vocabulary, legacy_hashes = _inputs()
    plan = build_development_sample_size_plan(
        lifecycle, created_at=TIMESTAMP
    )
    spec = build_development_generator_spec(
        lifecycle,
        vocabulary,
        plan,
        implementation_sha256=IMPLEMENTATION_SHA256,
        created_at=TIMESTAMP,
    )
    validate_development_generator_spec(
        spec,
        lifecycle,
        vocabulary,
        plan,
        legacy_question_hashes=legacy_hashes,
    )
    packet = build_development_review_packet(
        spec, plan, created_at=TIMESTAMP
    )
    return plan, spec, packet


def _approved_decisions(packet: dict) -> dict:
    payload = {
        "review_decisions_version": 1,
        "phase": "J1-R2",
        "review_packet_sha256": packet["review_packet_sha256"],
        "reviewer_role": "user",
        "reviewed_at": TIMESTAMP,
        "overall_decision": "approved",
        "decisions": [
            {
                "question_id": item["question_id"],
                "decision": "approved",
            }
            for item in packet["questions"]
        ],
    }
    payload["review_decisions_sha256"] = canonical_json_sha256(payload)
    return payload


def _reseal_spec(payload: dict) -> dict:
    payload = deepcopy(payload)
    payload.pop("generator_spec_sha256", None)
    payload["generator_spec_sha256"] = canonical_json_sha256(payload)
    return payload


def _reseal_decisions(payload: dict) -> dict:
    payload = deepcopy(payload)
    payload.pop("review_decisions_sha256", None)
    payload["review_decisions_sha256"] = canonical_json_sha256(payload)
    return payload


def test_sample_plan_is_descriptive_and_never_coerces_unlabeled_negatives() -> None:
    lifecycle, _, _ = _inputs()
    plan = build_development_sample_size_plan(
        lifecycle, created_at=TIMESTAMP
    )

    assert plan["question_count"] == 12
    assert plan["positive_label_count"] == 12
    assert plan["explicit_negative_label_count"] == 36
    assert plan["target_partition_counts"] == {
        "fit_pool": 8,
        "development_challenge_pool": 4,
        "lockbox_challenge_pool": 0,
    }
    assert plan["unlabeled_graph_concept_policy"] == (
        "ignore_never_assume_negative"
    )
    assert plan["usage"]["inferential_claim_allowed"] is False
    validate_development_sample_size_plan(plan, lifecycle)


def test_generator_uses_independent_closed_world_truth() -> None:
    _, spec, _ = _bundle()
    source = spec["source_contract"]

    assert source["source_type"] == "deterministic_synthetic_environment"
    assert source["subject_model_generated_questions"] is False
    assert source["subject_model_grades_itself"] is False
    assert source["live_graph_relations_used_as_ground_truth"] is False
    assert source["external_api_used"] is False
    assert source["personal_user_memory_allowed"] is False


def test_generator_materializes_twelve_unique_non_anchor_questions() -> None:
    _, spec, _ = _bundle()
    _, _, legacy_hashes = _inputs()
    questions = spec["questions"]
    hashes = [item["question_sha256"] for item in questions]

    assert len(questions) == 12
    assert len(set(hashes)) == 12
    assert not (set(hashes) & set(legacy_hashes))
    assert all(len(item["positive_concepts"]) == 1 for item in questions)
    assert all(
        len(item["explicit_negative_concepts"]) == 3 for item in questions
    )
    assert all(
        item["all_other_graph_concepts"] == "unlabeled"
        for item in questions
    )


def test_generator_reserves_lockbox_partition_targets() -> None:
    _, spec, _ = _bundle()
    partitions = [
        item["positive_concepts"][0]["partition"]
        for item in spec["questions"]
    ]

    assert partitions.count("fit_pool") == 8
    assert partitions.count("development_challenge_pool") == 4
    assert partitions.count("lockbox_challenge_pool") == 0


def test_review_packet_is_explicitly_blocked_pending_user_review() -> None:
    plan, spec, packet = _bundle()

    validated = validate_development_review_packet(packet, spec, plan)
    assert validated["question_count"] == 12
    assert validated["reviewer_role_required"] == "user"
    assert validated["review_gate"] is False
    assert validated["materialization_gate"] is False
    assert all(
        item["review_decision"] == "pending"
        for item in validated["questions"]
    )


def test_validator_rejects_resealed_subject_model_ground_truth() -> None:
    plan, spec, _ = _bundle()
    lifecycle, vocabulary, legacy_hashes = _inputs()
    spec["source_contract"]["subject_model_generated_questions"] = True
    spec = _reseal_spec(spec)

    with pytest.raises(
        ValueError, match="does not match deterministic implementation"
    ):
        validate_development_generator_spec(
            spec,
            lifecycle,
            vocabulary,
            plan,
            legacy_question_hashes=legacy_hashes,
        )


def test_validator_rejects_resealed_automatic_negative_policy() -> None:
    plan, spec, _ = _bundle()
    lifecycle, vocabulary, legacy_hashes = _inputs()
    spec["label_contract"][
        "automatic_random_negative_labeling_allowed"
    ] = True
    spec = _reseal_spec(spec)

    with pytest.raises(
        ValueError, match="does not match deterministic implementation"
    ):
        validate_development_generator_spec(
            spec,
            lifecycle,
            vocabulary,
            plan,
            legacy_question_hashes=legacy_hashes,
        )


def test_review_decisions_require_user_and_all_questions() -> None:
    _, _, packet = _bundle()
    decisions = _approved_decisions(packet)
    decisions["reviewer_role"] = "assistant"
    decisions = _reseal_decisions(decisions)

    with pytest.raises(ValueError, match="reviewer_role=user"):
        validate_development_review_decisions(decisions, packet)

    decisions = _approved_decisions(packet)
    decisions["decisions"][0]["decision"] = "rejected"
    decisions = _reseal_decisions(decisions)
    with pytest.raises(ValueError, match="explicit approval"):
        validate_development_review_decisions(decisions, packet)


def test_approved_review_materializes_development_but_not_lockbox() -> None:
    lifecycle, _, _ = _inputs()
    plan, spec, packet = _bundle()
    decisions = _approved_decisions(packet)
    labels = build_reviewed_development_label_pack(
        spec, packet, decisions, created_at=TIMESTAMP
    )
    development = materialize_reviewed_development_manifest(
        lifecycle,
        _load(
            "scripts/research/manifests/"
            "j1_r2_rolling_development_manifest_draft_20260722.json"
        ),
        spec,
        plan,
        packet,
        decisions,
        labels,
        created_at=TIMESTAMP,
    )
    anchor = validate_cohort_manifest(
        _load(
            "scripts/research/manifests/"
            "j1_r2_anchor_regression_manifest_20260722.json"
        ),
        lifecycle,
    )
    lockbox = validate_cohort_manifest(
        _load(
            "scripts/research/manifests/"
            "j1_r2_one_time_lockbox_manifest_draft_20260722.json"
        ),
        lifecycle,
    )
    readiness = build_cohort_manifest_readiness(
        lifecycle, [anchor, development, lockbox]
    )

    assert development["review_status"] == "user_reviewed"
    assert development["materialization"]["question_count"] == 12
    assert development["execution_gate"] is True
    assert labels["positive_label_count"] == 12
    assert labels["explicit_negative_label_count"] == 36
    assert readiness["development_manifest_gate"] is True
    assert readiness["lockbox_generator_manifest_gate"] is False
    assert readiness["lexical_baseline_execution_gate"] is False


def test_repository_development_generator_review_bundle_validates() -> None:
    lifecycle, vocabulary, legacy_hashes = _inputs()
    plan = validate_development_sample_size_plan(
        _load(
            "scripts/research/specs/"
            "j1_r2_rolling_development_sample_size_plan_draft_20260723.json"
        ),
        lifecycle,
    )
    spec = validate_development_generator_spec(
        _load(
            "scripts/research/specs/"
            "j1_r2_rolling_development_generator_spec_draft_20260723.json"
        ),
        lifecycle,
        vocabulary,
        plan,
        legacy_question_hashes=legacy_hashes,
    )
    packet = validate_development_review_packet(
        _load(
            "scripts/research/inputs/"
            "j1_r2_rolling_development_review_packet_20260723.json"
        ),
        spec,
        plan,
    )
    implementation_hash = hashlib.sha256(
        (
            PROJECT_ROOT
            / "neural"
            / "baby"
            / "relevance_cohort_generator.py"
        ).read_bytes()
    ).hexdigest()

    assert plan["sample_size_plan_sha256"] == (
        "17b705ddbd7533bacf1bcaffc3cba637a2cba6db8a37567a644567b75fc628f7"
    )
    assert spec["generator_spec_sha256"] == (
        "f900d8a097eaa61298dd0980b98b5a35c0efcb27fac93c5a4fe7108b85a057f5"
    )
    assert packet["review_packet_sha256"] == (
        "e5aded97a12ef997ab72d7687cd39e63edfd1e9fa8126f71b8eabaeb8b5f7624"
    )
    assert spec["implementation_sha256"] == implementation_hash
    assert packet["review_gate"] is False


def test_repository_reviewed_development_artifacts_validate() -> None:
    lifecycle, vocabulary, legacy_hashes = _inputs()
    plan = validate_development_sample_size_plan(
        _load(
            "scripts/research/specs/"
            "j1_r2_rolling_development_sample_size_plan_draft_20260723.json"
        ),
        lifecycle,
    )
    spec = validate_development_generator_spec(
        _load(
            "scripts/research/specs/"
            "j1_r2_rolling_development_generator_spec_draft_20260723.json"
        ),
        lifecycle,
        vocabulary,
        plan,
        legacy_question_hashes=legacy_hashes,
    )
    packet = validate_development_review_packet(
        _load(
            "scripts/research/inputs/"
            "j1_r2_rolling_development_review_packet_20260723.json"
        ),
        spec,
        plan,
    )
    decisions = validate_development_review_decisions(
        _load(
            "scripts/research/inputs/"
            "j1_r2_rolling_development_review_decisions_20260723.json"
        ),
        packet,
    )
    labels = _load(
        "scripts/research/inputs/"
        "j1_r2_rolling_development_labels_reviewed_20260723.json"
    )
    expected_labels = build_reviewed_development_label_pack(
        spec,
        packet,
        decisions,
        created_at=labels["created_at"],
    )
    development = _load(
        "scripts/research/manifests/"
        "j1_r2_rolling_development_manifest_reviewed_20260723.json"
    )
    expected_development = materialize_reviewed_development_manifest(
        lifecycle,
        _load(
            "scripts/research/manifests/"
            "j1_r2_rolling_development_manifest_draft_20260722.json"
        ),
        spec,
        plan,
        packet,
        decisions,
        labels,
        created_at=development["created_at"],
    )
    anchor = validate_cohort_manifest(
        _load(
            "scripts/research/manifests/"
            "j1_r2_anchor_regression_manifest_20260722.json"
        ),
        lifecycle,
    )
    lockbox = validate_cohort_manifest(
        _load(
            "scripts/research/manifests/"
            "j1_r2_one_time_lockbox_manifest_draft_20260722.json"
        ),
        lifecycle,
    )
    readiness = validate_cohort_manifest_readiness(
        _load(
            "claudedocs/research/"
            "j1_r2_relevance_cohort_readiness_after_development_20260723.json"
        ),
        lifecycle,
        [anchor, development, lockbox],
    )

    assert decisions["approval_basis"]["content_modifications"] == []
    assert decisions["approval_basis"][
        "positive_context_negative_mapping"
    ] == "approved_as_sealed"
    assert labels == expected_labels
    assert development == expected_development
    assert decisions["review_decisions_sha256"] == (
        "dc9a25573965979796febbd4d2d974b78065e79360f81e3729266125a66c5652"
    )
    assert labels["development_label_pack_sha256"] == (
        "10773ee23beefc13620477898021d30c34ae4585fc89b5f99b6cb22759325e9d"
    )
    assert development["cohort_manifest_sha256"] == (
        "f93e8c1e975763c8b06d045d905e15a777d95ae1948247e1196ffd8d3a27a982"
    )
    assert readiness["cohort_readiness_sha256"] == (
        "2353d97796211cf77080c683e3a3d540548e98fdb4ce4a27c6c0870ded4aa231"
    )
    assert readiness["development_manifest_gate"] is True
    assert readiness["lockbox_generator_manifest_gate"] is False
    assert readiness["lexical_baseline_execution_gate"] is False
