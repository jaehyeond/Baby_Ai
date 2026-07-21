"""Contracts for a lightweight pre-answer exploratory question probe.

This path deliberately does not preregister a confirmatory experiment.  It
captures read-only Graph and Local-Core rankings before answers are collected,
then permanently marks the questions as ineligible for confirmatory reuse.
"""

from __future__ import annotations

from datetime import datetime
import json
from typing import Any, Iterable, Mapping

from neural.baby.candidate_universe import (
    DEFAULT_TOP_K,
    build_independent_union,
    classify_candidate_vocabulary,
    exclude_question_cue_surfaces,
)
from neural.baby.pending_question_semantics import canonical_json_sha256
from neural.baby.question_calibration import (
    _question_sha256 as question_text_sha256,
    rank_raw_scores,
)


EXPLORATORY_MANIFEST_VERSION = 1
EXPLORATORY_CAPTURE_VERSION = 1
EXPLORATORY_PHASE = "J1-EXP-1"
EXPLORATORY_MANIFEST_STATUS = (
    "exploratory_questions_public_unanswered_not_for_claim"
)
EXPLORATORY_CAPTURE_STATUS = (
    "exploratory_pre_answer_raw_scores_captured_not_for_claim"
)
EXPLORATORY_EVIDENCE_SCOPE = "diagnostic_only_not_confirmatory_evidence"
EXPLORATORY_NEXT_STEP = (
    "collect_user_answers_then_run_lightweight_exploratory_signal_audit"
)

REQUIRED_FALSE_CONSTRAINTS = (
    "database_writes",
    "learning_enabled",
    "calibrator_fit",
    "probabilities_computed",
    "heldout_collection",
    "performance_claim",
    "production_promotion",
)
REQUIRED_FALSE_CAPTURE_FIELDS = (
    "database_writes",
    "learning_enabled",
    "probabilities_computed",
    "calibrator_fit_allowed",
    "heldout_gate",
    "performance_claim_gate",
    "production_promotion_gate",
    "confirmatory_reuse_allowed",
)
FORBIDDEN_MANIFEST_FIELDS = frozenset({
    "approval_recorded_at",
    "contract_sha256",
    "user_approval_scope",
})
FORBIDDEN_CAPTURE_FIELDS = frozenset({
    "answer",
    "answers",
    "candidate_labels",
    "label_pack",
    "review_decisions",
    "reviewed_answer_pack",
})


def _clone(value: Mapping[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(value, ensure_ascii=False))


def _require_zoned(value: Any, field: str) -> str:
    text = str(value or "")
    if not text:
        raise ValueError(f"{field} must be a non-empty ISO timestamp")
    parsed = datetime.fromisoformat(
        text[:-1] + "+00:00" if text.endswith("Z") else text
    )
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} must include a timezone offset")
    return text


def _require_sha256(value: Any, field: str) -> str:
    text = str(value or "")
    if len(text) != 64 or any(char not in "0123456789abcdef" for char in text):
        raise ValueError(f"{field} must be lowercase hex sha256")
    return text


def _walk_forbidden_fields(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key) in FORBIDDEN_CAPTURE_FIELDS:
                raise ValueError(f"exploratory capture forbids field: {key}")
            _walk_forbidden_fields(child)
    elif isinstance(value, list):
        for child in value:
            _walk_forbidden_fields(child)


