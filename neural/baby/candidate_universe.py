"""Pure contracts for an independently selected J1.1B candidate universe.

Validity filtering happens before either predictor is scored.  Graph and local
core must then score the same eligible vocabulary, select top-k independently,
and expose their union with both raw scores.  This module never converts scores
to probabilities and has no database, model, or conversation-handler imports.
"""

from __future__ import annotations

import json
import re
import unicodedata
from collections import Counter
from datetime import datetime
from typing import Any, Iterable, Mapping

from neural.baby.live_curiosity import filter_curiosity_cue_terms
from neural.baby.pending_question_semantics import canonical_json_sha256
from neural.baby.question_calibration import rank_raw_scores


CANDIDATE_VOCABULARY_VERSION = 2
INDEPENDENT_SCORE_CAPTURE_VERSION = 1
UNION_LABEL_PACK_VERSION = 1
PHASE = "J1.1B"
DEFAULT_TOP_K = 8
_CODE_IDENTIFIER_RE = re.compile(r"^[a-z][a-z0-9]*_[a-z0-9_]+$", re.IGNORECASE)
_CONTROL_CHARACTER_RE = re.compile(r"[\x00-\x1f\x7f]")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_CUE_SURFACE_SUFFIXES = (
    "에서", "에게", "한테", "처럼", "까지", "부터", "조차", "마저", "으로",
    "이나", "라도", "라면", "보다", "밖에", "은", "는", "이", "가", "을",
    "를", "의", "와", "과", "에", "만", "도", "로", "라", "요",
)
_AUDITED_INVALID_SURFACES = frozenset({
    "search_dictionary",
    "궁금해",
    "말해줘",
    "알려주세요",
    "설명해줘",
    "제가",
    "형은",
    "형의",
})
_DRAFT_LABEL_DECISIONS = frozenset({
    "proposed_approved",
    "proposed_rejected",
    "proposed_uncertain",
})
_REVIEWED_LABEL_DECISIONS = frozenset({"approved", "rejected", "uncertain"})


def normalize_candidate_name(value: Any) -> str:
    """Return a stable name used only for validity and duplicate checks."""

    normalized = unicodedata.normalize("NFKC", str(value or "")).casefold().strip()
    return " ".join(normalized.split())


