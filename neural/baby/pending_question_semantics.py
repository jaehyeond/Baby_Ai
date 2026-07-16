"""B5.9 fail-closed contract for reviewed semantic question outcomes.

The B5.7 answers are authoritative user answers, but selecting graph concepts
from those answers is a separate annotation task.  Assistant-generated labels
remain drafts until an explicit user review.  This module is offline-only and
does not import the database or the protected conversation handler.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from typing import Any, Mapping


SEMANTIC_LABEL_PACK_VERSION = 1
SEMANTIC_REVIEW_STATUSES = frozenset({"draft_unreviewed", "user_reviewed"})
SEMANTIC_LABEL_DECISIONS = frozenset({"proposed", "approved", "rejected"})
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def text_sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def canonical_json_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _require_zoned_timestamp(value: Any, field: str) -> str:
    raw = str(value or "").strip()
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} must include a timezone")
    return raw


def _semantic_candidates_by_order(
    b5_8_artifact: Mapping[str, Any],
) -> dict[int, dict[str, str]]:
    candidates: dict[int, dict[str, str]] = {}
    for raw_question in b5_8_artifact.get("questions") or []:
        question = dict(raw_question)
        order = int(question["order"])
        ids = list(question.get("outcome_ids") or [])
        names = list(question.get("outcome_names") or [])
        if len(ids) != len(names):
            raise ValueError(f"B5.8 outcome id/name length mismatch at order {order}")
        candidates[order] = {
            str(concept_id): str(name)
            for concept_id, name in zip(ids, names)
        }
    return candidates


def validate_semantic_label_pack(
    manifest: Mapping[str, Any],
    answers: Mapping[str, Any],
    b5_8_artifact: Mapping[str, Any],
    label_pack: Mapping[str, Any],
    *,
    require_user_review: bool = False,
) -> dict[str, Any]:
    """Validate provenance, exact answer binding, and label decisions."""

    normalized = json.loads(json.dumps(label_pack, ensure_ascii=False))
    if normalized.get("semantic_label_pack_version") != SEMANTIC_LABEL_PACK_VERSION:
        raise ValueError("unsupported semantic_label_pack_version")

    contract_sha256 = str(manifest.get("contract_sha256") or "")
    if not _SHA256_PATTERN.fullmatch(contract_sha256):
        raise ValueError("manifest contract_sha256 is invalid")
    for name, source in (
        ("answers", answers),
        ("B5.8 artifact", b5_8_artifact),
        ("semantic label pack", normalized),
    ):
        if source.get("contract_sha256") != contract_sha256:
            raise ValueError(f"{name} contract_sha256 mismatch")

    status = str(normalized.get("review_status") or "")
    if status not in SEMANTIC_REVIEW_STATUSES:
        raise ValueError("invalid review_status")
    reviewer_role = str(normalized.get("reviewer_role") or "")
    reviewed_at = normalized.get("reviewed_at")
    if status == "draft_unreviewed":
        if reviewer_role != "assistant_draft" or reviewed_at is not None:
            raise ValueError("draft labels must remain assistant_draft and unreviewed")
    else:
        if reviewer_role != "user":
            raise ValueError("user_reviewed labels require reviewer_role=user")
        _require_zoned_timestamp(reviewed_at, "reviewed_at")
    if require_user_review and status != "user_reviewed":
        raise ValueError("semantic labels require explicit user review")

    manifest_by_order = {
        int(item["order"]): dict(item) for item in manifest.get("questions") or []
    }
    answers_by_order = {
        int(item["order"]): dict(item) for item in answers.get("answers") or []
    }
    candidates_by_order = _semantic_candidates_by_order(b5_8_artifact)
    entries = list(normalized.get("entries") or [])
    expected_orders = set(manifest_by_order)
    actual_orders = {int(item.get("order", -1)) for item in entries}
    if actual_orders != expected_orders or len(entries) != len(expected_orders):
        raise ValueError("semantic entries must match every manifest order exactly once")

    for entry in entries:
        order = int(entry["order"])
        manifest_question = manifest_by_order[order]
        answer = answers_by_order.get(order)
        if answer is None:
            raise ValueError(f"missing answer at order {order}")
        for field in ("curiosity_log_id", "question_id"):
            expected = answer.get(field)
            if entry.get(field) != expected:
                raise ValueError(f"{field} mismatch at order {order}")
        if entry.get("curiosity_log_id") != manifest_question.get("curiosity_log_id"):
            raise ValueError(f"manifest action mismatch at order {order}")
        if entry.get("answer_sha256") != text_sha256(str(answer.get("answer") or "")):
            raise ValueError(f"answer_sha256 mismatch at order {order}")

        candidates = candidates_by_order.get(order, {})
        labels = list(entry.get("labels") or [])
        if not labels:
            raise ValueError(f"at least one semantic label is required at order {order}")
        seen_ids: set[str] = set()
        approved_count = 0
        for label in labels:
            concept_id = str(label.get("concept_id") or "").strip()
            name = str(label.get("name") or "").strip()
            decision = str(label.get("decision") or "")
            if not concept_id or concept_id in seen_ids:
                raise ValueError(f"duplicate or empty concept_id at order {order}")
            seen_ids.add(concept_id)
            if candidates.get(concept_id) != name:
                raise ValueError(f"label is not a B5.8 time-valid outcome at order {order}")
            if decision not in SEMANTIC_LABEL_DECISIONS:
                raise ValueError(f"invalid label decision at order {order}")
            if status == "draft_unreviewed" and decision != "proposed":
                raise ValueError("assistant draft cannot approve or reject labels")
            if status == "user_reviewed" and decision == "proposed":
                raise ValueError("user review must decide every proposed label")
            approved_count += int(decision == "approved")
        if status == "user_reviewed" and approved_count == 0:
            raise ValueError(f"user review requires an approved label at order {order}")

    return normalized


def build_action_answer_relation_proposals(
    manifest: Mapping[str, Any],
    answers: Mapping[str, Any],
    b5_8_artifact: Mapping[str, Any],
    label_pack: Mapping[str, Any],
) -> dict[str, Any]:
    """Build name/ID-bound proposals without issuing a database write."""

    pack = validate_semantic_label_pack(
        manifest,
        answers,
        b5_8_artifact,
        label_pack,
    )
    reviewed = pack["review_status"] == "user_reviewed"
    proposals: list[dict[str, Any]] = []
    evaluation_targets: dict[str, list[str]] = {}
    for entry in sorted(pack["entries"], key=lambda item: int(item["order"])):
        order = int(entry["order"])
        approved_ids: list[str] = []
        for label in entry["labels"]:
            decision = label["decision"]
            write_eligible = reviewed and decision == "approved"
            if write_eligible:
                approved_ids.append(label["concept_id"])
            proposals.append({
                "proposal_id": text_sha256(
                    f"{entry['question_id']}|ANSWER_EVIDENCES_CONCEPT|{label['concept_id']}"
                ),
                "source_label": "PendingQuestion",
                "source_id": entry["question_id"],
                "relationship_type": "ANSWER_EVIDENCES_CONCEPT",
                "target_label": "Concept",
                "target_id": label["concept_id"],
                "target_name": label["name"],
                "semantic_decision": decision,
                "review_status": pack["review_status"],
                "write_eligible_after_schema_review": write_eligible,
            })
        evaluation_targets[str(order)] = approved_ids

    return {
        "review_status": pack["review_status"],
        "semantic_target_validity_gate": reviewed,
        "relation_proposal_count": len(proposals),
        "relation_proposals": proposals,
        "evaluation_target_ids_by_order": evaluation_targets,
        "database_writes": False,
        "database_write_gate": False,
        "database_block_reason": (
            "semantic_labels_not_user_reviewed"
            if not reviewed
            else "offline_relation_schema_not_integrated"
        ),
    }
