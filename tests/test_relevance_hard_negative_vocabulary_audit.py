from __future__ import annotations

import copy
import hashlib
from typing import Any

import pytest

from neural.baby.pending_question_semantics import canonical_json_sha256
from neural.baby.relevance_hard_negative_vocabulary_audit import (
    RELEVANCE_REVIEW_DECISIONS,
    VOCABULARY_REVIEW_DECISIONS,
    build_hard_negative_vocabulary_outputs,
    validate_hard_negative_review_packet,
    validate_hard_negative_vocabulary_audit,
)


def _with_self_hash(
    payload: dict[str, Any],
    field: str,
) -> dict[str, Any]:
    payload[field] = canonical_json_sha256(payload)
    return payload


def _fixtures(
    *,
    positive_rank: int = 9,
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
]:
    concepts = [
        {"concept_id": "c01", "concept_name": "오답1"},
        {"concept_id": "c02", "concept_name": "오답2"},
        {"concept_id": "c03", "concept_name": "그래프에서."},
        {"concept_id": "c04", "concept_name": "그래프에서"},
        {"concept_id": "c05", "concept_name": "DUP"},
        {"concept_id": "c06", "concept_name": "dup"},
        {"concept_id": "c07", "concept_name": "근접1"},
        {"concept_id": "c08", "concept_name": "근접2"},
        {"concept_id": "p", "concept_name": "정답"},
        {"concept_id": "c09", "concept_name": "근접3"},
        {"concept_id": "c10", "concept_name": "근접4"},
        {"concept_id": "n", "concept_name": "명시음성"},
    ]
    vocabulary = _with_self_hash(
        {
            "candidate_vocabulary_version": 2,
            "eligible_concept_count": len(concepts),
            "eligible_concepts": concepts,
        },
        "candidate_vocabulary_sha256",
    )
    question = "정답 개념은 무엇인가?"
    question_sha256 = hashlib.sha256(question.encode("utf-8")).hexdigest()
    generator_spec = _with_self_hash(
        {
            "questions": [
                {
                    "question_id": "q1",
                    "order": 0,
                    "question": question,
                    "question_sha256": question_sha256,
                }
            ]
        },
        "generator_spec_sha256",
    )
    label_pack = _with_self_hash(
        {
            "entries": [
                {
                    "question_id": "q1",
                    "question_sha256": question_sha256,
                    "context_concepts_unscored": [
                        {
                            "concept_id": "c08",
                            "concept_name": "근접2",
                            "partition": "fit_pool",
                        }
                    ],
                    "labels": [
                        {
                            "concept_id": "p",
                            "concept_name": "정답",
                            "label": 1,
                            "partition": "fit_pool",
                        },
                        {
                            "concept_id": "n",
                            "concept_name": "명시음성",
                            "label": 0,
                            "partition": "fit_pool",
                        },
                    ],
                }
            ]
        },
        "development_label_pack_sha256",
    )

    base_order = [
        "c01",
        "c02",
        "c03",
        "c04",
        "c05",
        "c06",
        "c07",
        "c08",
        "p",
        "c09",
        "c10",
        "n",
    ]
    base_order.remove("p")
    base_order.insert(positive_rank - 1, "p")
    score_rows = [
        {
            "concept_id": concept_id,
            "score": round(0.99 - (index * 0.01), 12),
        }
        for index, concept_id in enumerate(base_order)
    ]
    rank_by_id = {
        item["concept_id"]: rank
        for rank, item in enumerate(score_rows, start=1)
    }
    score_by_id = {item["concept_id"]: item["score"] for item in score_rows}
    embedding = {
        "embedding_baseline_artifact_version": 1,
        "phase": "J1-R2-E2",
        "status": (
            "development_frozen_embedding_baseline_completed_not_for_claim"
        ),
        "candidate_count": len(concepts),
        "question_count": 1,
        "questions": [
            {
                "question_id": "q1",
                "question_sha256": question_sha256,
                "target_partition": "fit_pool",
                "positive_concept_ids": ["p"],
                "positive_ranks": {"p": rank_by_id["p"]},
                "positive_scores": {"p": score_by_id["p"]},
                "reviewed_pool": [
                    {
                        "concept_id": "p",
                        "label": 1,
                        "score": score_by_id["p"],
                        "full_vocabulary_rank": rank_by_id["p"],
                    },
                    {
                        "concept_id": "n",
                        "label": 0,
                        "score": score_by_id["n"],
                        "full_vocabulary_rank": rank_by_id["n"],
                    },
                ],
                "full_ranking_sha256": canonical_json_sha256(score_rows),
                "full_ranked_scores": score_rows,
            }
        ],
        "database_writes": False,
        "learning_enabled": False,
        "heldout_gate": False,
        "performance_claim_gate": False,
        "production_promotion_gate": False,
    }
    embedding["embedding_baseline_artifact_sha256"] = canonical_json_sha256(
        embedding
    )
    return vocabulary, generator_spec, label_pack, embedding


