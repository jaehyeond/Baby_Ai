from __future__ import annotations

import copy
import hashlib
from pathlib import Path
from typing import Any

import pytest

from neural.baby.pending_question_semantics import canonical_json_sha256
from neural.baby.relevance_embedding_baseline import (
    MODEL_ID,
    MODEL_REVISION,
    PHASE,
    REQUIRED_AUTHORIZED_ACTIONS,
    REQUIRED_FORBIDDEN_ACTIONS,
    build_embedding_baseline_artifact,
    embedding_model_contract,
    inspect_local_model_snapshot,
    score_embedding_questions,
    validate_embedding_baseline_artifact,
    validate_embedding_model_decision,
    validate_embedding_snapshot_manifest,
)


def _decision() -> dict[str, Any]:
    contract = embedding_model_contract()
    decision = {
        "embedding_model_decision_version": 1,
        "phase": PHASE,
        "reviewer_role": "user",
        "decision": "approved",
        "reviewed_at": "2026-07-28T00:00:00+00:00",
        "model_id": MODEL_ID,
        "immutable_revision": MODEL_REVISION,
        "embedding_model_contract_sha256": contract[
            "embedding_model_contract_sha256"
        ],
        "authorized_actions": list(REQUIRED_AUTHORIZED_ACTIONS),
        "forbidden_actions": list(REQUIRED_FORBIDDEN_ACTIONS),
        "lockbox_materialization_authorized": False,
        "training_authorized": False,
        "database_write_authorized": False,
    }
    decision["embedding_model_decision_sha256"] = canonical_json_sha256(decision)
    return decision


def _snapshot(decision: dict[str, Any]) -> dict[str, Any]:
    contract = embedding_model_contract()
    files = []
    for expected in contract["expected_files"]:
        actual_sha256 = (
            expected["digest"]
            if expected["verification"] == "sha256"
            else hashlib.sha256(expected["path"].encode("utf-8")).hexdigest()
        )
        files.append(
            {
                "path": expected["path"],
                "size": expected["size"],
                "expected_verification": expected["verification"],
                "expected_digest": expected["digest"],
                "actual_sha256": actual_sha256,
            }
        )
    snapshot = {
        "embedding_snapshot_manifest_version": 1,
        "phase": PHASE,
        "status": "pinned_local_embedding_snapshot_verified",
        "created_at": "2026-07-28T00:00:00+00:00",
        "model_id": MODEL_ID,
        "immutable_revision": MODEL_REVISION,
        "embedding_model_contract_sha256": contract[
            "embedding_model_contract_sha256"
        ],
        "embedding_model_decision_sha256": decision[
            "embedding_model_decision_sha256"
        ],
        "acquisition_method": "huggingface_snapshot_download_pinned_revision",
        "local_path_recorded": False,
        "files": files,
        "total_verified_bytes": contract["expected_total_bytes"],
        "configuration": {
            "model_config_sha256": "1" * 64,
            "pooling_config_sha256": "2" * 64,
            "tokenizer_config_sha256": "3" * 64,
        },
        "database_writes": False,
        "learning_enabled": False,
        "model_weights_changed": False,
        "lockbox_materialized": False,
        "heldout_gate": False,
        "performance_claim_gate": False,
        "production_promotion_gate": False,
    }
    snapshot["embedding_snapshot_manifest_sha256"] = canonical_json_sha256(
        snapshot
    )
    return snapshot


def _inputs() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    question = "빨간 과일은 무엇인가?"
    question_hash = hashlib.sha256(question.encode("utf-8")).hexdigest()
    vocabulary = {
        "candidate_vocabulary_sha256": "a" * 64,
        "eligible_concepts": [
            {"concept_id": "apple", "concept_name": "사과"},
            {"concept_id": "banana", "concept_name": "바나나"},
            {"concept_id": "car", "concept_name": "자동차"},
            {"concept_id": "train", "concept_name": "기차"},
        ],
    }
    spec = {
        "questions": [
            {
                "question_id": "q1",
                "order": 0,
                "question": question,
                "question_sha256": question_hash,
                "closed_world_fact": "사과는 빨간 과일이다.",
            }
        ]
    }
    labels = {
        "entries": [
            {
                "question_id": "q1",
                "question_sha256": question_hash,
                "labels": [
                    {
                        "concept_id": "apple",
                        "label": 1,
                        "partition": "fit_pool",
                    },
                    {
                        "concept_id": "banana",
                        "label": 0,
                        "partition": "fit_pool",
                    },
                    {
                        "concept_id": "car",
                        "label": 0,
                        "partition": "fit_pool",
                    },
                    {
                        "concept_id": "train",
                        "label": 0,
                        "partition": "fit_pool",
                    },
                ],
            }
        ]
    }
    return vocabulary, spec, labels


