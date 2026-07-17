"""Pure J1.1A contracts for answer routing and reviewed calibration labels.

The sealed J1.1 manifest and raw-score pack remain immutable.  This module
records which source is allowed to answer a question, binds external-teacher
reference answers to the sealed questions, and keeps assistant-proposed labels
unfit for calibration until explicit user review.  It imports neither Neo4j,
torch, the API server, nor the protected conversation handler.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any, Mapping

from neural.baby.pending_question_semantics import (
    canonical_json_sha256,
    text_sha256,
)


ANSWER_SOURCE_AMENDMENT_VERSION = 1
REFERENCE_ANSWER_PACK_VERSION = 1
CANDIDATE_LABEL_PACK_VERSION = 1
PHASE = "J1.1A"
QUESTION_SOURCE_ROUTES = {
    "public_knowledge": "external_teacher",
    "current_fact": "authoritative_retrieval",
    "personal_context": "user",
    "sensor_observation": "sensor",
    "tool_outcome": "tool",
    "safety_permission": "user",
    "unresolved": "abstain",
}
DRAFT_DECISIONS = frozenset({
    "proposed_approved",
    "proposed_rejected",
    "proposed_uncertain",
})
REVIEWED_DECISIONS = frozenset({"approved", "rejected", "uncertain"})
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def _clone(value: Mapping[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(value, ensure_ascii=False))


def _zoned_datetime(value: Any, field: str) -> datetime:
    raw = str(value or "").strip()
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} must include a timezone")
    return parsed.astimezone(timezone.utc)


def _require_sha256(value: Any, field: str) -> str:
    raw = str(value or "").strip().lower()
    if not _SHA256_PATTERN.fullmatch(raw):
        raise ValueError(f"{field} must be a lowercase SHA-256")
    return raw


def _without_key(payload: Mapping[str, Any], key: str) -> dict[str, Any]:
    normalized = _clone(payload)
    normalized.pop(key, None)
    return normalized


def route_answer_source(question_type: str) -> str:
    """Return the deterministic source route for a preregistered question type."""

    normalized = str(question_type or "").strip()
    if normalized not in QUESTION_SOURCE_ROUTES:
        raise ValueError("unsupported question_type")
    return QUESTION_SOURCE_ROUTES[normalized]


def seal_answer_source_amendment(payload: Mapping[str, Any]) -> dict[str, Any]:
    normalized = _clone(payload)
    normalized.pop("amendment_sha256", None)
    normalized["amendment_sha256"] = canonical_json_sha256(normalized)
    return normalized


def validate_answer_source_amendment(
    manifest: Mapping[str, Any],
    raw_pack: Mapping[str, Any],
    amendment: Mapping[str, Any],
) -> dict[str, Any]:
    normalized = _clone(amendment)
    if normalized.get("answer_source_amendment_version") != ANSWER_SOURCE_AMENDMENT_VERSION:
        raise ValueError("unsupported answer_source_amendment_version")
    if normalized.get("phase") != PHASE or normalized.get("status") != "active":
        raise ValueError("answer-source amendment must be active J1.1A")
    if normalized.get("manifest_id") != manifest.get("manifest_id"):
        raise ValueError("amendment manifest_id mismatch")
    if normalized.get("contract_sha256") != manifest.get("contract_sha256"):
        raise ValueError("amendment contract_sha256 mismatch")
    if normalized.get("raw_score_pack_sha256") != raw_pack.get("raw_score_pack_sha256"):
        raise ValueError("amendment raw_score_pack_sha256 mismatch")
    _require_sha256(normalized.get("contract_sha256"), "contract_sha256")
    _require_sha256(normalized.get("raw_score_pack_sha256"), "raw_score_pack_sha256")
    created_at = _zoned_datetime(normalized.get("created_at"), "created_at")
    raw_sealed_at = _zoned_datetime(raw_pack.get("sealed_at"), "raw_pack.sealed_at")
    if created_at < raw_sealed_at:
        raise ValueError("answer-source amendment must follow raw-score sealing")

    required_values = {
        "original_artifacts_mutated": False,
        "user_direct_answers_required": False,
        "batch_user_review_required": True,
        "calibrator_fit_allowed": False,
        "database_writes": False,
        "learning_enabled": False,
        "heldout_gate": False,
        "performance_claim_gate": False,
        "production_promotion_gate": False,
        "replacement_data_role": "teacher_labeled_calibration_bootstrap",
    }
    for field, expected in required_values.items():
        if normalized.get(field) != expected:
            raise ValueError(f"amendment field {field} must be {expected!r}")
    if normalized.get("superseded_next_step") != (
        "collect_new_user_answers_then_review_candidate_labels_and_fit_train_only_calibrators"
    ):
        raise ValueError("amendment must name the superseded next step exactly")
    if normalized.get("replacement_next_step") != (
        "draft_external_teacher_answers_and_candidate_labels_then_stop_for_batch_user_review"
    ):
        raise ValueError("amendment replacement_next_step mismatch")

    actual_hash = _require_sha256(normalized.get("amendment_sha256"), "amendment_sha256")
    expected_hash = canonical_json_sha256(_without_key(normalized, "amendment_sha256"))
    if actual_hash != expected_hash:
        raise ValueError("amendment_sha256 mismatch")
    return normalized


def seal_reference_answer_pack(payload: Mapping[str, Any]) -> dict[str, Any]:
    normalized = _clone(payload)
    normalized.pop("reference_answer_pack_sha256", None)
    for entry in normalized.get("answers") or []:
        entry["answer_sha256"] = text_sha256(str(entry.get("answer") or ""))
    normalized["reference_answer_pack_sha256"] = canonical_json_sha256(normalized)
    return normalized


def validate_reference_answer_pack(
    manifest: Mapping[str, Any],
    raw_pack: Mapping[str, Any],
    amendment: Mapping[str, Any],
    answer_pack: Mapping[str, Any],
) -> dict[str, Any]:
    validate_answer_source_amendment(manifest, raw_pack, amendment)
    normalized = _clone(answer_pack)
    if normalized.get("reference_answer_pack_version") != REFERENCE_ANSWER_PACK_VERSION:
        raise ValueError("unsupported reference_answer_pack_version")
    if normalized.get("phase") != PHASE:
        raise ValueError("reference answers must be J1.1A")
    for field, expected in (
        ("manifest_id", manifest.get("manifest_id")),
        ("contract_sha256", manifest.get("contract_sha256")),
        ("raw_score_pack_sha256", raw_pack.get("raw_score_pack_sha256")),
        ("answer_source_amendment_sha256", amendment.get("amendment_sha256")),
    ):
        if normalized.get(field) != expected:
            raise ValueError(f"reference answer {field} mismatch")
    if normalized.get("teacher_identity") != "codex_assistant":
        raise ValueError("reference answer teacher_identity mismatch")
    if normalized.get("teacher_identity_scope") != "conversation_assistant_not_model_snapshot":
        raise ValueError("reference answers must not claim an unavailable teacher model snapshot")
    review_status = normalized.get("review_status")
    if review_status == "awaiting_batch_user_review":
        if normalized.get("answer_provenance") != "external_teacher_drafted":
            raise ValueError("draft reference answer provenance mismatch")
        if normalized.get("reviewed_at") is not None:
            raise ValueError("draft reference answers cannot have reviewed_at")
    elif review_status == "user_reviewed":
        if normalized.get("answer_provenance") != (
            "external_teacher_drafted_user_reviewed"
        ):
            raise ValueError("reviewed reference answer provenance mismatch")
        if normalized.get("reviewer_role") != "user":
            raise ValueError("reviewed reference answers require reviewer_role=user")
        _zoned_datetime(normalized.get("reviewed_at"), "answer_pack.reviewed_at")
    else:
        raise ValueError("invalid reference answer review_status")
    if normalized.get("user_direct_answers") is not False:
        raise ValueError("reference pack must not claim direct user answers")
    if normalized.get("calibrator_fit_allowed") is not False:
        raise ValueError("reference answers cannot enable calibrator fitting")
    created_at = _zoned_datetime(normalized.get("created_at"), "answer_pack.created_at")
    if created_at < _zoned_datetime(raw_pack.get("sealed_at"), "raw_pack.sealed_at"):
        raise ValueError("reference answers must follow raw-score capture")

    manifest_by_order = {
        int(item["order"]): dict(item)
        for item in manifest.get("questions") or []
    }
    answers = list(normalized.get("answers") or [])
    if normalized.get("answer_count") != len(answers):
        raise ValueError("answer_count mismatch")
    if {int(item.get("order", -1)) for item in answers} != set(manifest_by_order):
        raise ValueError("reference answers must cover every manifest question")
    if len(answers) != len(manifest_by_order):
        raise ValueError("reference answers must contain every order exactly once")
    for entry in answers:
        order = int(entry["order"])
        expected = manifest_by_order[order]
        for field in ("question_id", "question", "question_sha256"):
            if entry.get(field) != expected.get(field):
                raise ValueError(f"reference answer {field} mismatch at order {order}")
        if entry.get("question_type") != "public_knowledge":
            raise ValueError("current J1.1A questions must be public_knowledge")
        if entry.get("answer_source") != route_answer_source(entry["question_type"]):
            raise ValueError("reference answer source route mismatch")
        answer = str(entry.get("answer") or "").strip()
        if not answer:
            raise ValueError("reference answer text is required")
        if entry.get("answer_sha256") != text_sha256(answer):
            raise ValueError("reference answer_sha256 mismatch")

    actual_hash = _require_sha256(
        normalized.get("reference_answer_pack_sha256"),
        "reference_answer_pack_sha256",
    )
    expected_hash = canonical_json_sha256(
        _without_key(normalized, "reference_answer_pack_sha256")
    )
    if actual_hash != expected_hash:
        raise ValueError("reference_answer_pack_sha256 mismatch")
    return normalized


def seal_candidate_label_pack(payload: Mapping[str, Any]) -> dict[str, Any]:
    normalized = _clone(payload)
    normalized.pop("candidate_label_pack_sha256", None)
    normalized["candidate_label_pack_sha256"] = canonical_json_sha256(normalized)
    return normalized


def build_user_reviewed_packs(
    answer_pack: Mapping[str, Any],
    label_pack: Mapping[str, Any],
    *,
    reviewed_at: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Create immutable user-reviewed successors without mutating draft packs."""

    _zoned_datetime(reviewed_at, "reviewed_at")
    reviewed_answers = _clone(answer_pack)
    if reviewed_answers.get("review_status") != "awaiting_batch_user_review":
        raise ValueError("reference answer pack is not awaiting user review")
    if reviewed_answers.get("answer_provenance") != "external_teacher_drafted":
        raise ValueError("only an external-teacher draft can become user reviewed")

    reviewed_labels = _clone(label_pack)
    if reviewed_labels.get("review_status") != "awaiting_user_review":
        raise ValueError("candidate label pack is not awaiting user review")
    if reviewed_labels.get("reviewer_role") != "assistant_draft":
        raise ValueError("only an assistant label draft can become user reviewed")
    if reviewed_labels.get("reference_answer_pack_sha256") != answer_pack.get(
        "reference_answer_pack_sha256"
    ):
        raise ValueError("draft candidate labels are not bound to the draft answers")

    reviewed_answers.update({
        "answer_provenance": "external_teacher_drafted_user_reviewed",
        "review_status": "user_reviewed",
        "reviewer_role": "user",
        "reviewed_at": reviewed_at,
        "calibrator_fit_allowed": False,
    })
    reviewed_answers = seal_reference_answer_pack(reviewed_answers)

    for entry in reviewed_labels.get("entries") or []:
        for label in entry.get("labels") or []:
            decision = str(label.get("decision") or "")
            if decision not in DRAFT_DECISIONS:
                raise ValueError("draft candidate label has a non-draft decision")
            label["decision"] = decision.removeprefix("proposed_")
    reviewed_labels.update({
        "reference_answer_pack_sha256": reviewed_answers[
            "reference_answer_pack_sha256"
        ],
        "review_status": "user_reviewed",
        "reviewer_role": "user",
        "reviewed_at": reviewed_at,
        "calibrator_fit_allowed": False,
        "database_writes": False,
        "learning_enabled": False,
    })
    reviewed_labels = seal_candidate_label_pack(reviewed_labels)
    return reviewed_answers, reviewed_labels