def _bindings(
    vocabulary: dict[str, Any],
    generator_spec: dict[str, Any],
    label_pack: dict[str, Any],
    embedding: dict[str, Any],
) -> dict[str, Any]:
    return {
        "candidate_vocabulary_sha256": vocabulary[
            "candidate_vocabulary_sha256"
        ],
        "generator_spec_sha256": generator_spec["generator_spec_sha256"],
        "development_label_pack_sha256": label_pack[
            "development_label_pack_sha256"
        ],
        "embedding_baseline_artifact_sha256": embedding[
            "embedding_baseline_artifact_sha256"
        ],
        "implementation_bundle_sha256": "a" * 64,
        "input_file_sha256s": {"fixture": "b" * 64},
    }


def _outputs(
    *,
    positive_rank: int = 9,
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
]:
    vocabulary, spec, labels, embedding = _fixtures(
        positive_rank=positive_rank
    )
    bindings = _bindings(vocabulary, spec, labels, embedding)
    packet, audit = build_hard_negative_vocabulary_outputs(
        vocabulary,
        spec,
        labels,
        embedding,
        bindings=bindings,
        created_at="2026-07-28T00:00:00+00:00",
    )
    return vocabulary, spec, labels, embedding, bindings, packet, audit


def test_selects_top_unjudged_and_positive_neighbors_without_labels() -> None:
    _, _, _, _, _, packet, audit = _outputs()

    candidates = packet["questions"][0]["review_candidates"]
    selected_ids = {item["concept_id"] for item in candidates}
    assert {"c01", "c02", "c03", "c04", "c05"}.issubset(selected_ids)
    assert {"c07", "c08", "c09", "c10"}.issubset(selected_ids)
    assert "p" not in selected_ids
    assert "n" not in selected_ids
    assert len(candidates) == 9
    assert all(item["current_label_status"] == "unjudged" for item in candidates)
    assert all(item["relevance_review_decision"] is None for item in candidates)
    assert all(item["vocabulary_review_decision"] is None for item in candidates)
    assert audit["selection_summary"]["auto_assigned_hard_negative_count"] == 0


def test_machine_flags_are_review_cues_not_vocabulary_labels() -> None:
    _, _, _, _, _, packet, audit = _outputs()

    quality = audit["vocabulary_quality"]
    assert quality["normalized_surface_collision_group_count"] == 1
    assert quality["boundary_punctuation_variant_group_count"] == 1
    by_id = {
        item["concept_id"]: item
        for item in packet["questions"][0]["review_candidates"]
    }
    assert "boundary_punctuation" in by_id["c03"]["machine_surface_flags"]
    assert "boundary_punctuation_variant" in by_id["c03"][
        "machine_surface_flags"
    ]
    assert "normalized_surface_collision" in by_id["c05"][
        "machine_surface_flags"
    ]
    assert packet["decision_contract"]["machine_surface_flags_are_labels"] is False


