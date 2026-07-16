"""Fail-closed B5.6 contract for action-conditioned question outcomes.

The contract is deliberately independent of ``conversation_handler.py``.  It
normalizes research metadata, validates the pre-display prediction snapshot,
and classifies answer state without changing the production curiosity policy.
"""

from __future__ import annotations

import math
import re
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping

from .live_curiosity import build_curiosity_cue_terms, filter_curiosity_cue_terms


PENDING_QUESTION_ACTION_METADATA_FIELDS = (
    "policy_action_id",
    "question_outcome_split",
    "question_outcome_contract_sha256",
)
PENDING_QUESTION_OUTCOME_SPLITS = frozenset({"train", "heldout"})
_POLICY_ACTION_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{2,127}$")
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_NUMERIC_UNIT_PATTERN = re.compile(r"(?<![\d,])(\d[\d,]*)\s*(시간|분|초)")
_NUMERIC_UNIT_SURFACE_PATTERN = re.compile(
    r"(?<![\d,])\d[\d,]*\s*(?:시간|분|초)[가-힣]*"
)
_KOREAN_TERM_PATTERN = re.compile(r"[가-힣]+")
_ASCII_TERM_PATTERN = re.compile(r"[A-Za-z][A-Za-z0-9._-]*")
_QUESTION_SURFACE_TERM_PATTERN = re.compile(
    r"[가-힣]+|[A-Za-z0-9][A-Za-z0-9._-]*"
)
_OUTCOME_PARTICLES: tuple[str, ...] = tuple(sorted((
    "에서", "에게", "한테", "처럼", "까지", "부터", "조차", "마저", "으로",
    "이랑", "이나", "라도", "라면", "보다", "밖에", "은", "는", "이", "가",
    "을", "를", "의", "와", "과", "도", "만", "로", "랑",
), key=len, reverse=True))
_OUTCOME_PREDICATE_ENDINGS: tuple[str, ...] = (
    "입니다", "합니다", "됩니다", "습니다", "하는", "하고", "하며", "하면", "해서",
)
_NON_CONTENT_PREDICATE_STEMS = frozenset({
    "모르", "맺", "하", "있", "없", "같", "되", "알", "주",
})
_LEXICAL_SURFACE_EXCEPTIONS = frozenset({"서로"})
_MAX_PENDING_QUESTION_TERMS = 32


def _required_text(value: Any, field: str, *, max_length: int = 128) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ValueError(f"{field} must not be empty")
    if len(normalized) > max_length:
        raise ValueError(f"{field} must be at most {max_length} characters")
    return normalized


