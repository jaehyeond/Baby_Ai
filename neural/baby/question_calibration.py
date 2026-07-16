"""Fail-closed J1.1 preregistration and raw-score capture contracts.

This module is deliberately pure: it does not import Neo4j, torch, the API
server, or the protected conversation handler.  J1.1 captures uncalibrated
predictor scores before questions are shown to the user.  It must not invent
relevance probabilities before reviewed answer labels exist.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping

from neural.baby.pending_question_semantics import canonical_json_sha256


QUESTION_CALIBRATION_MANIFEST_VERSION = 1
RAW_SCORE_PACK_VERSION = 1
PHASE = "J1.1"
SPLIT = "train_calibration"
PURPOSE = "probability_calibration_only"
RAW_SCORE_MODE = "offline_shadow_read_only"
REQUIRED_PREDICTORS = ("graph", "local_core")
MIN_CONCEPT_UNIVERSE = 4
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


def _question_sha256(question: str) -> str:
    return hashlib.sha256(question.encode("utf-8")).hexdigest()


def _without_key(payload: Mapping[str, Any], key: str) -> dict[str, Any]:
    normalized = _clone(payload)
    normalized.pop(key, None)
    return normalized


def _validate_manifest_body(manifest: Mapping[str, Any]) -> dict[str, Any]:
    normalized = _clone(manifest)
    if normalized.get("question_calibration_manifest_version") != QUESTION_CALIBRATION_MANIFEST_VERSION:
        raise ValueError("unsupported question_calibration_manifest_version")
    if normalized.get("phase") != PHASE:
        raise ValueError("manifest phase must be J1.1")
    if normalized.get("split") != SPLIT:
        raise ValueError("J1.1 calibration manifest must be train_calibration")
    if normalized.get("purpose") != PURPOSE:
        raise ValueError("manifest purpose must be probability_calibration_only")
    if not str(normalized.get("manifest_id") or "").strip():
        raise ValueError("manifest_id is required")
    _zoned_datetime(normalized.get("created_at"), "created_at")
    _zoned_datetime(normalized.get("approval_recorded_at"), "approval_recorded_at")

    approvals = set(normalized.get("user_approval_scope") or [])
    required_approvals = {
        "local_core_gpu_read_only_inference",
        "new_question_answer_collection",
    }
    if not required_approvals.issubset(approvals):
        raise ValueError("manifest is missing explicit J1.1 user approval scope")

    constraints = dict(normalized.get("constraints") or {})
    required_false = (
        "database_writes",
        "learning_enabled",
        "heldout_collection",
        "production_promotion",
        "questions_revealed_before_raw_capture",
    )
    if any(constraints.get(field) is not False for field in required_false):
        raise ValueError("J1.1 manifest constraints must keep writes, learning, heldout, promotion, and early reveal disabled")
    if constraints.get("calibrator_fit_before_reviewed_answers") is not False:
        raise ValueError("calibrator fitting must wait for reviewed answers")

    questions = list(normalized.get("questions") or [])
    if len(questions) < 2:
        raise ValueError("J1.1 requires at least two preregistered questions")
    if normalized.get("question_count") != len(questions):
        raise ValueError("question_count does not match questions")
    expected_orders = list(range(len(questions)))
    if [item.get("order") for item in questions] != expected_orders:
        raise ValueError("question orders must be contiguous and zero-based")

    seen_ids: set[str] = set()
    seen_questions: set[str] = set()
    for item in questions:
        question_id = str(item.get("question_id") or "").strip()
        question = str(item.get("question") or "").strip()
        cue_terms = [str(term).strip() for term in item.get("cue_terms") or []]
        if not question_id or question_id in seen_ids:
            raise ValueError("question_id must be non-empty and unique")
        if not question or question in seen_questions:
            raise ValueError("question text must be non-empty and unique")
        if not 1 <= len(cue_terms) <= 4 or any(not term for term in cue_terms):
            raise ValueError("each question requires one to four non-empty cue terms")
        if len(set(cue_terms)) != len(cue_terms):
            raise ValueError("cue terms must be unique within a question")
        if item.get("question_sha256") != _question_sha256(question):
            raise ValueError("question_sha256 mismatch")
        seen_ids.add(question_id)
        seen_questions.add(question)
    return normalized


def seal_question_manifest(draft: Mapping[str, Any]) -> dict[str, Any]:
    """Add exact question hashes and a canonical contract hash to a draft."""

    normalized = _clone(draft)
    normalized.pop("contract_sha256", None)
    for item in normalized.get("questions") or []:
        question = str(item.get("question") or "").strip()
        item["question"] = question
        item["question_sha256"] = _question_sha256(question)
    _validate_manifest_body(normalized)
    normalized["contract_sha256"] = canonical_json_sha256(normalized)
    return normalized


def validate_preregistered_manifest(manifest: Mapping[str, Any]) -> dict[str, Any]:
    normalized = _validate_manifest_body(manifest)
    expected = canonical_json_sha256(_without_key(normalized, "contract_sha256"))
    actual = _require_sha256(normalized.get("contract_sha256"), "contract_sha256")
    if actual != expected:
        raise ValueError("manifest contract_sha256 mismatch")
    return normalized


def rank_raw_scores(items: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Return deterministic descending ranks without converting scores to probabilities."""

    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw_item in items:
        item = dict(raw_item)
        concept_id = str(item.get("concept_id") or "").strip()
        concept_name = str(item.get("concept_name") or "").strip()
        try:
            raw_score = float(item.get("raw_score"))
        except (TypeError, ValueError) as exc:
            raise ValueError("raw_score must be numeric") from exc
        if not concept_id or concept_id in seen or not concept_name:
            raise ValueError("raw scores require unique concept IDs and names")
        if not math.isfinite(raw_score):
            raise ValueError("raw_score must be finite")
        normalized.append({
            "concept_id": concept_id,
            "concept_name": concept_name,
            "raw_score": raw_score,
        })
        seen.add(concept_id)
    normalized.sort(key=lambda item: (-item["raw_score"], item["concept_id"]))
    return [{**item, "rank": index + 1} for index, item in enumerate(normalized)]