def test_relevance_and_vocabulary_decisions_are_separate_axes() -> None:
    _, _, _, _, _, packet, _ = _outputs()

    contract = packet["decision_contract"]
    assert tuple(contract["relevance_review_decisions"]) == (
        RELEVANCE_REVIEW_DECISIONS
    )
    assert tuple(contract["vocabulary_review_decisions"]) == (
        VOCABULARY_REVIEW_DECISIONS
    )
    assert contract["relevance_and_vocabulary_are_separate_axes"] is True
    assert "context" in contract["relevance_review_decisions"]


def test_positive_neighbors_are_not_added_for_top8_success() -> None:
    _, _, _, _, _, packet, _ = _outputs(positive_rank=2)

    candidates = packet["questions"][0]["review_candidates"]
    assert len(candidates) == 5
    assert all(
        item["selection_reasons"] == ["top_unjudged"] for item in candidates
    )
    assert packet["questions"][0]["retrieval_status"] == "positive_in_top_8"


def test_packet_tamper_is_rejected() -> None:
    vocabulary, spec, labels, embedding, bindings, packet, _ = _outputs()
    tampered = copy.deepcopy(packet)
    tampered["questions"][0]["review_candidates"][0][
        "relevance_review_decision"
    ] = "hard_negative"
    tampered["hard_negative_review_packet_sha256"] = canonical_json_sha256(
        {
            key: value
            for key, value in tampered.items()
            if key != "hard_negative_review_packet_sha256"
        }
    )

    with pytest.raises(ValueError, match="does not match sealed inputs"):
        validate_hard_negative_review_packet(
            tampered,
            vocabulary,
            spec,
            labels,
            embedding,
            expected_bindings=bindings,
        )


def test_audit_tamper_is_rejected() -> None:
    vocabulary, spec, labels, embedding, bindings, packet, audit = _outputs()
    tampered = copy.deepcopy(audit)
    tampered["selection_summary"]["auto_assigned_hard_negative_count"] = 1
    tampered["hard_negative_vocabulary_audit_sha256"] = canonical_json_sha256(
        {
            key: value
            for key, value in tampered.items()
            if key != "hard_negative_vocabulary_audit_sha256"
        }
    )

    with pytest.raises(ValueError, match="does not match sealed inputs"):
        validate_hard_negative_vocabulary_audit(
            tampered,
            packet,
            vocabulary,
            spec,
            labels,
            embedding,
            expected_bindings=bindings,
        )


def test_question_drift_is_rejected_before_candidate_selection() -> None:
    vocabulary, spec, labels, embedding = _fixtures()
    spec["questions"][0]["question"] = "바뀐 질문"
    spec["generator_spec_sha256"] = canonical_json_sha256(
        {
            key: value
            for key, value in spec.items()
            if key != "generator_spec_sha256"
        }
    )

    with pytest.raises(ValueError, match="question hash mismatch"):
        build_hard_negative_vocabulary_outputs(
            vocabulary,
            spec,
            labels,
            embedding,
            bindings=_bindings(vocabulary, spec, labels, embedding),
            created_at="2026-07-28T00:00:00+00:00",
        )


def test_binding_drift_is_rejected_on_reaudit() -> None:
    vocabulary, spec, labels, embedding, bindings, packet, _ = _outputs()
    changed_bindings = copy.deepcopy(bindings)
    changed_bindings["implementation_bundle_sha256"] = "c" * 64

    with pytest.raises(ValueError, match="does not match sealed inputs"):
        validate_hard_negative_review_packet(
            packet,
            vocabulary,
            spec,
            labels,
            embedding,
            expected_bindings=changed_bindings,
        )


def test_all_downstream_action_gates_remain_false() -> None:
    _, _, _, _, _, packet, audit = _outputs()

    for payload in (packet, audit):
        assert payload["review_complete_gate"] is False
        assert payload["training_data_materialization_gate"] is False
        assert payload["database_write_gate"] is False
        assert payload["learned_head_fit_gate"] is False
        assert payload["heldout_gate"] is False
        assert payload["performance_claim_gate"] is False
        assert payload["production_promotion_gate"] is False