def validate_exploratory_question_manifest(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate and fingerprint an explicitly non-confirmatory question batch."""

    normalized = _clone(payload)
    forbidden = sorted(FORBIDDEN_MANIFEST_FIELDS & set(normalized))
    if forbidden:
        raise ValueError(
            "exploratory manifest must not carry sealing fields: "
            + ",".join(forbidden)
        )
    if normalized.get("exploratory_question_manifest_version") != (
        EXPLORATORY_MANIFEST_VERSION
    ):
        raise ValueError("unsupported exploratory question manifest version")
    if normalized.get("phase") != EXPLORATORY_PHASE:
        raise ValueError("exploratory manifest phase mismatch")
    if normalized.get("status") != EXPLORATORY_MANIFEST_STATUS:
        raise ValueError("exploratory manifest status mismatch")
    if normalized.get("evidence_scope") != EXPLORATORY_EVIDENCE_SCOPE:
        raise ValueError("exploratory manifest evidence scope mismatch")
    if not str(normalized.get("manifest_id") or "").strip():
        raise ValueError("exploratory manifest_id is required")
    _require_zoned(normalized.get("prepared_at"), "prepared_at")

    if normalized.get("questions_public_before_raw_capture") is not True:
        raise ValueError("exploratory manifest must disclose public questions")
    if normalized.get("answers_available_before_capture") is not False:
        raise ValueError("exploratory manifest requires unanswered questions")
    if normalized.get("confirmatory_reuse_allowed") is not False:
        raise ValueError("exploratory questions cannot be reused for confirmation")

    constraints = dict(normalized.get("constraints") or {})
    offending = [
        field
        for field in REQUIRED_FALSE_CONSTRAINTS
        if constraints.get(field) is not False
    ]
    if offending:
        raise ValueError(
            "exploratory constraints must stay false: "
            + ",".join(sorted(offending))
        )

    questions = list(normalized.get("questions") or [])
    if len(questions) < 2:
        raise ValueError("exploratory probe requires at least two questions")
    if normalized.get("question_count") != len(questions):
        raise ValueError("exploratory question_count mismatch")
    if [item.get("order") for item in questions] != list(range(len(questions))):
        raise ValueError("exploratory question orders must be contiguous")

    seen_ids: set[str] = set()
    seen_texts: set[str] = set()
    for item in questions:
        question_id = str(item.get("question_id") or "").strip()
        question = str(item.get("question") or "").strip()
        cue_terms = [str(term).strip() for term in item.get("cue_terms") or []]
        if not question_id or question_id in seen_ids:
            raise ValueError("exploratory question IDs must be unique")
        if not question or question in seen_texts:
            raise ValueError("exploratory question text must be unique")
        if not 1 <= len(cue_terms) <= 4 or any(not term for term in cue_terms):
            raise ValueError("exploratory questions require one to four cue terms")
        if len(set(cue_terms)) != len(cue_terms):
            raise ValueError("exploratory cue terms must be unique per question")
        item["question_id"] = question_id
        item["question"] = question
        item["cue_terms"] = cue_terms
        item["question_sha256"] = question_text_sha256(question)
        seen_ids.add(question_id)
        seen_texts.add(question)

    normalized.pop("manifest_snapshot_sha256", None)
    normalized["manifest_snapshot_sha256"] = canonical_json_sha256(normalized)
    return normalized


def _score_map(
    scores_by_order: Mapping[int, Iterable[Mapping[str, Any]]],
    order: int,
    predictor: str,
) -> list[dict[str, Any]]:
    try:
        raw = scores_by_order[order]
    except KeyError as error:
        raise ValueError(f"missing {predictor} scores for order {order}") from error
    return rank_raw_scores(raw)


def _top_rows(rows: list[dict[str, Any]], top_k: int) -> list[dict[str, Any]]:
    return [dict(item) for item in rows[:top_k]]


def build_exploratory_pre_answer_capture(
    manifest: Mapping[str, Any],
    source_concepts: Iterable[Mapping[str, Any]],
    graph_scores_by_order: Mapping[int, Iterable[Mapping[str, Any]]],
    local_scores_by_order: Mapping[int, Iterable[Mapping[str, Any]]],
    *,
    graph_predictor: Mapping[str, Any],
    local_core_predictor: Mapping[str, Any],
    captured_at: str,
) -> dict[str, Any]:
    """Build one compact diagnostic artifact from full-vocabulary raw scores."""

    normalized_manifest = validate_exploratory_question_manifest(manifest)
    concepts = sorted(
        [
            {
                "id": str(item.get("id") or ""),
                "name": str(item.get("name") or ""),
            }
            for item in source_concepts
        ],
        key=lambda item: (item["id"], item["name"]),
    )
    eligible, rejected = classify_candidate_vocabulary(concepts)
    if len(eligible) < DEFAULT_TOP_K:
        raise ValueError("exploratory probe has fewer than top_k eligible concepts")

    expected_orders = {int(item["order"]) for item in normalized_manifest["questions"]}
    if {int(item) for item in graph_scores_by_order} != expected_orders:
        raise ValueError("graph score orders do not match exploratory manifest")
    if {int(item) for item in local_scores_by_order} != expected_orders:
        raise ValueError("local-core score orders do not match exploratory manifest")

    questions: list[dict[str, Any]] = []
    for question in normalized_manifest["questions"]:
        order = int(question["order"])
        scoped, cue_exclusions = exclude_question_cue_surfaces(
            eligible, question["cue_terms"]
        )
        graph_scores = _score_map(graph_scores_by_order, order, "graph")
        local_scores = _score_map(local_scores_by_order, order, "local-core")
        union = build_independent_union(
            scoped,
            graph_scores,
            local_scores,
            top_k=DEFAULT_TOP_K,
        )
        graph_top = _top_rows(graph_scores, DEFAULT_TOP_K)
        local_top = _top_rows(local_scores, DEFAULT_TOP_K)
        questions.append({
            "order": order,
            "question_id": question["question_id"],
            "question": question["question"],
            "question_sha256": question["question_sha256"],
            "cue_terms": list(question["cue_terms"]),
            "eligible_concept_count": len(scoped),
            "cue_exclusions": cue_exclusions,
            "graph_full_score_count": len(graph_scores),
            "graph_full_scores_sha256": canonical_json_sha256(graph_scores),
            "graph_top_k": graph_top,
            "local_core_full_score_count": len(local_scores),
            "local_core_full_scores_sha256": canonical_json_sha256(local_scores),
            "local_core_top_k": local_top,
            "top_k_overlap_count": len(
                {item["concept_id"] for item in graph_top}
                & {item["concept_id"] for item in local_top}
            ),
            "independent_union": union,
        })

    graph_metadata = _clone(graph_predictor)
    local_metadata = _clone(local_core_predictor)
    _require_sha256(
        graph_metadata.get("implementation_sha256"),
        "graph_predictor.implementation_sha256",
    )
    _require_sha256(
        local_metadata.get("adapter_sha256"),
        "local_core_predictor.adapter_sha256",
    )
    _require_sha256(
        local_metadata.get("model_snapshot_sha256"),
        "local_core_predictor.model_snapshot_sha256",
    )
    if local_metadata.get("trainable_parameter_count") != 0:
        raise ValueError("exploratory local-core capture must be read-only")

    result = {
        "exploratory_pre_answer_capture_version": EXPLORATORY_CAPTURE_VERSION,
        "phase": EXPLORATORY_PHASE,
        "status": EXPLORATORY_CAPTURE_STATUS,
        "evidence_scope": EXPLORATORY_EVIDENCE_SCOPE,
        "captured_at": _require_zoned(captured_at, "captured_at"),
        "manifest_id": normalized_manifest["manifest_id"],
        "manifest_snapshot_sha256": normalized_manifest["manifest_snapshot_sha256"],
        "questions_public_before_raw_capture": True,
        "answers_available_before_capture": False,
        "captured_before_answers": True,
        "exploratory_not_for_claim": True,
        "confirmatory_reuse_allowed": False,
        "source_concept_count": len(concepts),
        "eligible_concept_count": len(eligible),
        "rejected_concept_count": len(rejected),
        "graph_snapshot_sha256": canonical_json_sha256({"concepts": concepts}),
        "graph_predictor": graph_metadata,
        "local_core_predictor": local_metadata,
        "question_count": len(questions),
        "questions": questions,
        "exploratory_capture_gate": True,
        "gpu_inference_executed": True,
        "database_writes": False,
        "learning_enabled": False,
        "probabilities_computed": False,
        "calibrator_fit_allowed": False,
        "heldout_gate": False,
        "performance_claim_gate": False,
        "production_promotion_gate": False,
        "block_reasons": [
            "answers_not_collected",
            "exploratory_only_not_confirmatory",
        ],
        "next_step": EXPLORATORY_NEXT_STEP,
    }
    result["exploratory_pre_answer_capture_sha256"] = canonical_json_sha256(result)
    return validate_exploratory_pre_answer_capture(result, normalized_manifest)


def validate_exploratory_pre_answer_capture(
    payload: Mapping[str, Any],
    manifest: Mapping[str, Any],
) -> dict[str, Any]:
    normalized_manifest = validate_exploratory_question_manifest(manifest)
    normalized = _clone(payload)
    _walk_forbidden_fields(normalized)

    if normalized.get("exploratory_pre_answer_capture_version") != (
        EXPLORATORY_CAPTURE_VERSION
    ):
        raise ValueError("unsupported exploratory capture version")
    if normalized.get("phase") != EXPLORATORY_PHASE:
        raise ValueError("exploratory capture phase mismatch")
    if normalized.get("status") != EXPLORATORY_CAPTURE_STATUS:
        raise ValueError("exploratory capture status mismatch")
    if normalized.get("evidence_scope") != EXPLORATORY_EVIDENCE_SCOPE:
        raise ValueError("exploratory capture evidence scope mismatch")
    _require_zoned(normalized.get("captured_at"), "captured_at")
    if normalized.get("manifest_id") != normalized_manifest["manifest_id"]:
        raise ValueError("exploratory capture manifest_id mismatch")
    if normalized.get("manifest_snapshot_sha256") != normalized_manifest.get(
        "manifest_snapshot_sha256"
    ):
        raise ValueError("exploratory capture manifest binding mismatch")

    truthy_required = (
        "questions_public_before_raw_capture",
        "captured_before_answers",
        "exploratory_not_for_claim",
        "exploratory_capture_gate",
        "gpu_inference_executed",
    )
    if any(normalized.get(field) is not True for field in truthy_required):
        raise ValueError("exploratory capture truth fields mismatch")
    if normalized.get("answers_available_before_capture") is not False:
        raise ValueError("exploratory capture cannot include prior answers")
    for field in REQUIRED_FALSE_CAPTURE_FIELDS:
        if normalized.get(field) is not False:
            raise ValueError(f"{field} must remain false for exploratory capture")
    if list(normalized.get("block_reasons") or []) != [
        "answers_not_collected",
        "exploratory_only_not_confirmatory",
    ]:
        raise ValueError("exploratory capture block reasons mismatch")
    if normalized.get("next_step") != EXPLORATORY_NEXT_STEP:
        raise ValueError("exploratory capture next_step mismatch")

    source_count = int(normalized.get("source_concept_count", 0))
    global_eligible_count = int(normalized.get("eligible_concept_count", 0))
    rejected_count = int(normalized.get("rejected_concept_count", 0))
    if source_count <= 0 or global_eligible_count < DEFAULT_TOP_K:
        raise ValueError("exploratory concept counts are invalid")
    if global_eligible_count + rejected_count != source_count:
        raise ValueError("exploratory concept counts do not sum")

    questions = list(normalized.get("questions") or [])
    manifest_questions = list(normalized_manifest["questions"])
    if normalized.get("question_count") != len(questions):
        raise ValueError("exploratory capture question_count mismatch")
    if len(questions) != len(manifest_questions):
        raise ValueError("exploratory capture does not cover the manifest")
    for captured, expected in zip(questions, manifest_questions):
        for field in ("order", "question_id", "question", "question_sha256"):
            if captured.get(field) != expected.get(field):
                raise ValueError(f"exploratory capture question {field} mismatch")
        if captured.get("cue_terms") != expected.get("cue_terms"):
            raise ValueError("exploratory capture question cue_terms mismatch")
        question_eligible_count = int(captured.get("eligible_concept_count", 0))
        if captured.get("graph_full_score_count") != question_eligible_count:
            raise ValueError("exploratory graph full-score count mismatch")
        if captured.get("local_core_full_score_count") != question_eligible_count:
            raise ValueError("exploratory local-core full-score count mismatch")
        _require_sha256(
            captured.get("graph_full_scores_sha256"),
            "graph_full_scores_sha256",
        )
        _require_sha256(
            captured.get("local_core_full_scores_sha256"),
            "local_core_full_scores_sha256",
        )
        for field in ("graph_top_k", "local_core_top_k"):
            rows = list(captured.get(field) or [])
            if len(rows) != DEFAULT_TOP_K:
                raise ValueError(f"exploratory {field} count mismatch")
            ids = [str(item.get("concept_id") or "") for item in rows]
            if any(not item for item in ids) or len(ids) != len(set(ids)):
                raise ValueError(f"exploratory {field} IDs must be unique")

        graph_ids = [item["concept_id"] for item in captured["graph_top_k"]]
        local_ids = [item["concept_id"] for item in captured["local_core_top_k"]]
        union = dict(captured.get("independent_union") or {})
        if union.get("eligible_concept_count") != question_eligible_count:
            raise ValueError("exploratory union eligible count mismatch")
        if union.get("graph_top_k_ids") != graph_ids:
            raise ValueError("exploratory union graph top-k mismatch")
        if union.get("local_core_top_k_ids") != local_ids:
            raise ValueError("exploratory union local-core top-k mismatch")
        union_rows = list(union.get("union") or [])
        if union.get("union_count") != len(union_rows):
            raise ValueError("exploratory union_count mismatch")
        if union.get("probabilities_computed") is not False:
            raise ValueError("exploratory union cannot carry probabilities")
        if union.get("calibrator_fit_allowed") is not False:
            raise ValueError("exploratory union cannot enable calibrator fit")
        overlap = len(set(graph_ids) & set(local_ids))
        if captured.get("top_k_overlap_count") != overlap:
            raise ValueError("exploratory top-k overlap count mismatch")

    local_metadata = dict(normalized.get("local_core_predictor") or {})
    graph_metadata = dict(normalized.get("graph_predictor") or {})
    _require_sha256(
        graph_metadata.get("implementation_sha256"),
        "graph_predictor.implementation_sha256",
    )
    if local_metadata.get("trainable_parameter_count") != 0:
        raise ValueError("exploratory local-core capture must remain frozen")
    _require_sha256(
        local_metadata.get("adapter_sha256"),
        "local_core_predictor.adapter_sha256",
    )
    _require_sha256(
        local_metadata.get("model_snapshot_sha256"),
        "local_core_predictor.model_snapshot_sha256",
    )
    _require_sha256(
        normalized.get("graph_snapshot_sha256"),
        "graph_snapshot_sha256",
    )

    supplied = _require_sha256(
        normalized.get("exploratory_pre_answer_capture_sha256"),
        "exploratory_pre_answer_capture_sha256",
    )
    unhashed = _clone(normalized)
    unhashed.pop("exploratory_pre_answer_capture_sha256", None)
    if supplied != canonical_json_sha256(unhashed):
        raise ValueError("exploratory pre-answer capture sha256 mismatch")
    return normalized