def _validate_ranked_scores(
    items: Iterable[Mapping[str, Any]],
    *,
    field: str,
) -> list[dict[str, Any]]:
    supplied = [dict(item) for item in items]
    expected = rank_raw_scores(supplied)
    if supplied != expected:
        raise ValueError(f"{field} raw scores are not deterministically ranked")
    return supplied


def _find_forbidden_probability_fields(value: Any, path: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            if key in {"probability", "concept_probabilities", "relevance_probability"}:
                found.append(child_path)
            found.extend(_find_forbidden_probability_fields(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_find_forbidden_probability_fields(child, f"{path}[{index}]"))
    return found


def seal_raw_score_pack(pack: Mapping[str, Any]) -> dict[str, Any]:
    normalized = _clone(pack)
    normalized.pop("raw_score_pack_sha256", None)
    for question in normalized.get("questions") or []:
        question.pop("question_snapshot_sha256", None)
        question["question_snapshot_sha256"] = canonical_json_sha256(question)
    normalized["raw_score_pack_sha256"] = canonical_json_sha256(normalized)
    return normalized


def validate_raw_score_pack(
    manifest: Mapping[str, Any],
    pack: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate question binding, identical universes, provenance, and no-learning gates."""

    registered = validate_preregistered_manifest(manifest)
    normalized = _clone(pack)
    if normalized.get("raw_score_pack_version") != RAW_SCORE_PACK_VERSION:
        raise ValueError("unsupported raw_score_pack_version")
    if normalized.get("phase") != PHASE or normalized.get("mode") != RAW_SCORE_MODE:
        raise ValueError("raw score pack must use J1.1 offline shadow mode")
    if normalized.get("split") != SPLIT:
        raise ValueError("raw score pack must remain train_calibration")
    if normalized.get("manifest_id") != registered.get("manifest_id"):
        raise ValueError("raw score manifest_id mismatch")
    if normalized.get("contract_sha256") != registered.get("contract_sha256"):
        raise ValueError("raw score contract_sha256 mismatch")

    required_false = (
        "learning_enabled",
        "database_writes",
        "gradients_enabled",
        "optimizer_created",
        "questions_revealed_before_capture",
        "probabilities_created",
        "calibrator_fitted",
        "heldout_gate",
        "performance_claim_gate",
        "production_promotion_gate",
    )
    if any(normalized.get(field) is not False for field in required_false):
        raise ValueError("raw score pack violates a no-learning/no-write/no-claim gate")
    if normalized.get("gpu_inference_read_only") is not True:
        raise ValueError("local-core capture must be explicitly read-only GPU inference")
    forbidden = _find_forbidden_probability_fields(normalized)
    if forbidden:
        raise ValueError(f"uncalibrated raw pack contains probability fields: {forbidden[0]}")

    manifest_time = _zoned_datetime(registered.get("created_at"), "manifest.created_at")
    pack_created = _zoned_datetime(normalized.get("created_at"), "pack.created_at")
    sealed_at = _zoned_datetime(normalized.get("sealed_at"), "pack.sealed_at")
    if manifest_time > pack_created or pack_created > sealed_at:
        raise ValueError("manifest must precede raw capture and raw capture must precede sealing")

    graph_model_hash = _require_sha256(
        normalized.get("graph_model_snapshot_sha256"),
        "graph_model_snapshot_sha256",
    )
    local_model_hash = _require_sha256(
        normalized.get("local_core_model_snapshot_sha256"),
        "local_core_model_snapshot_sha256",
    )
    _require_sha256(normalized.get("graph_implementation_sha256"), "graph_implementation_sha256")
    _require_sha256(normalized.get("local_core_adapter_sha256"), "local_core_adapter_sha256")
    if normalized.get("graph_snapshot_scope") != "query_scoped_not_full_database":
        raise ValueError("graph snapshot scope must state its query-scoped limitation")
    if str(normalized.get("local_core_device") or "").split(":", 1)[0] != "cuda":
        raise ValueError("J1.1 approved inference must run on CUDA")
    if int(normalized.get("local_core_trainable_parameter_count", -1)) != 0:
        raise ValueError("read-only local core must expose zero trainable parameters")

    manifest_questions = {
        int(item["order"]): dict(item)
        for item in registered.get("questions") or []
    }
    pack_questions = list(normalized.get("questions") or [])
    if len(pack_questions) != len(manifest_questions):
        raise ValueError("raw pack question count mismatch")
    if normalized.get("question_count") != len(pack_questions):
        raise ValueError("raw pack question_count mismatch")

    total_scores = 0
    for question in pack_questions:
        order = int(question.get("order", -1))
        expected_question = manifest_questions.get(order)
        if expected_question is None:
            raise ValueError("raw pack contains an unknown question order")
        for field in ("question_id", "question", "question_sha256", "cue_terms"):
            if question.get(field) != expected_question.get(field):
                raise ValueError(f"raw pack {field} mismatch at order {order}")

        concepts = [dict(item) for item in question.get("concept_universe") or []]
        concept_ids = [str(item.get("concept_id") or "") for item in concepts]
        if len(concepts) < MIN_CONCEPT_UNIVERSE or len(set(concept_ids)) != len(concepts):
            raise ValueError("every question requires a unique concept universe of at least four")
        if any(not concept_id or not str(item.get("concept_name") or "").strip() for concept_id, item in zip(concept_ids, concepts)):
            raise ValueError("concept universe IDs and names must be non-empty")

        predictors = dict(question.get("predictors") or {})
        if set(predictors) != set(REQUIRED_PREDICTORS):
            raise ValueError("every question requires graph and local_core raw scores")
        for predictor_name, expected_hash in (
            ("graph", graph_model_hash),
            ("local_core", local_model_hash),
        ):
            predictor = dict(predictors[predictor_name])
            if predictor.get("predictor") != predictor_name:
                raise ValueError("predictor identity mismatch")
            if predictor.get("model_snapshot_sha256") != expected_hash:
                raise ValueError("predictor model snapshot hash mismatch")
            captured_at = _zoned_datetime(
                predictor.get("captured_at"),
                f"question[{order}].{predictor_name}.captured_at",
            )
            if captured_at < manifest_time or captured_at > sealed_at:
                raise ValueError("predictor capture must be after preregistration and before sealing")
            expected_type = (
                "graph_max_relationship_strength"
                if predictor_name == "graph"
                else "mean_conditional_token_log_probability"
            )
            if predictor.get("raw_score_type") != expected_type:
                raise ValueError("unexpected predictor raw_score_type")
            scores = _validate_ranked_scores(
                predictor.get("raw_scores") or [],
                field=f"question[{order}].{predictor_name}",
            )
            if {item["concept_id"] for item in scores} != set(concept_ids):
                raise ValueError("graph and local_core must score the exact concept universe")
            total_scores += len(scores)

        question_hash = _require_sha256(
            question.get("question_snapshot_sha256"),
            f"question[{order}].question_snapshot_sha256",
        )
        expected_hash = canonical_json_sha256(_without_key(question, "question_snapshot_sha256"))
        if question_hash != expected_hash:
            raise ValueError("question snapshot hash mismatch")

    if normalized.get("raw_score_count_per_predictor") * 2 != total_scores:
        raise ValueError("raw_score_count_per_predictor mismatch")
    pack_hash = _require_sha256(
        normalized.get("raw_score_pack_sha256"),
        "raw_score_pack_sha256",
    )
    expected_pack_hash = canonical_json_sha256(_without_key(normalized, "raw_score_pack_sha256"))
    if pack_hash != expected_pack_hash:
        raise ValueError("raw_score_pack_sha256 mismatch")
    return normalized