def validate_candidate_label_pack(
    manifest: Mapping[str, Any],
    raw_pack: Mapping[str, Any],
    answer_pack: Mapping[str, Any],
    label_pack: Mapping[str, Any],
    *,
    require_user_review: bool = False,
) -> dict[str, Any]:
    normalized = _clone(label_pack)
    if normalized.get("candidate_label_pack_version") != CANDIDATE_LABEL_PACK_VERSION:
        raise ValueError("unsupported candidate_label_pack_version")
    if normalized.get("phase") != PHASE:
        raise ValueError("candidate labels must be J1.1A")
    for field, expected in (
        ("manifest_id", manifest.get("manifest_id")),
        ("contract_sha256", manifest.get("contract_sha256")),
        ("raw_score_pack_sha256", raw_pack.get("raw_score_pack_sha256")),
        ("reference_answer_pack_sha256", answer_pack.get("reference_answer_pack_sha256")),
    ):
        if normalized.get(field) != expected:
            raise ValueError(f"candidate label {field} mismatch")

    status = normalized.get("review_status")
    if status == "awaiting_user_review":
        if normalized.get("reviewer_role") != "assistant_draft" or normalized.get("reviewed_at") is not None:
            raise ValueError("draft candidate labels must remain assistant_draft and unreviewed")
        allowed_decisions = DRAFT_DECISIONS
    elif status == "user_reviewed":
        if answer_pack.get("review_status") != "user_reviewed":
            raise ValueError("user-reviewed labels require user-reviewed reference answers")
        if normalized.get("reviewer_role") != "user":
            raise ValueError("user-reviewed candidate labels require reviewer_role=user")
        _zoned_datetime(normalized.get("reviewed_at"), "candidate_labels.reviewed_at")
        allowed_decisions = REVIEWED_DECISIONS
    else:
        raise ValueError("invalid candidate label review_status")
    if require_user_review and status != "user_reviewed":
        raise ValueError("candidate labels require explicit user review")
    if normalized.get("calibrator_fit_allowed") is not False:
        raise ValueError("J1.1A candidate labels cannot enable calibrator fitting")
    if normalized.get("database_writes") is not False or normalized.get("learning_enabled") is not False:
        raise ValueError("candidate label pack must remain offline and no-learning")

    answers_by_order = {
        int(item["order"]): dict(item)
        for item in answer_pack.get("answers") or []
    }
    raw_by_order = {
        int(item["order"]): dict(item)
        for item in raw_pack.get("questions") or []
    }
    entries = list(normalized.get("entries") or [])
    expected_orders = set(raw_by_order)
    if len(entries) != len(expected_orders) or {
        int(item.get("order", -1)) for item in entries
    } != expected_orders:
        raise ValueError("candidate label entries must match every raw question exactly once")

    for entry in entries:
        order = int(entry["order"])
        raw_question = raw_by_order[order]
        answer = answers_by_order[order]
        if entry.get("question_id") != raw_question.get("question_id"):
            raise ValueError("candidate label question_id mismatch")
        if entry.get("question_sha256") != raw_question.get("question_sha256"):
            raise ValueError("candidate label question_sha256 mismatch")
        if entry.get("answer_sha256") != answer.get("answer_sha256"):
            raise ValueError("candidate label answer_sha256 mismatch")
        universe = {
            str(item.get("concept_id") or ""): str(item.get("concept_name") or "")
            for item in raw_question.get("concept_universe") or []
        }
        labels = list(entry.get("labels") or [])
        if len(labels) != len(universe):
            raise ValueError("candidate labels must decide the full concept universe")
        seen: set[str] = set()
        for label in labels:
            concept_id = str(label.get("concept_id") or "")
            concept_name = str(label.get("concept_name") or "")
            decision = str(label.get("decision") or "")
            if not concept_id or concept_id in seen or universe.get(concept_id) != concept_name:
                raise ValueError("candidate label is duplicate or outside the sealed universe")
            if decision not in allowed_decisions:
                raise ValueError("candidate label decision is invalid for its review status")
            if not str(label.get("rationale") or "").strip():
                raise ValueError("candidate label rationale is required")
            seen.add(concept_id)
        if seen != set(universe):
            raise ValueError("candidate labels do not cover the exact sealed universe")

    actual_hash = _require_sha256(
        normalized.get("candidate_label_pack_sha256"),
        "candidate_label_pack_sha256",
    )
    expected_hash = canonical_json_sha256(
        _without_key(normalized, "candidate_label_pack_sha256")
    )
    if actual_hash != expected_hash:
        raise ValueError("candidate_label_pack_sha256 mismatch")
    return normalized