def _lexical_artifact() -> dict[str, Any]:
    return {
        "baseline_id": "lexical_char_ngram_tfidf_v1",
        "candidate_count": 4,
        "question_count": 1,
        "lexical_baseline_artifact_sha256": "4" * 64,
    }


def _bindings(
    decision: dict[str, Any],
    snapshot: dict[str, Any],
) -> dict[str, Any]:
    return {
        "lexical_baseline_artifact_sha256": "4" * 64,
        "embedding_model_decision_sha256": decision[
            "embedding_model_decision_sha256"
        ],
        "embedding_snapshot_manifest_sha256": snapshot[
            "embedding_snapshot_manifest_sha256"
        ],
        "embedding_model_contract_sha256": embedding_model_contract()[
            "embedding_model_contract_sha256"
        ],
        "implementation_bundle_sha256": "5" * 64,
        "input_file_sha256s": {
            "fixture": "6" * 64,
        },
    }


def _runtime() -> dict[str, Any]:
    return {
        "python_version": "3.12.0",
        "torch_version": "2.0.0",
        "transformers_version": "4.0.0",
        "device": "cpu",
        "dtype": "float32",
        "batch_size": 4,
        "deterministic_algorithms": True,
        "embedding_dimension": 384,
        "model_parameter_count": 117000000,
        "trainable_parameter_count": 0,
        "encoded_batch_count": 2,
        "max_non_padding_tokens": 12,
    }


def _artifact() -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
]:
    vocabulary, spec, labels = _inputs()
    decision = _decision()
    snapshot = _snapshot(decision)
    scores = {
        "q1": [
            {"concept_id": "apple", "score": 0.9},
            {"concept_id": "banana", "score": 0.5},
            {"concept_id": "car", "score": 0.1},
            {"concept_id": "train", "score": 0.0},
        ]
    }
    artifact = build_embedding_baseline_artifact(
        vocabulary,
        spec,
        labels,
        _lexical_artifact(),
        decision,
        snapshot,
        scores,
        bindings=_bindings(decision, snapshot),
        runtime=_runtime(),
        created_at="2026-07-28T00:00:00+00:00",
    )
    return artifact, vocabulary, spec, labels, decision, snapshot


def test_model_contract_pins_official_e5_inference_surface() -> None:
    contract = embedding_model_contract()

    assert contract["model_id"] == MODEL_ID
    assert contract["immutable_revision"] == MODEL_REVISION
    assert contract["embedding_dimension"] == 384
    assert contract["max_length"] == 512
    assert contract["prompt_template"]["query_prefix"] == "query: "
    assert contract["prompt_template"]["candidate_prefix"] == "passage: "
    assert contract["pooling"]["method"] == (
        "attention_mask_mean_pool_last_hidden_state"
    )
    assert contract["loading"]["local_files_only"] is True
    assert contract["loading"]["trust_remote_code"] is False
    assert contract["loading"]["trainable_parameter_count"] == 0


def test_user_decision_is_exact_scope_and_self_hashed() -> None:
    decision = _decision()
    assert validate_embedding_model_decision(decision) == decision

    wrong_reviewer = copy.deepcopy(decision)
    wrong_reviewer["reviewer_role"] = "agent"
    wrong_reviewer["embedding_model_decision_sha256"] = canonical_json_sha256(
        {key: value for key, value in wrong_reviewer.items() if key != "embedding_model_decision_sha256"}
    )
    with pytest.raises(ValueError, match="reviewer_role"):
        validate_embedding_model_decision(wrong_reviewer)


def test_snapshot_manifest_rejects_lfs_digest_substitution() -> None:
    decision = _decision()
    snapshot = _snapshot(decision)
    target = next(
        item for item in snapshot["files"] if item["path"] == "model.safetensors"
    )
    target["actual_sha256"] = "f" * 64
    snapshot["embedding_snapshot_manifest_sha256"] = canonical_json_sha256(
        {
            key: value
            for key, value in snapshot.items()
            if key != "embedding_snapshot_manifest_sha256"
        }
    )
    with pytest.raises(ValueError, match="LFS content"):
        validate_embedding_snapshot_manifest(snapshot, decision)