def classify_candidate_vocabulary(
    concepts: Iterable[Mapping[str, Any]],
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Split a predictor-neutral concept snapshot into eligible and rejected rows."""

    source = [dict(item) for item in concepts]
    id_counts = Counter(str(item.get("id") or "").strip() for item in source)
    name_counts = Counter(normalize_candidate_name(item.get("name")) for item in source)
    eligible: list[dict[str, str]] = []
    rejected: list[dict[str, str]] = []
    for item in source:
        concept_id = str(item.get("id") or "").strip()
        concept_name = str(item.get("name") or "").strip()
        normalized_name = normalize_candidate_name(concept_name)
        reason = ""
        if not concept_id:
            reason = "missing_concept_id"
        elif not normalized_name:
            reason = "missing_concept_name"
        elif id_counts[concept_id] != 1:
            reason = "duplicate_concept_id"
        elif name_counts[normalized_name] != 1:
            reason = "duplicate_normalized_name"
        elif len(normalized_name) > 64:
            reason = "name_too_long"
        elif _CONTROL_CHARACTER_RE.search(concept_name):
            reason = "control_character"
        elif normalized_name in _AUDITED_INVALID_SURFACES:
            reason = "audited_invalid_surface"
        elif not filter_curiosity_cue_terms([normalized_name]):
            reason = "generic_speech_act"
        elif _CODE_IDENTIFIER_RE.fullmatch(normalized_name):
            reason = "code_identifier"

        if reason:
            rejected.append({
                "concept_id": concept_id,
                "concept_name": concept_name,
                "reason": reason,
            })
        else:
            eligible.append({
                "concept_id": concept_id,
                "concept_name": concept_name,
            })
    eligible.sort(key=lambda item: item["concept_id"])
    rejected.sort(key=lambda item: (item["reason"], item["concept_id"], item["concept_name"]))
    return eligible, rejected


def exclude_question_cue_surfaces(
    concepts: Iterable[Mapping[str, Any]],
    cue_terms: Iterable[str],
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Remove exact cues and narrow surface variants before predictor scoring."""

    normalized_cues = {
        normalize_candidate_name(term)
        for term in cue_terms
        if normalize_candidate_name(term)
    }
    eligible: list[dict[str, str]] = []
    excluded: list[dict[str, str]] = []
    for raw in concepts:
        concept = {
            "concept_id": str(raw.get("concept_id") or "").strip(),
            "concept_name": str(raw.get("concept_name") or "").strip(),
        }
        name = normalize_candidate_name(concept["concept_name"])
        reason = ""
        if name in normalized_cues:
            reason = "exact_question_cue"
        else:
            for cue in normalized_cues:
                if len(cue) >= 2 and any(
                    name == f"{cue}{suffix}" for suffix in _CUE_SURFACE_SUFFIXES
                ):
                    reason = "question_cue_surface_variant"
                    break
        if reason:
            excluded.append({**concept, "reason": reason})
        else:
            eligible.append(concept)
    return eligible, excluded


def build_independent_union(
    eligible_concepts: Iterable[Mapping[str, Any]],
    graph_scores: Iterable[Mapping[str, Any]],
    local_core_scores: Iterable[Mapping[str, Any]],
    *,
    top_k: int = DEFAULT_TOP_K,
) -> dict[str, Any]:
    """Build Graph top-k union Local-Core top-k from the same complete vocabulary."""

    if top_k < 1:
        raise ValueError("top_k must be positive")
    concepts = [
        {
            "concept_id": str(item.get("concept_id") or "").strip(),
            "concept_name": str(item.get("concept_name") or "").strip(),
        }
        for item in eligible_concepts
    ]
    expected = {item["concept_id"]: item["concept_name"] for item in concepts}
    if len(expected) != len(concepts) or not expected:
        raise ValueError("eligible concepts require unique, non-empty IDs")

    graph_ranked = rank_raw_scores(graph_scores)
    local_ranked = rank_raw_scores(local_core_scores)
    for predictor, ranked in (("graph", graph_ranked), ("local_core", local_ranked)):
        actual = {item["concept_id"]: item["concept_name"] for item in ranked}
        if actual != expected:
            raise ValueError(
                f"{predictor} must score the exact complete eligible vocabulary"
            )

    graph_by_id = {item["concept_id"]: item for item in graph_ranked}
    local_by_id = {item["concept_id"]: item for item in local_ranked}
    graph_top = graph_ranked[:top_k]
    local_top = local_ranked[:top_k]
    union_ids = list(dict.fromkeys(
        [item["concept_id"] for item in graph_top]
        + [item["concept_id"] for item in local_top]
    ))
    union = [{
        "concept_id": concept_id,
        "concept_name": expected[concept_id],
        "graph_raw_score": graph_by_id[concept_id]["raw_score"],
        "graph_rank": graph_by_id[concept_id]["rank"],
        "local_core_raw_score": local_by_id[concept_id]["raw_score"],
        "local_core_rank": local_by_id[concept_id]["rank"],
    } for concept_id in union_ids]
    return {
        "eligible_concept_count": len(expected),
        "top_k": top_k,
        "selection_rule": "graph_top_k_union_local_core_top_k",
        "graph_top_k_ids": [item["concept_id"] for item in graph_top],
        "local_core_top_k_ids": [item["concept_id"] for item in local_top],
        "union_count": len(union),
        "union": union,
        "probabilities_computed": False,
        "calibrator_fit_allowed": False,
    }


def seal_candidate_vocabulary(payload: Mapping[str, Any]) -> dict[str, Any]:
    normalized = json.loads(json.dumps(payload, ensure_ascii=False))
    normalized.pop("candidate_vocabulary_sha256", None)
    normalized["candidate_vocabulary_sha256"] = canonical_json_sha256(normalized)
    return normalized


def validate_candidate_vocabulary(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a sealed, read-only preflight vocabulary snapshot."""

    normalized = json.loads(json.dumps(payload, ensure_ascii=False))
    if normalized.get("candidate_vocabulary_version") != CANDIDATE_VOCABULARY_VERSION:
        raise ValueError("unsupported candidate_vocabulary_version")
    if normalized.get("phase") != PHASE or normalized.get("status") != "preflight_only":
        raise ValueError("candidate vocabulary must be J1.1B preflight_only")
    try:
        created_at = datetime.fromisoformat(
            str(normalized.get("created_at") or "").replace("Z", "+00:00")
        )
    except ValueError as exc:
        raise ValueError("created_at must be an ISO timestamp") from exc
    if created_at.tzinfo is None or created_at.utcoffset() is None:
        raise ValueError("created_at must include a timezone")
    for field in (
        "manifest_contract_sha256",
        "reviewed_reference_answer_pack_sha256",
        "reviewed_candidate_label_pack_sha256",
        "graph_snapshot_sha256",
    ):
        if not _SHA256_RE.fullmatch(str(normalized.get(field) or "")):
            raise ValueError(f"{field} must be a lowercase SHA-256")

    contract = dict(normalized.get("selection_contract") or {})
    required_contract = {
        "source_vocabulary": "neo4j_full_concept_snapshot",
        "validity_filter_precedes_predictor_scoring": True,
        "semantic_labels_used_for_filtering": False,
        "graph_scores_required_for_full_question_vocabulary": True,
        "local_core_scores_required_for_full_question_vocabulary": True,
        "top_k": DEFAULT_TOP_K,
        "union_rule": "graph_top_k_union_local_core_top_k",
        "both_predictors_rescore_union": True,
    }
    for field, expected in required_contract.items():
        if contract.get(field) != expected:
            raise ValueError(f"selection_contract.{field} must be {expected!r}")

    eligible = list(normalized.get("eligible_concepts") or [])
    rejected = list(normalized.get("rejected_concepts") or [])
    if normalized.get("eligible_concept_count") != len(eligible):
        raise ValueError("eligible_concept_count mismatch")
    if normalized.get("rejected_concept_count") != len(rejected):
        raise ValueError("rejected_concept_count mismatch")
    if normalized.get("source_concept_count") != len(eligible) + len(rejected):
        raise ValueError("source_concept_count mismatch")
    ids = [str(item.get("concept_id") or "") for item in eligible]
    if not ids or len(ids) != len(set(ids)) or any(not item for item in ids):
        raise ValueError("eligible concepts require unique non-empty IDs")
    if any(not str(item.get("concept_name") or "").strip() for item in eligible):
        raise ValueError("eligible concepts require names")
    expected_rejections = dict(Counter(
        str(item.get("reason") or "") for item in rejected
    ))
    if normalized.get("rejection_counts") != expected_rejections:
        raise ValueError("rejection_counts mismatch")

    scopes = list(normalized.get("question_scopes") or [])
    if not scopes:
        raise ValueError("question scopes are required")
    if any(int(item.get("eligible_concept_count", 0)) < DEFAULT_TOP_K for item in scopes):
        raise ValueError("each question scope requires at least top_k eligible concepts")
    for field in (
        "database_writes",
        "learning_enabled",
        "gpu_inference_executed",
        "probabilities_computed",
        "calibrator_fit_allowed",
        "heldout_gate",
        "performance_claim_gate",
        "production_promotion_gate",
    ):
        if normalized.get(field) is not False:
            raise ValueError(f"{field} must remain false at preflight")

    supplied_hash = str(normalized.get("candidate_vocabulary_sha256") or "")
    if not _SHA256_RE.fullmatch(supplied_hash):
        raise ValueError("candidate_vocabulary_sha256 must be a lowercase SHA-256")
    unhashed = json.loads(json.dumps(normalized, ensure_ascii=False))
    unhashed.pop("candidate_vocabulary_sha256", None)
    if supplied_hash != canonical_json_sha256(unhashed):
        raise ValueError("candidate_vocabulary_sha256 mismatch")
    return normalized


def seal_independent_score_capture(payload: Mapping[str, Any]) -> dict[str, Any]:
    normalized = json.loads(json.dumps(payload, ensure_ascii=False))
    normalized.pop("independent_score_capture_sha256", None)
    normalized["independent_score_capture_sha256"] = canonical_json_sha256(normalized)
    return normalized


def validate_independent_score_capture(
    vocabulary: Mapping[str, Any],
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Recompute every independent top-k union from sealed full raw scores."""

    validated_vocabulary = validate_candidate_vocabulary(vocabulary)
    normalized = json.loads(json.dumps(payload, ensure_ascii=False))
    if normalized.get("independent_score_capture_version") != (
        INDEPENDENT_SCORE_CAPTURE_VERSION
    ):
        raise ValueError("unsupported independent_score_capture_version")
    if normalized.get("phase") != PHASE or normalized.get("status") != "raw_scores_sealed":
        raise ValueError("independent score capture must be sealed J1.1B raw scores")
    if normalized.get("candidate_vocabulary_sha256") != validated_vocabulary.get(
        "candidate_vocabulary_sha256"
    ):
        raise ValueError("candidate vocabulary binding mismatch")
    try:
        captured_at = datetime.fromisoformat(
            str(normalized.get("captured_at") or "").replace("Z", "+00:00")
        )
    except ValueError as exc:
        raise ValueError("captured_at must be an ISO timestamp") from exc
    if captured_at.tzinfo is None or captured_at.utcoffset() is None:
        raise ValueError("captured_at must include a timezone")

    global_concepts = {
        item["concept_id"]: dict(item)
        for item in validated_vocabulary["eligible_concepts"]
    }
    scopes = {
        int(item["order"]): dict(item)
        for item in validated_vocabulary["question_scopes"]
    }
    questions = list(normalized.get("questions") or [])
    if normalized.get("question_count") != len(questions) or len(questions) != len(scopes):
        raise ValueError("score capture question_count mismatch")
    if {int(item.get("order", -1)) for item in questions} != set(scopes):
        raise ValueError("score capture orders mismatch")

    for question in questions:
        order = int(question["order"])
        scope = scopes[order]
        excluded_ids = {
            item["concept_id"] for item in scope.get("cue_exclusions") or []
        }
        expected_concepts = [
            concept for concept_id, concept in global_concepts.items()
            if concept_id not in excluded_ids
        ]
        if question.get("question_id") != scope.get("question_id"):
            raise ValueError("score capture question_id mismatch")
        if question.get("question_sha256") != scope.get("question_sha256"):
            raise ValueError("score capture question_sha256 mismatch")
        if question.get("eligible_concept_count") != len(expected_concepts):
            raise ValueError("score capture eligible_concept_count mismatch")
        rebuilt = build_independent_union(
            expected_concepts,
            question.get("graph_raw_scores") or [],
            question.get("local_core_raw_scores") or [],
            top_k=DEFAULT_TOP_K,
        )
        if question.get("independent_union") != rebuilt:
            raise ValueError("stored independent union does not reproduce")

    required_values = {
        "database_writes": False,
        "learning_enabled": False,
        "gpu_inference_executed": True,
        "probabilities_computed": False,
        "calibrator_fit_allowed": False,
        "heldout_gate": False,
        "performance_claim_gate": False,
        "production_promotion_gate": False,
    }
    for field, expected in required_values.items():
        if normalized.get(field) != expected:
            raise ValueError(f"{field} must be {expected!r} for raw-score capture")
    supplied_hash = str(normalized.get("independent_score_capture_sha256") or "")
    if not _SHA256_RE.fullmatch(supplied_hash):
        raise ValueError("independent_score_capture_sha256 must be a SHA-256")
    unhashed = json.loads(json.dumps(normalized, ensure_ascii=False))
    unhashed.pop("independent_score_capture_sha256", None)
    if supplied_hash != canonical_json_sha256(unhashed):
        raise ValueError("independent_score_capture_sha256 mismatch")
    return normalized


def seal_union_label_pack(payload: Mapping[str, Any]) -> dict[str, Any]:
    normalized = json.loads(json.dumps(payload, ensure_ascii=False))
    normalized.pop("union_label_pack_sha256", None)
    normalized["union_label_pack_sha256"] = canonical_json_sha256(normalized)
    return normalized


def validate_union_label_pack(
    capture: Mapping[str, Any],
    answer_pack: Mapping[str, Any],
    payload: Mapping[str, Any],
    *,
    require_user_review: bool = False,
) -> dict[str, Any]:
    """Bind semantic decisions to every independent-union candidate exactly once."""

    normalized_capture = json.loads(json.dumps(capture, ensure_ascii=False))
    normalized = json.loads(json.dumps(payload, ensure_ascii=False))
    if normalized.get("union_label_pack_version") != UNION_LABEL_PACK_VERSION:
        raise ValueError("unsupported union_label_pack_version")
    if normalized.get("phase") != PHASE:
        raise ValueError("union labels must be J1.1B")
    if normalized.get("independent_score_capture_sha256") != normalized_capture.get(
        "independent_score_capture_sha256"
    ):
        raise ValueError("independent score capture binding mismatch")
    if normalized.get("reviewed_reference_answer_pack_sha256") != answer_pack.get(
        "reference_answer_pack_sha256"
    ):
        raise ValueError("reviewed reference answer binding mismatch")
    if answer_pack.get("review_status") != "user_reviewed":
        raise ValueError("union labels require user-reviewed reference answers")
    if normalized.get("semantic_label_source") != (
        "external_teacher_drafted_against_user_reviewed_reference_answers"
    ):
        raise ValueError("union label source mismatch")

    review_status = normalized.get("review_status")
    if review_status == "awaiting_user_review":
        if normalized.get("reviewer_role") != "assistant_draft":
            raise ValueError("draft union labels require reviewer_role=assistant_draft")
        if normalized.get("reviewed_at") is not None:
            raise ValueError("draft union labels cannot have reviewed_at")
        allowed_decisions = _DRAFT_LABEL_DECISIONS
    elif review_status == "user_reviewed":
        if normalized.get("reviewer_role") != "user":
            raise ValueError("reviewed union labels require reviewer_role=user")
        try:
            reviewed_at = datetime.fromisoformat(
                str(normalized.get("reviewed_at") or "").replace("Z", "+00:00")
            )
        except ValueError as exc:
            raise ValueError("reviewed_at must be an ISO timestamp") from exc
        if reviewed_at.tzinfo is None or reviewed_at.utcoffset() is None:
            raise ValueError("reviewed_at must include a timezone")
        allowed_decisions = _REVIEWED_LABEL_DECISIONS
    else:
        raise ValueError("invalid union label review_status")
    if require_user_review and review_status != "user_reviewed":
        raise ValueError("union labels require explicit user review")

    answers = {
        int(item["order"]): dict(item) for item in answer_pack.get("answers") or []
    }
    captures = {
        int(item["order"]): dict(item)
        for item in normalized_capture.get("questions") or []
    }
    entries = list(normalized.get("entries") or [])
    if normalized.get("label_count") != sum(
        len(entry.get("labels") or []) for entry in entries
    ):
        raise ValueError("union label_count mismatch")
    if len(entries) != len(captures) or {
        int(item.get("order", -1)) for item in entries
    } != set(captures):
        raise ValueError("union label entries must cover every capture question")

    for entry in entries:
        order = int(entry["order"])
        captured = captures[order]
        answer = answers[order]
        if entry.get("question_id") != captured.get("question_id"):
            raise ValueError("union label question_id mismatch")
        if entry.get("question_sha256") != captured.get("question_sha256"):
            raise ValueError("union label question_sha256 mismatch")
        if entry.get("answer_sha256") != answer.get("answer_sha256"):
            raise ValueError("union label answer_sha256 mismatch")
        universe = {
            item["concept_id"]: item["concept_name"]
            for item in captured["independent_union"]["union"]
        }
        labels = list(entry.get("labels") or [])
        if len(labels) != len(universe):
            raise ValueError("union labels must decide the complete independent union")
        seen: set[str] = set()
        for label in labels:
            concept_id = str(label.get("concept_id") or "")
            if (
                not concept_id
                or concept_id in seen
                or universe.get(concept_id) != label.get("concept_name")
            ):
                raise ValueError("union label is duplicate or outside the sealed union")
            if label.get("decision") not in allowed_decisions:
                raise ValueError("union label decision is invalid for review status")
            if not str(label.get("rationale") or "").strip():
                raise ValueError("union label rationale is required")
            seen.add(concept_id)

    required_false = (
        "user_direct_answers",
        "database_writes",
        "learning_enabled",
        "probabilities_computed",
        "calibrator_fit_allowed",
        "heldout_gate",
        "performance_claim_gate",
        "production_promotion_gate",
    )
    if any(normalized.get(field) is not False for field in required_false):
        raise ValueError("union labels cannot enable downstream gates")
    supplied_hash = str(normalized.get("union_label_pack_sha256") or "")
    if not _SHA256_RE.fullmatch(supplied_hash):
        raise ValueError("union_label_pack_sha256 must be a SHA-256")
    unhashed = json.loads(json.dumps(normalized, ensure_ascii=False))
    unhashed.pop("union_label_pack_sha256", None)
    if supplied_hash != canonical_json_sha256(unhashed):
        raise ValueError("union_label_pack_sha256 mismatch")
    return normalized


def build_union_label_readiness_report(
    capture: Mapping[str, Any],
    answer_pack: Mapping[str, Any],
    label_pack: Mapping[str, Any],
) -> dict[str, Any]:
    labels = validate_union_label_pack(capture, answer_pack, label_pack)
    capture_by_order = {
        int(item["order"]): item for item in capture.get("questions") or []
    }
    counts = {"approved": 0, "rejected": 0, "uncertain": 0}
    positive_orders: list[int] = []
    graph_positive_orders: list[int] = []
    local_positive_orders: list[int] = []
    draft = labels["review_status"] != "user_reviewed"
    per_question = []
    for entry in sorted(labels["entries"], key=lambda item: int(item["order"])):
        order = int(entry["order"])
        approved_ids = set()
        approved_names: list[str] = []
        uncertain_names: list[str] = []
        local_counts = {"approved": 0, "rejected": 0, "uncertain": 0}
        for label in entry["labels"]:
            decision = str(label["decision"])
            if draft:
                decision = decision.removeprefix("proposed_")
            counts[decision] += 1
            local_counts[decision] += 1
            if decision == "approved":
                approved_ids.add(label["concept_id"])
                approved_names.append(label["concept_name"])
            elif decision == "uncertain":
                uncertain_names.append(label["concept_name"])
        union = capture_by_order[order]["independent_union"]
        graph_positive = bool(approved_ids & set(union["graph_top_k_ids"]))
        local_positive = bool(approved_ids & set(union["local_core_top_k_ids"]))
        if approved_ids:
            positive_orders.append(order)
        if graph_positive:
            graph_positive_orders.append(order)
        if local_positive:
            local_positive_orders.append(order)
        per_question.append({
            "order": order,
            "decision_counts": local_counts,
            "approved_names": approved_names,
            "uncertain_names": uncertain_names,
            "graph_positive_coverage": graph_positive,
            "local_core_positive_coverage": local_positive,
        })
    question_count = len(per_question)
    review_gate = labels["review_status"] == "user_reviewed"
    coverage_gate = (
        len(positive_orders) == question_count
        and len(graph_positive_orders) == question_count
        and len(local_positive_orders) == question_count
    )
    return {
        "phase": PHASE,
        "status": (
            "reviewed_pending_calibrator_design_audit"
            if review_gate and coverage_gate else
            "awaiting_user_review_of_independent_union_labels"
        ),
        "review_status": labels["review_status"],
        "question_count": question_count,
        "candidate_label_count": sum(counts.values()),
        "decision_counts": counts,
        "question_positive_coverage_count": len(positive_orders),
        "graph_positive_coverage_count": len(graph_positive_orders),
        "local_core_positive_coverage_count": len(local_positive_orders),
        "dual_predictor_positive_coverage_gate": coverage_gate,
        "fair_candidate_universe_gate": True,
        "explicit_user_review_gate": review_gate,
        "calibrator_fit_gate": False,
        "per_question": per_question,
        "database_writes": False,
        "learning_enabled": False,
        "probabilities_computed": False,
        "heldout_gate": False,
        "performance_claim_gate": False,
        "production_promotion_gate": False,
        "block_reasons": (
            ["explicit_user_review_of_independent_union_labels_missing"]
            if not review_gate else
            ([] if coverage_gate else ["dual_predictor_positive_coverage_missing"])
        ),
        "next_step": (
            "user_batch_review_independent_union_label_draft"
            if not review_gate else
            "audit_train_only_calibrator_design_before_any_fit"
        ),
    }