def build_answer_source_readiness_report(
    manifest: Mapping[str, Any],
    raw_pack: Mapping[str, Any],
    amendment: Mapping[str, Any],
    answer_pack: Mapping[str, Any],
    label_pack: Mapping[str, Any],
) -> dict[str, Any]:
    amendment_valid = validate_answer_source_amendment(manifest, raw_pack, amendment)
    answers_valid = validate_reference_answer_pack(
        manifest,
        raw_pack,
        amendment_valid,
        answer_pack,
    )
    labels_valid = validate_candidate_label_pack(
        manifest,
        raw_pack,
        answers_valid,
        label_pack,
    )

    counts = {"approved": 0, "rejected": 0, "uncertain": 0}
    coverage_orders: list[int] = []
    per_question: list[dict[str, Any]] = []
    draft = labels_valid["review_status"] != "user_reviewed"
    for entry in sorted(labels_valid["entries"], key=lambda item: int(item["order"])):
        local_counts = {"approved": 0, "rejected": 0, "uncertain": 0}
        names = {"approved": [], "uncertain": []}
        for label in entry["labels"]:
            decision = str(label["decision"])
            if draft:
                decision = decision.removeprefix("proposed_")
            local_counts[decision] += 1
            counts[decision] += 1
            if decision in names:
                names[decision].append(label["concept_name"])
        if local_counts["approved"] > 0:
            coverage_orders.append(int(entry["order"]))
        per_question.append({
            "order": int(entry["order"]),
            "question_id": entry["question_id"],
            "proposed_approved_names": names["approved"],
            "proposed_uncertain_names": names["uncertain"],
            "proposed_rejected_count": local_counts["rejected"],
            "candidate_coverage": local_counts["approved"] > 0,
        })

    question_count = len(per_question)
    review_gate = labels_valid["review_status"] == "user_reviewed"
    coverage_gate = len(coverage_orders) == question_count
    fair_universe_gate = False
    provisional_calibrator_fit_gate = review_gate and coverage_gate
    question_selection_calibrator_gate = provisional_calibrator_fit_gate and fair_universe_gate
    block_reasons: list[str] = []
    if not review_gate:
        block_reasons.append("explicit_user_batch_review_missing")
    if not coverage_gate:
        block_reasons.append(
            f"candidate_positive_coverage_{len(coverage_orders)}_of_{question_count}"
        )
    if not fair_universe_gate:
        block_reasons.append("candidate_universe_is_graph_selected_only")
    return {
        "status": (
            "blocked_pending_candidate_universe_v2"
            if review_gate else "awaiting_user_review_and_candidate_universe_v2"
        ),
        "phase": PHASE,
        "answer_source_contract_gate": True,
        "reference_answer_contract_gate": True,
        "label_proposal_contract_gate": True,
        "review_status": labels_valid["review_status"],
        "question_count": question_count,
        "candidate_label_count": sum(counts.values()),
        "proposed_decision_counts": counts,
        "candidate_positive_coverage_count": len(coverage_orders),
        "candidate_positive_coverage_gate": coverage_gate,
        "fair_candidate_universe_gate": fair_universe_gate,
        "provisional_calibrator_fit_gate": provisional_calibrator_fit_gate,
        "question_selection_calibrator_gate": question_selection_calibrator_gate,
        "per_question_review": per_question,
        "block_reasons": block_reasons,
        "database_writes": False,
        "learning_enabled": False,
        "heldout_gate": False,
        "performance_claim_gate": False,
        "production_promotion_gate": False,
        "next_step": (
            "build_independent_union_candidate_universe_v2_before_any_calibrator_fit"
            if review_gate else
            "user_batch_review_reference_answers_and_label_draft_then_build_"
            "independent_union_candidate_universe_v2_before_any_calibrator_fit"
        ),
    }
