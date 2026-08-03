from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from neural.baby.relevance_lexical_baseline import (
    build_lexical_baseline_artifact,
    build_lexical_index,
    character_ngram_counts,
    normalize_lexical_text,
    score_lexical_question,
    validate_lexical_baseline_artifact,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _load(relative_path: str) -> dict:
    return json.loads((PROJECT_ROOT / relative_path).read_text(encoding="utf-8"))


def _repository_inputs() -> tuple[dict, dict, dict]:
    return (
        _load(
            "scripts/research/inputs/"
            "j1_1_candidate_vocabulary_v2_20260716.json"
        ),
        _load(
            "scripts/research/specs/"
            "j1_r2_rolling_development_generator_spec_draft_20260723.json"
        ),
        _load(
            "scripts/research/inputs/"
            "j1_r2_rolling_development_labels_reviewed_20260723.json"
        ),
    )


def _bindings(vocabulary: dict) -> dict:
    digest = "a" * 64
    return {
        "candidate_vocabulary_sha256": vocabulary[
            "candidate_vocabulary_sha256"
        ],
        "r1_contract_sha256": digest,
        "cohort_lifecycle_contract_sha256": digest,
        "development_label_pack_sha256": digest,
        "development_manifest_sha256": digest,
        "lockbox_generator_manifest_sha256": digest,
        "cohort_readiness_sha256": digest,
        "implementation_bundle_sha256": digest,
        "input_file_sha256s": {"test": digest},
    }


def test_normalization_contract_is_unicode_and_whitespace_stable() -> None:
    assert normalize_lexical_text("  ＡBC\t서울\n") == "abc 서울"
    assert character_ngram_counts("가나", min_n=2, max_n=2) == {"가나": 1}


def test_index_and_ranking_are_deterministic_with_concept_id_ties() -> None:
    concepts = [
        {"concept_id": "b", "concept_name": "서울"},
        {"concept_id": "a", "concept_name": "부산"},
        {"concept_id": "c", "concept_name": "서울시"},
    ]
    index = build_lexical_index(concepts)
    first = score_lexical_question(index, "서울")
    second = score_lexical_question(index, "서울")
    assert first == second
    assert first[0]["concept_id"] == "b"

    zero_scores = score_lexical_question(index, "xyz")
    assert [item["concept_id"] for item in zero_scores] == ["a", "b", "c"]
    assert all(item["score"] == 0.0 for item in zero_scores)


def test_repository_artifact_ranks_full_vocabulary_without_learning() -> None:
    vocabulary, spec, labels = _repository_inputs()
    artifact = build_lexical_baseline_artifact(
        vocabulary,
        spec,
        labels,
        bindings=_bindings(vocabulary),
        created_at="2026-07-28T00:00:00+00:00",
    )
    assert artifact["candidate_count"] == 1069
    assert artifact["question_count"] == 12
    assert artifact["database_writes"] is False
    assert artifact["learning_enabled"] is False
    assert artifact["external_api_used"] is False
    assert artifact["lockbox_materialized"] is False
    assert artifact["performance_claim_gate"] is False
    assert len(artifact["questions"][0]["top_ranked_concepts"]) == 20
    validate_lexical_baseline_artifact(artifact, vocabulary, spec, labels)


def test_closed_world_fact_is_not_a_question_feature() -> None:
    vocabulary, spec, labels = _repository_inputs()
    original = build_lexical_baseline_artifact(
        vocabulary,
        spec,
        labels,
        bindings=_bindings(vocabulary),
        created_at="2026-07-28T00:00:00+00:00",
    )
    changed_spec = copy.deepcopy(spec)
    for item in changed_spec["questions"]:
        item["closed_world_fact"] = "정답을 반복해도 scorer 입력이 아니다."
    changed = build_lexical_baseline_artifact(
        vocabulary,
        changed_spec,
        labels,
        bindings=_bindings(vocabulary),
        created_at="2026-07-28T00:00:00+00:00",
    )
    assert original["aggregate_metrics"] == changed["aggregate_metrics"]
    assert original["questions"] == changed["questions"]


def test_artifact_validator_rejects_metric_tampering() -> None:
    vocabulary, spec, labels = _repository_inputs()
    artifact = build_lexical_baseline_artifact(
        vocabulary,
        spec,
        labels,
        bindings=_bindings(vocabulary),
        created_at="2026-07-28T00:00:00+00:00",
    )
    artifact["aggregate_metrics"]["macro_mrr"] = 1.0
    with pytest.raises(ValueError, match="sha256 mismatch"):
        validate_lexical_baseline_artifact(artifact, vocabulary, spec, labels)

