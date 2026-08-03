from copy import deepcopy
import json
from pathlib import Path

import pytest

from neural.baby.pending_question_semantics import canonical_json_sha256
from neural.baby.relevance_cohort_lifecycle import (
    build_anchor_manifest,
    build_cohort_manifest_readiness,
    build_planned_generator_manifest,
    build_relevance_cohort_lifecycle_contract,
    seal_cohort_manifest,
    validate_cohort_manifest,
    validate_cohort_manifest_readiness,
    validate_relevance_cohort_lifecycle_contract,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TIMESTAMP = "2026-07-22T06:00:00+00:00"


def _load(relative_path: str) -> dict:
    return json.loads(
        (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")
    )


def _inputs() -> tuple[dict, str, list[str]]:
    r1 = _load(
        "claudedocs/research/j1_r1_relevance_scorer_contract_20260722.json"
    )
    vocabulary = _load(
        "scripts/research/inputs/"
        "j1_1_candidate_vocabulary_v2_20260716.json"
    )
    legacy_manifest = _load(
        "scripts/research/manifests/j1_1_train_calibration_a_20260716.json"
    )
    question_hashes = [
        question["question_sha256"] for question in legacy_manifest["questions"]
    ]
    return r1, vocabulary["graph_snapshot_sha256"], question_hashes


def _lifecycle() -> dict:
    r1, graph_snapshot_sha256, question_hashes = _inputs()
    return build_relevance_cohort_lifecycle_contract(
        r1,
        graph_snapshot_sha256=graph_snapshot_sha256,
        legacy_question_hashes=question_hashes,
        created_at=TIMESTAMP,
    )


def _manifests() -> tuple[dict, dict, dict]:
    lifecycle = _lifecycle()
    return (
        build_anchor_manifest(lifecycle, created_at=TIMESTAMP),
        build_planned_generator_manifest(
            lifecycle,
            role="rolling_development",
            cohort_id="development-test-0001",
            cohort_generation_id="development-generation-test-0001",
            created_at=TIMESTAMP,
        ),
        build_planned_generator_manifest(
            lifecycle,
            role="one_time_lockbox",
            cohort_id="lockbox-test-0001",
            cohort_generation_id="lockbox-generation-test-0001",
            created_at=TIMESTAMP,
        ),
    )


def _reseal_lifecycle(payload: dict) -> dict:
    payload = deepcopy(payload)
    payload.pop("cohort_lifecycle_contract_sha256", None)
    payload["cohort_lifecycle_contract_sha256"] = canonical_json_sha256(payload)
    return payload


def test_lifecycle_limits_cohorts_to_evaluation_evidence() -> None:
    lifecycle = _lifecycle()
    boundary = lifecycle["learning_evaluation_boundary"]

    assert lifecycle["research_goal"]["system"] == (
        "source_aware_grounded_developmental_self_improvement"
    )
    assert boundary["cohort_scope"] == "evaluation_evidence_only"
    assert boundary["live_growth_stream_blocked_by_contract"] is False
    assert boundary["live_graph_updates_blocked_by_contract"] is False
    assert boundary["live_memory_consolidation_blocked_by_contract"] is False
    assert boundary["live_curiosity_generation_blocked_by_contract"] is False
    assert lifecycle["evaluation_epoch"]["partition_scope"] == (
        "this_evaluation_epoch_only"
    )


def test_lifecycle_releases_only_consumed_labels_to_next_generation() -> None:
    lifecycle = _lifecycle()
    boundary = lifecycle["learning_evaluation_boundary"]

    assert boundary["reserved_item"] == (
        "supervised_benchmark_label_not_live_concept"
    )
    assert boundary["reserved_labels_release_after_consumption"] is True
    assert boundary["released_labels_may_train_only_next_generation"] is True
    assert lifecycle["lifecycle_state_machine"]["lockbox_reopen_allowed"] is False


def test_anchor_is_reusable_regression_data_not_heldout_evidence() -> None:
    anchor, _, _ = _manifests()

    assert anchor["role"] == "anchor_regression"
    assert anchor["materialization"]["question_count"] == 6
    assert anchor["usage"]["reusable"] is True
    assert anchor["usage"]["heldout_claim_allowed"] is False
    assert anchor["performance_claim_gate"] is False


def test_planned_development_and_lockbox_do_not_fake_question_data() -> None:
    _, development, lockbox = _manifests()

    for manifest in (development, lockbox):
        assert manifest["review_status"] == "awaiting_user_review"
        assert manifest["materialization"]["materialized"] is False
        assert manifest["materialization"]["question_count"] == 0
        assert manifest["materialization"]["question_hashes"] == []
        assert manifest["execution_gate"] is False
    assert development["usage"]["model_selection_allowed"] is True
    assert lockbox["materialization"]["plaintext_questions_in_repository"] is False
    assert lockbox["usage"]["one_time_open"] is True
    assert lockbox["generator"]["seed_policy"] == (
        "hidden_seed_sampled_after_model_freeze"
    )


def test_draft_bundle_keeps_lexical_baseline_blocked() -> None:
    lifecycle = _lifecycle()
    readiness = build_cohort_manifest_readiness(lifecycle, _manifests())

    assert readiness["anchor_manifest_gate"] is True
    assert readiness["development_manifest_gate"] is False
    assert readiness["lockbox_generator_manifest_gate"] is False
    assert readiness["lexical_baseline_execution_gate"] is False
    assert readiness["live_learning_blocked"] is False
    assert len(readiness["cohort_readiness_sha256"]) == 64


def test_validator_rejects_resealed_live_learning_block() -> None:
    lifecycle = _lifecycle()
    anchor, _, _ = _manifests()
    anchor["live_learning_blocked"] = True
    anchor = seal_cohort_manifest(anchor)

    with pytest.raises(ValueError, match="cannot block the live learning stream"):
        validate_cohort_manifest(anchor, lifecycle)


def test_validator_rejects_resealed_lockbox_plaintext() -> None:
    lifecycle = _lifecycle()
    _, _, lockbox = _manifests()
    lockbox["materialization"]["plaintext_questions_in_repository"] = True
    lockbox = seal_cohort_manifest(lockbox)

    with pytest.raises(ValueError, match="lockbox plaintext"):
        validate_cohort_manifest(lockbox, lifecycle)


def test_bundle_rejects_question_overlap_across_roles() -> None:
    lifecycle = _lifecycle()
    anchor, development, lockbox = _manifests()
    duplicate_hash = anchor["materialization"]["question_hashes"][0]
    development["materialization"] = {
        "materialized": True,
        "question_count": 1,
        "question_hashes": [duplicate_hash],
        "question_set_sha256": canonical_json_sha256([duplicate_hash]),
        "plaintext_questions_in_repository": True,
    }
    development = seal_cohort_manifest(development)

    with pytest.raises(ValueError, match="overlap across roles"):
        build_cohort_manifest_readiness(
            lifecycle, [anchor, development, lockbox]
        )


def test_lifecycle_validator_rejects_resealed_growth_freeze() -> None:
    lifecycle = _lifecycle()
    lifecycle["learning_evaluation_boundary"][
        "live_growth_stream_blocked_by_contract"
    ] = True
    lifecycle = _reseal_lifecycle(lifecycle)
    r1, graph_snapshot_sha256, question_hashes = _inputs()

    with pytest.raises(ValueError, match="does not match bound inputs"):
        validate_relevance_cohort_lifecycle_contract(
            lifecycle,
            r1,
            graph_snapshot_sha256=graph_snapshot_sha256,
            legacy_question_hashes=question_hashes,
        )


def test_readiness_validator_rejects_self_hash_tamper() -> None:
    lifecycle = _lifecycle()
    manifests = _manifests()
    readiness = build_cohort_manifest_readiness(lifecycle, manifests)
    readiness["next_step"] = "run_lexical_baseline"

    with pytest.raises(ValueError, match="cohort_readiness_sha256 mismatch"):
        validate_cohort_manifest_readiness(readiness, lifecycle, manifests)


def test_repository_j1_r2_artifacts_validate() -> None:
    r1, graph_snapshot_sha256, question_hashes = _inputs()
    lifecycle = validate_relevance_cohort_lifecycle_contract(
        _load(
            "claudedocs/research/"
            "j1_r2_relevance_cohort_lifecycle_20260722.json"
        ),
        r1,
        graph_snapshot_sha256=graph_snapshot_sha256,
        legacy_question_hashes=question_hashes,
    )
    manifests = (
        _load(
            "scripts/research/manifests/"
            "j1_r2_anchor_regression_manifest_20260722.json"
        ),
        _load(
            "scripts/research/manifests/"
            "j1_r2_rolling_development_manifest_draft_20260722.json"
        ),
        _load(
            "scripts/research/manifests/"
            "j1_r2_one_time_lockbox_manifest_draft_20260722.json"
        ),
    )
    readiness = validate_cohort_manifest_readiness(
        _load(
            "claudedocs/research/"
            "j1_r2_relevance_cohort_readiness_20260722.json"
        ),
        lifecycle,
        manifests,
    )

    assert lifecycle["cohort_lifecycle_contract_sha256"] == (
        "2ab4cf1edc5a97063d3cf540ff20620f645a7ff494bffb008cef84240577ce32"
    )
    assert readiness["cohort_readiness_sha256"] == (
        "6beb8b98795cff0387a0980fdf3a4422d138c38d49c0b09da4b427f28a73e1f6"
    )
    assert readiness["anchor_manifest_gate"] is True
    assert readiness["lexical_baseline_execution_gate"] is False