def test_missing_local_snapshot_fails_before_model_import(tmp_path: Path) -> None:
    missing = tmp_path / "missing-model"
    with pytest.raises(FileNotFoundError, match="local model directory"):
        inspect_local_model_snapshot(
            missing,
            _decision(),
            created_at="2026-07-28T00:00:00+00:00",
            acquisition_method="huggingface_snapshot_download_pinned_revision",
        )


def test_scoring_uses_only_prefixed_question_and_candidate_names() -> None:
    concepts = [
        {"concept_id": "apple", "concept_name": "사과"},
        {"concept_id": "banana", "concept_name": "바나나"},
    ]
    questions = [
        {
            "question_id": "q1",
            "order": 0,
            "question": "빨간 과일",
            "closed_world_fact": "this must never enter the encoder",
        }
    ]
    observed: list[list[str]] = []
    vectors = {
        "passage: 사과": [1.0, 0.0],
        "passage: 바나나": [0.0, 1.0],
        "query: 빨간 과일": [1.0, 0.0],
    }

    def encode(texts: list[str]) -> list[list[float]]:
        observed.append(list(texts))
        return [vectors[text] for text in texts]

    result = score_embedding_questions(concepts, questions, encode)

    assert observed == [
        ["passage: 사과", "passage: 바나나"],
        ["query: 빨간 과일"],
    ]
    assert result["q1"][0]["concept_id"] == "apple"
    assert all("closed_world_fact" not in text for batch in observed for text in batch)


def test_embedding_artifact_recomputes_full_ranking_and_metrics() -> None:
    artifact, vocabulary, spec, labels, decision, snapshot = _artifact()

    assert artifact["candidate_count"] == 4
    assert artifact["question_count"] == 1
    assert artifact["aggregate_metrics"]["macro_recall_at_8"] == 1.0
    assert artifact["questions"][0]["positive_ranks"] == {"apple": 1}
    assert len(artifact["questions"][0]["full_ranked_scores"]) == 4
    assert artifact["embedding_baseline_execution_gate"] is True
    assert artifact["heldout_gate"] is False
    assert artifact["learning_enabled"] is False
    assert (
        validate_embedding_baseline_artifact(
            artifact,
            vocabulary,
            spec,
            labels,
            _lexical_artifact(),
            decision,
            snapshot,
        )
        == artifact
    )


def test_embedding_artifact_rejects_metric_tampering() -> None:
    artifact, vocabulary, spec, labels, decision, snapshot = _artifact()
    artifact["aggregate_metrics"]["macro_mrr"] = 0.0

    with pytest.raises(ValueError, match="sha256 mismatch"):
        validate_embedding_baseline_artifact(
            artifact,
            vocabulary,
            spec,
            labels,
            _lexical_artifact(),
            decision,
            snapshot,
        )


def test_embedding_artifact_requires_every_candidate_score() -> None:
    vocabulary, spec, labels = _inputs()
    decision = _decision()
    snapshot = _snapshot(decision)
    incomplete = {
        "q1": [
            {"concept_id": "apple", "score": 0.9},
            {"concept_id": "banana", "score": 0.5},
        ]
    }
    with pytest.raises(ValueError, match="full candidate vocabulary"):
        build_embedding_baseline_artifact(
            vocabulary,
            spec,
            labels,
            _lexical_artifact(),
            decision,
            snapshot,
            incomplete,
            bindings=_bindings(decision, snapshot),
            runtime=_runtime(),
            created_at="2026-07-28T00:00:00+00:00",
        )


def test_embedding_artifact_rejects_nonfrozen_runtime() -> None:
    vocabulary, spec, labels = _inputs()
    decision = _decision()
    snapshot = _snapshot(decision)
    scores = {
        "q1": [
            {"concept_id": "apple", "score": 0.9},
            {"concept_id": "banana", "score": 0.5},
            {"concept_id": "car", "score": 0.1},
            {"concept_id": "train", "score": 0.0},
        ]
    }
    runtime = _runtime()
    runtime["trainable_parameter_count"] = 1

    with pytest.raises(ValueError, match="trainable_parameter_count"):
        build_embedding_baseline_artifact(
            vocabulary,
            spec,
            labels,
            _lexical_artifact(),
            decision,
            snapshot,
            scores,
            bindings=_bindings(decision, snapshot),
            runtime=runtime,
            created_at="2026-07-28T00:00:00+00:00",
        )