def parse_pending_question_action_contract(
    metadata: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Normalize one question action or raise before a question is displayed."""

    raw = dict(metadata or {})
    curiosity_log_id = raw.get("curiosity_log_id")
    policy_action_id = raw.get("policy_action_id")
    if curiosity_log_id is None and policy_action_id is None:
        raise ValueError("curiosity_log_id or policy_action_id is required")

    normalized_curiosity_id = None
    if curiosity_log_id is not None:
        normalized_curiosity_id = _required_text(
            curiosity_log_id,
            "curiosity_log_id",
        )

    normalized_policy_id = None
    if policy_action_id is not None:
        normalized_policy_id = _required_text(
            policy_action_id,
            "policy_action_id",
        ).casefold()
        if not _POLICY_ACTION_ID_PATTERN.fullmatch(normalized_policy_id):
            raise ValueError(
                "policy_action_id must be 3-128 lowercase letters, digits, '.', '_', or '-'"
            )

    split = str(raw.get("question_outcome_split") or "").strip().casefold()
    if split not in PENDING_QUESTION_OUTCOME_SPLITS:
        raise ValueError("question_outcome_split must be 'train' or 'heldout'")

    contract_sha256 = str(
        raw.get("question_outcome_contract_sha256") or ""
    ).strip().casefold()
    if not _SHA256_PATTERN.fullmatch(contract_sha256):
        raise ValueError(
            "question_outcome_contract_sha256 must be 64 lowercase hex chars"
        )

    action_key = (
        f"policy:{normalized_policy_id}"
        if normalized_policy_id
        else f"curiosity:{normalized_curiosity_id}"
    )
    return {
        "curiosity_log_id": normalized_curiosity_id,
        "policy_action_id": normalized_policy_id,
        "policy_action_key": action_key,
        "split": split,
        "contract_sha256": contract_sha256,
    }


def validate_pending_question_action_state(
    contract: Mapping[str, Any],
    existing_actions: Iterable[Mapping[str, Any]],
    *,
    conflicting_split_count: int = 0,
    curiosity_log_exists: bool = True,
) -> dict[str, Any]:
    """Reject reused actions, cross-split manifests, and missing provenance."""

    if contract.get("curiosity_log_id") and not curiosity_log_exists:
        return {"status": "rejected", "reason": "curiosity_log_not_found"}
    if int(conflicting_split_count or 0) > 0:
        return {"status": "rejected", "reason": "contract_reused_across_splits"}
    if any(True for _ in existing_actions):
        return {"status": "rejected", "reason": "duplicate_policy_action"}
    return {"status": "valid", "reason": None}


def _unique_ids(items: Iterable[Mapping[str, Any]]) -> list[str]:
    return list(dict.fromkeys(
        str(item.get("id") or "").strip()
        for item in items
        if str(item.get("id") or "").strip()
    ))


def _prediction_candidates(items: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in items:
        candidate_id = str(item.get("id") or "").strip()
        if not candidate_id or candidate_id in seen:
            continue
        raw_score = item.get("score", 0.0)
        try:
            score = float(raw_score or 0.0)
        except (TypeError, ValueError) as exc:
            raise ValueError("prediction score must be numeric") from exc
        if not math.isfinite(score):
            raise ValueError("prediction score must be finite")
        seen.add(candidate_id)
        candidates.append({
            "id": candidate_id,
            "name": str(item.get("name") or "").strip(),
            "score": score,
            "rank": len(candidates) + 1,
        })
    return candidates


def normalize_pending_question_prediction(
    snapshot: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Require a timestamped, non-empty graph prediction before publication."""

    raw = dict(snapshot or {})
    cue_ids = _unique_ids(raw.get("cue_concepts") or [])
    predicted_candidates = _prediction_candidates(raw.get("predicted_concepts") or [])
    predicted_ids = [item["id"] for item in predicted_candidates]
    if not cue_ids:
        raise ValueError("pending question prediction requires known cue concepts")
    if not predicted_ids:
        raise ValueError("pending question prediction requires predicted concept ids")

    captured_at = str(raw.get("captured_at") or "").strip()
    try:
        parsed_at = datetime.fromisoformat(captured_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("prediction_captured_at must be ISO-8601") from exc
    if parsed_at.tzinfo is None:
        raise ValueError("prediction_captured_at must include a timezone")

    input_terms = list(dict.fromkeys(
        str(term).strip().casefold()
        for term in (raw.get("input_terms") or [])
        if str(term).strip()
    ))
    return {
        "cue_ids": cue_ids,
        "predicted_ids": predicted_ids,
        "predicted_candidates": predicted_candidates,
        "input_terms": input_terms,
        "captured_at": parsed_at.astimezone(timezone.utc).isoformat(),
    }


def prediction_precedes_question(
    prediction_captured_at: str,
    asked_at: str,
) -> bool:
    """Return whether the stored prediction was captured before publication."""

    captured = datetime.fromisoformat(str(prediction_captured_at).replace("Z", "+00:00"))
    asked = datetime.fromisoformat(str(asked_at).replace("Z", "+00:00"))
    if captured.tzinfo is None or asked.tzinfo is None:
        return False
    return captured.astimezone(timezone.utc) <= asked.astimezone(timezone.utc)


def validate_pending_question_answer_state(
    question: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Classify a stored question before accepting an external answer."""

    if question is None:
        return {"status": "not_found", "reason": "pending_question_not_found"}
    props = dict(question)
    if props.get("question_outcome_evaluation") is not True:
        return {"status": "legacy", "reason": None}
    if props.get("answer") is not None or props.get("status") == "answered":
        return {"status": "rejected", "reason": "question_already_answered"}
    if props.get("status") != "pending":
        return {"status": "rejected", "reason": "question_not_pending"}

    required = (
        "question_outcome_policy_action_key",
        "question_outcome_split",
        "question_outcome_contract_sha256",
        "prediction_captured_at",
    )
    if any(not props.get(field) for field in required):
        return {"status": "rejected", "reason": "incomplete_question_contract"}
    predicted_ids = [item for item in props.get("predicted_concept_ids", []) if item]
    cue_ids = [item for item in props.get("curiosity_cue_ids", []) if item]
    if not predicted_ids or not cue_ids:
        return {"status": "rejected", "reason": "incomplete_prediction_snapshot"}
    try:
        captured_at = datetime.fromisoformat(
            str(props["prediction_captured_at"]).replace("Z", "+00:00")
        )
    except ValueError:
        return {"status": "rejected", "reason": "invalid_prediction_timestamp"}
    if captured_at.tzinfo is None:
        return {"status": "rejected", "reason": "invalid_prediction_timestamp"}
    return {
        "status": "ready",
        "reason": None,
        "prediction_captured_at": captured_at.astimezone(timezone.utc).isoformat(),
        "cue_ids": cue_ids,
        "predicted_ids": predicted_ids,
    }


def _derived_korean_term(token: str) -> str | None:
    for ending in _OUTCOME_PREDICATE_ENDINGS:
        if token.endswith(ending) and len(token) > len(ending):
            stem = token[: -len(ending)]
            if stem not in _NON_CONTENT_PREDICATE_STEMS and len(stem) >= 2:
                return stem
            return None
    for particle in _OUTCOME_PARTICLES:
        if token.endswith(particle) and len(token) > len(particle):
            stem = token[: -len(particle)]
            if stem not in _NON_CONTENT_PREDICATE_STEMS and len(stem) >= 2:
                return stem
            return None
    return token if len(token) >= 2 else None


def _looks_inflected(token: str) -> bool:
    if token in _LEXICAL_SURFACE_EXCEPTIONS:
        return False
    return any(
        token.endswith(suffix) and len(token) > len(suffix)
        for suffix in (*_OUTCOME_PREDICATE_ENDINGS, *_OUTCOME_PARTICLES)
    )


def _numeric_unit_facts(text: str) -> list[str]:
    facts: list[str] = []
    raw = text or ""
    for match in _NUMERIC_UNIT_PATTERN.finditer(raw):
        number, unit = match.groups()
        suffix = raw[match.end():]
        if unit == "분" and re.match(r"의\s*\d", suffix):
            continue
        facts.append(f"{number.replace(',', '')}{unit}".casefold())
    return facts


def _pending_question_term_candidates(text: str) -> list[str]:
    raw = text or ""
    numeric_facts = _numeric_unit_facts(raw)
    without_numeric_surfaces = _NUMERIC_UNIT_SURFACE_PATTERN.sub(" ", raw)
    korean_tokens = [
        match.group(0).casefold()
        for match in _KOREAN_TERM_PATTERN.finditer(without_numeric_surfaces)
    ]
    derived_terms = [
        term for token in korean_tokens
        if (term := _derived_korean_term(token)) is not None
    ]
    ascii_terms = [
        match.group(0).casefold()
        for match in _ASCII_TERM_PATTERN.finditer(without_numeric_surfaces)
    ]
    surface_terms = [
        token for token in korean_tokens
        if len(token) >= 2 and not _looks_inflected(token)
    ]
    return filter_curiosity_cue_terms(dict.fromkeys(
        [*numeric_facts, *derived_terms, *ascii_terms, *surface_terms]
    ))


def build_pending_question_terms(text: str) -> list[str]:
    """Build bounded outcome candidates without importing the protected handler.

    Numeric facts are kept as compounds and candidates are collected across the
    whole answer before the 32-term bound is applied.  This avoids the previous
    first-12-token bias while retaining exact-name lookup compatibility.
    """

    return _pending_question_term_candidates(text)[:_MAX_PENDING_QUESTION_TERMS]


def build_pending_question_cue_terms(text: str) -> list[str]:
    """Preserve the established B-2 question-cue normalization contract."""

    surface_terms = _QUESTION_SURFACE_TERM_PATTERN.findall(text or "")
    return filter_curiosity_cue_terms(
        build_curiosity_cue_terms(text, extracted_terms=surface_terms)
    )


def audit_pending_question_terms(
    text: str,
    terms: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Report parser coverage; this is not a semantic truth judgment."""

    normalized_terms = list(dict.fromkeys(
        str(term).strip().casefold()
        for term in (terms if terms is not None else build_pending_question_terms(text))
        if str(term).strip()
    ))
    expected_numeric = list(dict.fromkeys(_numeric_unit_facts(text)))
    covered_numeric = [term for term in expected_numeric if term in normalized_terms]
    one_character_korean = [
        term for term in normalized_terms
        if len(term) == 1 and _KOREAN_TERM_PATTERN.fullmatch(term)
    ]
    predicate_fragments = sorted(
        set(normalized_terms) & _NON_CONTENT_PREDICATE_STEMS
    )
    numeric_coverage = (
        len(covered_numeric) / len(expected_numeric) if expected_numeric else 1.0
    )
    candidates = _pending_question_term_candidates(text)
    measurement_gate = bool(
        normalized_terms
        and numeric_coverage == 1.0
        and not one_character_korean
        and not predicate_fragments
    )
    return {
        "measurement_content_gate": measurement_gate,
        "scope": "parser_coverage_only_not_semantic_truth",
        "term_count": len(normalized_terms),
        "candidate_count_before_limit": len(candidates),
        "term_limit": _MAX_PENDING_QUESTION_TERMS,
        "candidate_truncated": len(candidates) > _MAX_PENDING_QUESTION_TERMS,
        "numeric_facts": expected_numeric,
        "covered_numeric_facts": covered_numeric,
        "numeric_fact_coverage": round(numeric_coverage, 6),
        "one_character_korean_terms": one_character_korean,
        "predicate_fragments": predicate_fragments,
    }
