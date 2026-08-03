"""Read-only hard-negative and graph-vocabulary audit for J1-R2-E3.

The module consumes the sealed development embedding result. It selects
review candidates without assigning labels and computes only deterministic
surface-form diagnostics. It has no model, database, or runtime dependencies.
"""

from __future__ import annotations

import hashlib
import math
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime
from typing import Any, Mapping, Sequence

from neural.baby.pending_question_semantics import canonical_json_sha256


PHASE = "J1-R2-E3"
AUDIT_ARTIFACT_VERSION = 1
REVIEW_PACKET_VERSION = 1
TOP_UNJUDGED_PER_QUESTION = 5
POSITIVE_NEIGHBOR_RADIUS = 2
EVALUATION_K = 8

RELEVANCE_REVIEW_DECISIONS = (
    "positive",
    "context",
    "hard_negative",
    "unrelated_negative",
    "uncertain",
)
VOCABULARY_REVIEW_DECISIONS = (
    "canonical",
    "alias",
    "fragment",
    "malformed",
    "uncertain",
)

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _require_sha256(value: Any, field: str) -> str:
    normalized = str(value or "")
    if not _SHA256_RE.fullmatch(normalized):
        raise ValueError(f"{field} must be a lowercase SHA-256")
    return normalized


def _validate_created_at(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("created_at must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise ValueError("created_at must include a timezone")
    return value


def _validate_self_hash(
    payload: Mapping[str, Any],
    field: str,
) -> str:
    supplied = _require_sha256(payload.get(field), field)
    unhashed = dict(payload)
    unhashed.pop(field, None)
    if supplied != canonical_json_sha256(unhashed):
        raise ValueError(f"{field} mismatch")
    return supplied


def _question_hash(question: str) -> str:
    return hashlib.sha256(question.encode("utf-8")).hexdigest()


def _review_candidate_id(question_id: str, concept_id: str) -> str:
    return hashlib.sha256(
        f"{question_id}\0{concept_id}".encode("utf-8")
    ).hexdigest()


def _is_punctuation(character: str) -> bool:
    return unicodedata.category(character).startswith("P")


def _surface_key(name: str) -> str:
    normalized = unicodedata.normalize("NFKC", name).casefold()
    return " ".join(normalized.split())


def _boundary_key(surface_key: str) -> str:
    start = 0
    end = len(surface_key)
    while start < end and _is_punctuation(surface_key[start]):
        start += 1
    while end > start and _is_punctuation(surface_key[end - 1]):
        end -= 1
    return surface_key[start:end].strip()


def _base_surface_flags(name: str, surface_key: str) -> list[str]:
    flags: list[str] = []
    if not surface_key:
        flags.append("empty_after_nfkc_casefold")
    if name != name.strip():
        flags.append("leading_or_trailing_whitespace")
    if any(character in "\r\n" for character in name):
        flags.append("contains_line_break")
    if any(
        unicodedata.category(character) in {"Cc", "Cf"} for character in name
    ):
        flags.append("contains_control_or_format_character")
    if surface_key and (
        _is_punctuation(surface_key[0])
        or _is_punctuation(surface_key[-1])
    ):
        flags.append("boundary_punctuation")
    return flags


def _vocabulary_analysis(
    concepts: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    profiles: dict[str, dict[str, Any]] = {}
    normalized_groups: dict[str, list[str]] = defaultdict(list)
    boundary_groups: dict[str, list[str]] = defaultdict(list)

    for item in concepts:
        concept_id = str(item.get("concept_id") or "")
        concept_name = str(item.get("concept_name") or "")
        if not concept_id or concept_id in profiles:
            raise ValueError("candidate vocabulary has a missing or duplicate concept_id")
        surface_key = _surface_key(concept_name)
        boundary_key = _boundary_key(surface_key)
        profiles[concept_id] = {
            "concept_id": concept_id,
            "concept_name": concept_name,
            "normalized_surface_key": surface_key,
            "boundary_punctuation_key": boundary_key,
            "machine_surface_flags": _base_surface_flags(
                concept_name,
                surface_key,
            ),
        }
        normalized_groups[surface_key].append(concept_id)
        if boundary_key:
            boundary_groups[boundary_key].append(concept_id)

    normalized_collision_groups = []
    for surface_key, concept_ids in sorted(normalized_groups.items()):
        if len(concept_ids) < 2:
            continue
        sorted_ids = sorted(concept_ids)
        normalized_collision_groups.append(
            {
                "normalized_surface_key": surface_key,
                "member_count": len(sorted_ids),
                "members": [
                    {
                        "concept_id": concept_id,
                        "concept_name": profiles[concept_id]["concept_name"],
                    }
                    for concept_id in sorted_ids
                ],
            }
        )
        for concept_id in sorted_ids:
            profiles[concept_id]["machine_surface_flags"].append(
                "normalized_surface_collision"
            )

    boundary_variant_groups = []
    for boundary_key, concept_ids in sorted(boundary_groups.items()):
        distinct_surface_keys = {
            profiles[concept_id]["normalized_surface_key"]
            for concept_id in concept_ids
        }
        if len(concept_ids) < 2 or len(distinct_surface_keys) < 2:
            continue
        sorted_ids = sorted(concept_ids)
        boundary_variant_groups.append(
            {
                "boundary_punctuation_key": boundary_key,
                "member_count": len(sorted_ids),
                "members": [
                    {
                        "concept_id": concept_id,
                        "concept_name": profiles[concept_id]["concept_name"],
                        "normalized_surface_key": profiles[concept_id][
                            "normalized_surface_key"
                        ],
                    }
                    for concept_id in sorted_ids
                ],
            }
        )
        for concept_id in sorted_ids:
            profiles[concept_id]["machine_surface_flags"].append(
                "boundary_punctuation_variant"
            )

    flag_counts: Counter[str] = Counter()
    flagged_concepts = []
    for concept_id in sorted(profiles):
        profile = profiles[concept_id]
        profile["machine_surface_flags"] = sorted(
            set(profile["machine_surface_flags"])
        )
        flag_counts.update(profile["machine_surface_flags"])
        if profile["machine_surface_flags"]:
            flagged_concepts.append(dict(profile))

    summary = {
        "candidate_count": len(profiles),
        "flagged_concept_count": len(flagged_concepts),
        "machine_surface_flag_counts": dict(sorted(flag_counts.items())),
        "normalized_surface_collision_group_count": len(
            normalized_collision_groups
        ),
        "boundary_punctuation_variant_group_count": len(
            boundary_variant_groups
        ),
        "normalized_surface_collision_groups": normalized_collision_groups,
        "boundary_punctuation_variant_groups": boundary_variant_groups,
        "flagged_concepts": flagged_concepts,
        "interpretation": (
            "machine flags are deterministic review cues, not automatic "
            "vocabulary-quality labels"
        ),
    }
    return profiles, summary


def _validate_upstream(
    vocabulary: Mapping[str, Any],
    generator_spec: Mapping[str, Any],
    label_pack: Mapping[str, Any],
    embedding_artifact: Mapping[str, Any],
) -> tuple[
    list[dict[str, str]],
    list[Mapping[str, Any]],
    dict[str, Mapping[str, Any]],
    dict[str, Mapping[str, Any]],
]:
    _validate_self_hash(vocabulary, "candidate_vocabulary_sha256")
    _validate_self_hash(generator_spec, "generator_spec_sha256")
    _validate_self_hash(label_pack, "development_label_pack_sha256")
    _validate_self_hash(
        embedding_artifact,
        "embedding_baseline_artifact_sha256",
    )

    if embedding_artifact.get("phase") != "J1-R2-E2":
        raise ValueError("unexpected embedding predecessor phase")
    if embedding_artifact.get("status") != (
        "development_frozen_embedding_baseline_completed_not_for_claim"
    ):
        raise ValueError("embedding predecessor is not the sealed development result")
    for field in (
        "database_writes",
        "learning_enabled",
        "heldout_gate",
        "performance_claim_gate",
        "production_promotion_gate",
    ):
        if embedding_artifact.get(field) is not False:
            raise ValueError(f"embedding predecessor {field} must remain false")

    raw_concepts = vocabulary.get("eligible_concepts") or []
    concepts = sorted(
        (
            {
                "concept_id": str(item.get("concept_id") or ""),
                "concept_name": str(item.get("concept_name") or ""),
            }
            for item in raw_concepts
        ),
        key=lambda item: item["concept_id"],
    )
    concept_ids = {item["concept_id"] for item in concepts}
    if (
        len(concepts) != int(vocabulary.get("eligible_concept_count") or 0)
        or len(concept_ids) != len(concepts)
        or "" in concept_ids
    ):
        raise ValueError("candidate vocabulary count or IDs are invalid")
    if int(embedding_artifact.get("candidate_count") or 0) != len(concepts):
        raise ValueError("embedding candidate count does not match vocabulary")

    questions = sorted(
        generator_spec.get("questions") or [],
        key=lambda item: int(item.get("order")),
    )
    labels_by_question = {
        str(item.get("question_id") or ""): item
        for item in label_pack.get("entries") or []
    }
    embedding_by_question = {
        str(item.get("question_id") or ""): item
        for item in embedding_artifact.get("questions") or []
    }
    question_ids = {str(item.get("question_id") or "") for item in questions}
    if (
        len(question_ids) != len(questions)
        or set(labels_by_question) != question_ids
        or set(embedding_by_question) != question_ids
    ):
        raise ValueError("question sets do not match across sealed inputs")

    for question_item in questions:
        question_id = str(question_item.get("question_id") or "")
        question = str(question_item.get("question") or "")
        question_sha256 = _question_hash(question)
        if question_sha256 != question_item.get("question_sha256"):
            raise ValueError(f"question hash mismatch: {question_id}")
        label_entry = labels_by_question[question_id]
        embedding_entry = embedding_by_question[question_id]
        if (
            label_entry.get("question_sha256") != question_sha256
            or embedding_entry.get("question_sha256") != question_sha256
        ):
            raise ValueError(f"question binding mismatch: {question_id}")

        labels = list(label_entry.get("labels") or [])
        reviewed_by_id = {
            str(item.get("concept_id") or ""): int(item.get("label"))
            for item in labels
        }
        if (
            len(reviewed_by_id) != len(labels)
            or not set(reviewed_by_id).issubset(concept_ids)
            or any(label not in (0, 1) for label in reviewed_by_id.values())
        ):
            raise ValueError(f"reviewed labels are invalid: {question_id}")
        embedding_reviewed = {
            str(item.get("concept_id") or ""): int(item.get("label"))
            for item in embedding_entry.get("reviewed_pool") or []
        }
        if reviewed_by_id != embedding_reviewed:
            raise ValueError(f"embedding reviewed pool drift: {question_id}")

        expected_positive_ids = sorted(
            concept_id
            for concept_id, label in reviewed_by_id.items()
            if label == 1
        )
        if expected_positive_ids != sorted(
            embedding_entry.get("positive_concept_ids") or []
        ):
            raise ValueError(f"embedding positive set drift: {question_id}")

        ranking = list(embedding_entry.get("full_ranked_scores") or [])
        ranked_ids = [str(item.get("concept_id") or "") for item in ranking]
        if (
            len(ranked_ids) != len(concepts)
            or len(set(ranked_ids)) != len(ranked_ids)
            or set(ranked_ids) != concept_ids
        ):
            raise ValueError(f"embedding full ranking drift: {question_id}")
        previous: tuple[float, str] | None = None
        score_rows = []
        for rank, item in enumerate(ranking, start=1):
            concept_id = str(item.get("concept_id") or "")
            score = float(item.get("score"))
            if not math.isfinite(score) or score < -1.0 or score > 1.0:
                raise ValueError(f"embedding score invalid: {question_id}")
            ordering = (-score, concept_id)
            if previous is not None and ordering < previous:
                raise ValueError(f"embedding ranking order drift: {question_id}")
            previous = ordering
            score_rows.append({"concept_id": concept_id, "score": score})
            if concept_id in expected_positive_ids:
                stored_rank = int(
                    embedding_entry.get("positive_ranks", {}).get(concept_id)
                )
                if stored_rank != rank:
                    raise ValueError(f"positive rank drift: {question_id}")
        if canonical_json_sha256(score_rows) != embedding_entry.get(
            "full_ranking_sha256"
        ):
            raise ValueError(f"full ranking hash drift: {question_id}")

    return concepts, questions, labels_by_question, embedding_by_question


def _validate_bindings(bindings: Mapping[str, Any]) -> dict[str, Any]:
    normalized = dict(bindings)
    for field, value in normalized.items():
        if field == "input_file_sha256s":
            if not isinstance(value, Mapping) or not value:
                raise ValueError("input_file_sha256s must be a non-empty mapping")
            for path, digest in value.items():
                _require_sha256(digest, f"input_file_sha256s.{path}")
        else:
            _require_sha256(value, f"bindings.{field}")
    return normalized


def build_hard_negative_vocabulary_outputs(
    vocabulary: Mapping[str, Any],
    generator_spec: Mapping[str, Any],
    label_pack: Mapping[str, Any],
    embedding_artifact: Mapping[str, Any],
    *,
    bindings: Mapping[str, Any],
    created_at: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build a sealed pending-review packet and its read-only audit artifact."""

    concepts, questions, labels_by_question, embedding_by_question = (
        _validate_upstream(
            vocabulary,
            generator_spec,
            label_pack,
            embedding_artifact,
        )
    )
    normalized_bindings = _validate_bindings(bindings)
    created_at = _validate_created_at(created_at)
    concept_by_id = {item["concept_id"]: item for item in concepts}
    profiles, vocabulary_quality = _vocabulary_analysis(concepts)

    packet_questions = []
    audit_question_summaries = []
    selected_unique_ids: set[str] = set()
    selection_reason_counts: Counter[str] = Counter()
    selected_flag_counts: Counter[str] = Counter()

    for question_item in questions:
        question_id = str(question_item["question_id"])
        label_entry = labels_by_question[question_id]
        embedding_entry = embedding_by_question[question_id]
        ranking = list(embedding_entry["full_ranked_scores"])
        rank_by_id = {
            str(item["concept_id"]): rank
            for rank, item in enumerate(ranking, start=1)
        }
        score_by_id = {
            str(item["concept_id"]): float(item["score"]) for item in ranking
        }
        labels = list(label_entry.get("labels") or [])
        reviewed_ids = {str(item["concept_id"]) for item in labels}
        positive_ids = sorted(
            str(item["concept_id"])
            for item in labels
            if int(item["label"]) == 1
        )
        positive_ranks = [rank_by_id[concept_id] for concept_id in positive_ids]
        best_positive_score = max(score_by_id[item] for item in positive_ids)

        reasons_by_id: dict[str, set[str]] = defaultdict(set)
        top_unjudged = [
            str(item["concept_id"])
            for item in ranking
            if str(item["concept_id"]) not in reviewed_ids
        ][:TOP_UNJUDGED_PER_QUESTION]
        for concept_id in top_unjudged:
            reasons_by_id[concept_id].add("top_unjudged")

        for positive_rank in positive_ranks:
            if positive_rank <= EVALUATION_K:
                continue
            start = max(1, positive_rank - POSITIVE_NEIGHBOR_RADIUS)
            end = min(len(ranking), positive_rank + POSITIVE_NEIGHBOR_RADIUS)
            for rank in range(start, end + 1):
                concept_id = str(ranking[rank - 1]["concept_id"])
                if concept_id not in reviewed_ids:
                    reasons_by_id[concept_id].add(
                        "positive_rank_neighbor_for_top8_miss"
                    )

        review_candidates = []
        for concept_id in sorted(reasons_by_id, key=rank_by_id.__getitem__):
            rank = rank_by_id[concept_id]
            profile = profiles[concept_id]
            reasons = sorted(reasons_by_id[concept_id])
            flags = list(profile["machine_surface_flags"])
            selected_unique_ids.add(concept_id)
            selection_reason_counts.update(reasons)
            selected_flag_counts.update(flags)
            review_candidates.append(
                {
                    "candidate_review_id": _review_candidate_id(
                        question_id,
                        concept_id,
                    ),
                    "concept_id": concept_id,
                    "concept_name": concept_by_id[concept_id]["concept_name"],
                    "embedding_rank": rank,
                    "embedding_score": round(score_by_id[concept_id], 12),
                    "score_margin_vs_best_positive": round(
                        score_by_id[concept_id] - best_positive_score,
                        12,
                    ),
                    "rank_gap_to_nearest_positive": min(
                        abs(rank - positive_rank)
                        for positive_rank in positive_ranks
                    ),
                    "selection_reasons": reasons,
                    "machine_surface_flags": flags,
                    "normalized_surface_key": profile[
                        "normalized_surface_key"
                    ],
                    "boundary_punctuation_key": profile[
                        "boundary_punctuation_key"
                    ],
                    "current_label_status": "unjudged",
                    "relevance_review_decision": None,
                    "vocabulary_review_decision": None,
                    "alias_target_concept_id": None,
                    "reviewer_note": None,
                }
            )

        positive_references = [
            {
                "concept_id": concept_id,
                "concept_name": concept_by_id[concept_id]["concept_name"],
                "embedding_rank": rank_by_id[concept_id],
                "embedding_score": round(score_by_id[concept_id], 12),
            }
            for concept_id in positive_ids
        ]
        explicit_negative_references = [
            {
                "concept_id": str(item["concept_id"]),
                "concept_name": concept_by_id[str(item["concept_id"])][
                    "concept_name"
                ],
                "embedding_rank": rank_by_id[str(item["concept_id"])],
                "embedding_score": round(
                    score_by_id[str(item["concept_id"])],
                    12,
                ),
            }
            for item in labels
            if int(item["label"]) == 0
        ]
        context_references = [
            {
                "concept_id": str(item["concept_id"]),
                "concept_name": str(item["concept_name"]),
            }
            for item in label_entry.get("context_concepts_unscored") or []
        ]
        best_positive_rank = min(positive_ranks)
        packet_questions.append(
            {
                "question_id": question_id,
                "order": int(question_item["order"]),
                "question": str(question_item["question"]),
                "question_sha256": str(question_item["question_sha256"]),
                "target_partition": str(
                    embedding_entry.get("target_partition") or ""
                ),
                "retrieval_status": (
                    "positive_in_top_8"
                    if best_positive_rank <= EVALUATION_K
                    else "positive_outside_top_8"
                ),
                "positive_references": positive_references,
                "existing_context_references": context_references,
                "existing_explicit_negative_references": (
                    explicit_negative_references
                ),
                "review_candidates": review_candidates,
            }
        )
        audit_question_summaries.append(
            {
                "question_id": question_id,
                "target_partition": str(
                    embedding_entry.get("target_partition") or ""
                ),
                "best_positive_rank": best_positive_rank,
                "positive_in_top_8": best_positive_rank <= EVALUATION_K,
                "review_candidate_count": len(review_candidates),
                "machine_flagged_review_candidate_count": sum(
                    bool(item["machine_surface_flags"])
                    for item in review_candidates
                ),
            }
        )

    review_row_count = sum(
        len(item["review_candidates"]) for item in packet_questions
    )
    packet = {
        "hard_negative_review_packet_version": REVIEW_PACKET_VERSION,
        "phase": PHASE,
        "status": "pending_user_review_not_training_data",
        "created_at": created_at,
        "bindings": normalized_bindings,
        "selection_contract": {
            "top_unjudged_per_question": TOP_UNJUDGED_PER_QUESTION,
            "positive_neighbor_radius": POSITIVE_NEIGHBOR_RADIUS,
            "positive_neighbor_only_for_positive_outside_top_k": True,
            "top_k": EVALUATION_K,
            "currently_reviewed_concepts_excluded_from_new_candidates": True,
            "unjudged_is_not_negative": True,
        },
        "decision_contract": {
            "relevance_review_decisions": list(
                RELEVANCE_REVIEW_DECISIONS
            ),
            "vocabulary_review_decisions": list(
                VOCABULARY_REVIEW_DECISIONS
            ),
            "relevance_and_vocabulary_are_separate_axes": True,
            "hard_negative_definition": (
                "plausibly relevant confound but not an acceptable answer"
            ),
            "context_definition": (
                "related context that must not be auto-converted to a "
                "binary negative"
            ),
            "machine_surface_flags_are_labels": False,
        },
        "question_count": len(packet_questions),
        "review_row_count": review_row_count,
        "reviewed_row_count": 0,
        "questions": packet_questions,
        "review_complete_gate": False,
        "training_data_materialization_gate": False,
        "database_write_gate": False,
        "learned_head_fit_gate": False,
        "heldout_gate": False,
        "performance_claim_gate": False,
        "production_promotion_gate": False,
        "next_step": "user_reviews_packet_into_separate_decision_artifact",
    }
    packet["hard_negative_review_packet_sha256"] = canonical_json_sha256(
        packet
    )

    audit = {
        "hard_negative_vocabulary_audit_version": AUDIT_ARTIFACT_VERSION,
        "phase": PHASE,
        "status": (
            "development_diagnostic_generated_review_pending_not_training_data"
        ),
        "created_at": created_at,
        "bindings": {
            **normalized_bindings,
            "hard_negative_review_packet_sha256": packet[
                "hard_negative_review_packet_sha256"
            ],
        },
        "selection_summary": {
            "question_count": len(packet_questions),
            "review_row_count": review_row_count,
            "unique_selected_concept_count": len(selected_unique_ids),
            "selection_reason_counts": dict(
                sorted(selection_reason_counts.items())
            ),
            "selected_machine_surface_flag_counts": dict(
                sorted(selected_flag_counts.items())
            ),
            "auto_assigned_positive_count": 0,
            "auto_assigned_context_count": 0,
            "auto_assigned_hard_negative_count": 0,
            "auto_assigned_unrelated_negative_count": 0,
        },
        "question_summaries": audit_question_summaries,
        "vocabulary_quality": vocabulary_quality,
        "review_complete_gate": False,
        "training_data_materialization_gate": False,
        "database_write_gate": False,
        "learning_enabled": False,
        "learned_head_fit_gate": False,
        "lockbox_materialized": False,
        "heldout_gate": False,
        "performance_claim_gate": False,
        "production_promotion_gate": False,
        "next_step": "review_pending_rows_before_any_label_or_training_change",
    }
    audit["hard_negative_vocabulary_audit_sha256"] = canonical_json_sha256(
        audit
    )
    return packet, audit


def validate_hard_negative_review_packet(
    packet: Mapping[str, Any],
    vocabulary: Mapping[str, Any],
    generator_spec: Mapping[str, Any],
    label_pack: Mapping[str, Any],
    embedding_artifact: Mapping[str, Any],
    *,
    expected_bindings: Mapping[str, Any],
) -> dict[str, Any]:
    """Rebuild the packet from sealed inputs and reject any changed row."""

    normalized = dict(packet)
    _validate_self_hash(normalized, "hard_negative_review_packet_sha256")
    expected_packet, _ = build_hard_negative_vocabulary_outputs(
        vocabulary,
        generator_spec,
        label_pack,
        embedding_artifact,
        bindings=expected_bindings,
        created_at=str(normalized.get("created_at") or ""),
    )
    if normalized != expected_packet:
        raise ValueError("hard-negative review packet does not match sealed inputs")
    return normalized


def validate_hard_negative_vocabulary_audit(
    audit: Mapping[str, Any],
    packet: Mapping[str, Any],
    vocabulary: Mapping[str, Any],
    generator_spec: Mapping[str, Any],
    label_pack: Mapping[str, Any],
    embedding_artifact: Mapping[str, Any],
    *,
    expected_bindings: Mapping[str, Any],
) -> dict[str, Any]:
    """Rebuild the audit and verify its packet binding and all summaries."""

    normalized = dict(audit)
    _validate_self_hash(
        normalized,
        "hard_negative_vocabulary_audit_sha256",
    )
    validated_packet = validate_hard_negative_review_packet(
        packet,
        vocabulary,
        generator_spec,
        label_pack,
        embedding_artifact,
        expected_bindings=expected_bindings,
    )
    expected_packet, expected_audit = build_hard_negative_vocabulary_outputs(
        vocabulary,
        generator_spec,
        label_pack,
        embedding_artifact,
        bindings=expected_bindings,
        created_at=str(normalized.get("created_at") or ""),
    )
    if validated_packet != expected_packet:
        raise ValueError("review packet rebuild mismatch")
    if normalized != expected_audit:
        raise ValueError("hard-negative vocabulary audit does not match sealed inputs")
    return normalized
