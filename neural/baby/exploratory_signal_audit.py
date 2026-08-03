"""Pure contracts for answer-first exploratory signal auditing.

The answer specification is fixed without reading predictor output.  Only a
sealed successor may then consume the exploratory top-k capture.  The audit is
descriptive, exact-name-only, and permanently ineligible for confirmation.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
import json
import unicodedata
from itertools import combinations
from typing import Any, Iterable, Mapping

from neural.baby.answer_source import route_answer_source
from neural.baby.candidate_universe import (
    DEFAULT_TOP_K,
    classify_candidate_vocabulary,
    exclude_question_cue_surfaces,
)
from neural.baby.exploratory_question_probe import (
    EXPLORATORY_EVIDENCE_SCOPE,
    EXPLORATORY_PHASE,
    validate_exploratory_pre_answer_capture,
    validate_exploratory_question_manifest,
)
from neural.baby.pending_question_semantics import canonical_json_sha256


ANSWER_SPEC_VERSION = 1
ANSWER_PACK_VERSION = 1
AUDIT_VERSION = 1
ANSWER_SPEC_STATUS = "external_teacher_answers_fixed_before_prediction_review"
ANSWER_PACK_STATUS = (
    "exploratory_external_teacher_answers_sealed_before_prediction_review"
)
AUDIT_STATUS = "exploratory_exact_target_signal_audit_completed_not_for_claim"
TEACHER_IDENTITY_SCOPE = "conversation_assistant_not_model_snapshot"

_FALSE_GATES = (
    "database_writes",
    "learning_enabled",
    "probabilities_computed",
    "calibrator_fit_allowed",
    "heldout_gate",
    "performance_claim_gate",
    "production_promotion_gate",
    "confirmatory_reuse_allowed",
)


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


def _normalize_name(value: Any) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).strip().casefold()
    return " ".join(text.split())


def validate_exploratory_answer_spec(
    payload: Mapping[str, Any],
    manifest: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate and fingerprint answers that were fixed before prediction review."""

    normalized_manifest = validate_exploratory_question_manifest(manifest)
    normalized = _clone(payload)
    expected_top_fields = {
        "answer_source",
        "exploratory_answer_spec_version",
        "exploratory_only_not_ground_truth",
        "generated_before_prediction_reveal",
        "phase",
        "prepared_at",
        "question_type",
        "questions",
        "status",
        "teacher_identity_scope",
        "user_review_required",
    }
    if set(normalized) != expected_top_fields:
        raise ValueError("exploratory answer spec fields mismatch")
    if normalized.get("exploratory_answer_spec_version") != ANSWER_SPEC_VERSION:
        raise ValueError("unsupported exploratory answer spec version")
    if normalized.get("phase") != EXPLORATORY_PHASE:
        raise ValueError("exploratory answer spec phase mismatch")
    if normalized.get("status") != ANSWER_SPEC_STATUS:
        raise ValueError("exploratory answer spec status mismatch")
    _require_zoned(normalized.get("prepared_at"), "prepared_at")
    if normalized.get("generated_before_prediction_reveal") is not True:
        raise ValueError("answers must be fixed before prediction review")
    if normalized.get("exploratory_only_not_ground_truth") is not True:
        raise ValueError("exploratory answers cannot be ground truth")
    if normalized.get("user_review_required") is not False:
        raise ValueError("public-knowledge teacher answers do not require user review")
    if normalized.get("teacher_identity_scope") != TEACHER_IDENTITY_SCOPE:
        raise ValueError("exploratory teacher identity scope mismatch")
    routed = route_answer_source(str(normalized.get("question_type") or ""))
    if routed != "external_teacher" or normalized.get("answer_source") != routed:
        raise ValueError("public-knowledge answers must use external_teacher")

    questions = list(normalized.get("questions") or [])
    expected_questions = list(normalized_manifest["questions"])
    if len(questions) != len(expected_questions):
        raise ValueError("exploratory answer spec must cover every question")
    cleaned_questions: list[dict[str, Any]] = []
    for answer_item, question in zip(questions, expected_questions):
        if set(answer_item) != {
            "answer",
            "order",
            "question_id",
            "target_concepts",
        }:
            raise ValueError("exploratory answer item fields mismatch")
        if answer_item.get("order") != question["order"]:
            raise ValueError("exploratory answer order mismatch")
        if answer_item.get("question_id") != question["question_id"]:
            raise ValueError("exploratory answer question_id mismatch")
        answer = str(answer_item.get("answer") or "").strip()
        if not answer:
            raise ValueError("exploratory teacher answer cannot be empty")
        targets = [
            str(item).strip() for item in answer_item.get("target_concepts") or []
        ]
        normalized_targets = [_normalize_name(item) for item in targets]
        if not 2 <= len(targets) <= 6 or any(not item for item in targets):
            raise ValueError("each answer requires two to six target concepts")
        if len(normalized_targets) != len(set(normalized_targets)):
            raise ValueError("answer target concepts must be unique")
        cue_names = {_normalize_name(item) for item in question["cue_terms"]}
        if cue_names & set(normalized_targets):
            raise ValueError("answer targets must exclude question cue terms")
        cleaned_questions.append({
            "order": question["order"],
            "question_id": question["question_id"],
            "answer": answer,
            "target_concepts": targets,
        })

    normalized["questions"] = cleaned_questions
    normalized["exploratory_answer_spec_sha256"] = canonical_json_sha256(normalized)
    return normalized


def seal_exploratory_answer_pack(
    answer_spec: Mapping[str, Any],
    manifest: Mapping[str, Any],
    capture: Mapping[str, Any],
    *,
    sealed_at: str,
) -> dict[str, Any]:
    """Bind the pre-fixed answers to the already captured question batch."""

    normalized_manifest = validate_exploratory_question_manifest(manifest)
    normalized_capture = validate_exploratory_pre_answer_capture(
        capture, normalized_manifest
    )
    normalized_spec = validate_exploratory_answer_spec(
        answer_spec, normalized_manifest
    )
    questions = []
    for answer_item, question in zip(
        normalized_spec["questions"], normalized_manifest["questions"]
    ):
        questions.append({
            "order": question["order"],
            "question_id": question["question_id"],
            "question": question["question"],
            "question_sha256": question["question_sha256"],
            "cue_terms": list(question["cue_terms"]),
            "answer": answer_item["answer"],
            "target_concepts": list(answer_item["target_concepts"]),
        })

    result = {
        "exploratory_answer_pack_version": ANSWER_PACK_VERSION,
        "phase": EXPLORATORY_PHASE,
        "status": ANSWER_PACK_STATUS,
        "evidence_scope": EXPLORATORY_EVIDENCE_SCOPE,
        "prepared_at": normalized_spec["prepared_at"],
        "sealed_at": _require_zoned(sealed_at, "sealed_at"),
        "manifest_id": normalized_manifest["manifest_id"],
        "manifest_snapshot_sha256": normalized_manifest[
            "manifest_snapshot_sha256"
        ],
        "exploratory_pre_answer_capture_sha256": normalized_capture[
            "exploratory_pre_answer_capture_sha256"
        ],
        "exploratory_answer_spec_sha256": normalized_spec[
            "exploratory_answer_spec_sha256"
        ],
        "question_type": "public_knowledge",
        "answer_source": "external_teacher",
        "teacher_identity_scope": TEACHER_IDENTITY_SCOPE,
        "generated_before_prediction_reveal": True,
        "prediction_fields_consumed_for_answer_generation": False,
        "exploratory_only_not_ground_truth": True,
        "answer_pack_mutation_after_prediction_reveal_allowed": False,
        "user_review_required": False,
        "question_count": len(questions),
        "questions": questions,
        "superseded_capture_next_step": normalized_capture["next_step"],
        "next_step": "run_lightweight_exploratory_signal_audit",
        "database_writes": False,
        "learning_enabled": False,
        "probabilities_computed": False,
        "calibrator_fit_allowed": False,
        "heldout_gate": False,
        "performance_claim_gate": False,
        "production_promotion_gate": False,
        "confirmatory_reuse_allowed": False,
    }
    result["exploratory_answer_pack_sha256"] = canonical_json_sha256(result)
    return validate_exploratory_answer_pack(
        result, normalized_manifest, normalized_capture
    )


def validate_exploratory_answer_pack(
    payload: Mapping[str, Any],
    manifest: Mapping[str, Any],
    capture: Mapping[str, Any],
) -> dict[str, Any]:
    normalized_manifest = validate_exploratory_question_manifest(manifest)
    normalized_capture = validate_exploratory_pre_answer_capture(
        capture, normalized_manifest
    )
    normalized = _clone(payload)
    if normalized.get("exploratory_answer_pack_version") != ANSWER_PACK_VERSION:
        raise ValueError("unsupported exploratory answer pack version")
    if normalized.get("phase") != EXPLORATORY_PHASE:
        raise ValueError("exploratory answer pack phase mismatch")
    if normalized.get("status") != ANSWER_PACK_STATUS:
        raise ValueError("exploratory answer pack status mismatch")
    if normalized.get("evidence_scope") != EXPLORATORY_EVIDENCE_SCOPE:
        raise ValueError("exploratory answer pack evidence scope mismatch")
    _require_zoned(normalized.get("prepared_at"), "prepared_at")
    _require_zoned(normalized.get("sealed_at"), "sealed_at")
    if normalized.get("manifest_id") != normalized_manifest["manifest_id"]:
        raise ValueError("exploratory answer pack manifest_id mismatch")
    if normalized.get("manifest_snapshot_sha256") != normalized_manifest[
        "manifest_snapshot_sha256"
    ]:
        raise ValueError("exploratory answer pack manifest binding mismatch")
    if normalized.get("exploratory_pre_answer_capture_sha256") != (
        normalized_capture["exploratory_pre_answer_capture_sha256"]
    ):
        raise ValueError("exploratory answer pack capture binding mismatch")
    _require_sha256(
        normalized.get("exploratory_answer_spec_sha256"),
        "exploratory_answer_spec_sha256",
    )
    if normalized.get("question_type") != "public_knowledge":
        raise ValueError("exploratory answer pack question type mismatch")
    if normalized.get("answer_source") != "external_teacher":
        raise ValueError("exploratory answer pack source mismatch")
    if normalized.get("teacher_identity_scope") != TEACHER_IDENTITY_SCOPE:
        raise ValueError("exploratory answer pack teacher scope mismatch")
    truthy_fields = (
        "generated_before_prediction_reveal",
        "exploratory_only_not_ground_truth",
    )
    if any(normalized.get(field) is not True for field in truthy_fields):
        raise ValueError("exploratory answer pack truth fields mismatch")
    false_fields = (
        "prediction_fields_consumed_for_answer_generation",
        "answer_pack_mutation_after_prediction_reveal_allowed",
        "user_review_required",
        *_FALSE_GATES,
    )
    if any(normalized.get(field) is not False for field in false_fields):
        raise ValueError("exploratory answer pack false fields mismatch")
    if normalized.get("superseded_capture_next_step") != normalized_capture[
        "next_step"
    ]:
        raise ValueError("exploratory answer pack next-step amendment mismatch")
    if normalized.get("next_step") != "run_lightweight_exploratory_signal_audit":
        raise ValueError("exploratory answer pack next step mismatch")

    questions = list(normalized.get("questions") or [])
    expected_questions = list(normalized_manifest["questions"])
    if normalized.get("question_count") != len(questions):
        raise ValueError("exploratory answer pack question_count mismatch")
    if len(questions) != len(expected_questions):
        raise ValueError("exploratory answer pack coverage mismatch")
    for item, expected in zip(questions, expected_questions):
        for field in ("order", "question_id", "question", "question_sha256"):
            if item.get(field) != expected[field]:
                raise ValueError(f"exploratory answer pack {field} mismatch")
        if item.get("cue_terms") != expected["cue_terms"]:
            raise ValueError("exploratory answer pack cue mismatch")
        if not str(item.get("answer") or "").strip():
            raise ValueError("exploratory answer pack answer cannot be empty")
        targets = [str(value).strip() for value in item.get("target_concepts") or []]
        if not 2 <= len(targets) <= 6:
            raise ValueError("exploratory answer pack target count mismatch")
        if len({_normalize_name(value) for value in targets}) != len(targets):
            raise ValueError("exploratory answer pack targets must be unique")
        if {_normalize_name(value) for value in item["cue_terms"]} & {
            _normalize_name(value) for value in targets
        }:
            raise ValueError("exploratory answer pack targets include a cue")

    supplied = _require_sha256(
        normalized.get("exploratory_answer_pack_sha256"),
        "exploratory_answer_pack_sha256",
    )
    unhashed = _clone(normalized)
    unhashed.pop("exploratory_answer_pack_sha256", None)
    if supplied != canonical_json_sha256(unhashed):
        raise ValueError("exploratory answer pack sha256 mismatch")
    return normalized


def _target_availability(
    targets: Iterable[str],
    eligible_concepts: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    by_name: dict[str, list[dict[str, str]]] = defaultdict(list)
    for concept in eligible_concepts:
        concept_id = str(concept["concept_id"])
        concept_name = str(concept["concept_name"])
        by_name[_normalize_name(concept_name)].append({
            "concept_id": concept_id,
            "concept_name": concept_name,
        })
    return [
        {
            "target_concept": target,
            "eligible_candidate_matches": sorted(
                by_name.get(_normalize_name(target), []),
                key=lambda item: (item["concept_id"], item["concept_name"]),
            ),
            "available_in_captured_vocabulary": bool(
                by_name.get(_normalize_name(target))
            ),
        }
        for target in targets
    ]


def _predictor_question_result(
    targets: Iterable[str],
    top_rows: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    compact_rows = [
        {
            "concept_id": str(item["concept_id"]),
            "concept_name": str(item["concept_name"]),
            "rank": int(item["rank"]),
        }
        for item in top_rows
    ]
    by_name: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in compact_rows:
        by_name[_normalize_name(item["concept_name"])].append(item)
    hits = [
        {
            "target_concept": target,
            "top_k_matches": by_name[_normalize_name(target)],
        }
        for target in targets
        if by_name.get(_normalize_name(target))
    ]
    return {
        "top_k": compact_rows,
        "exact_target_hits": hits,
        "exact_target_hit_count": len(hits),
    }


def _predictor_summary(
    question_results: Iterable[Mapping[str, Any]],
    predictor_key: str,
) -> dict[str, Any]:
    results = list(question_results)
    appearances: dict[str, dict[str, Any]] = {}
    top_sets: list[set[str]] = []
    hit_count = 0
    questions_with_hit = 0
    for result in results:
        predictor = dict(result[predictor_key])
        hit_count += int(predictor["exact_target_hit_count"])
        questions_with_hit += int(predictor["exact_target_hit_count"] > 0)
        names = set()
        for row in predictor["top_k"]:
            normalized_name = _normalize_name(row["concept_name"])
            names.add(normalized_name)
            entry = appearances.setdefault(normalized_name, {
                "concept_name": row["concept_name"],
                "question_ids": [],
            })
            entry["question_ids"].append(result["question_id"])
        top_sets.append(names)
    pairwise = [
        len(left & right) / len(left | right) if left | right else 0.0
        for left, right in combinations(top_sets, 2)
    ]
    repeated = [
        {
            "concept_name": item["concept_name"],
            "question_count": len(set(item["question_ids"])),
            "question_ids": sorted(set(item["question_ids"])),
        }
        for item in appearances.values()
        if len(set(item["question_ids"])) >= 2
    ]
    repeated.sort(key=lambda item: (-item["question_count"], item["concept_name"]))
    return {
        "top_k_slots": len(results) * DEFAULT_TOP_K,
        "unique_top_k_concept_count": len(appearances),
        "repeated_concepts": repeated,
        "mean_pairwise_top_k_jaccard": (
            sum(pairwise) / len(pairwise) if pairwise else 0.0
        ),
        "exact_target_hit_count": hit_count,
        "questions_with_exact_target_hit": questions_with_hit,
    }


def build_exploratory_signal_audit(
    answer_pack: Mapping[str, Any],
    manifest: Mapping[str, Any],
    capture: Mapping[str, Any],
    source_concepts: Iterable[Mapping[str, Any]],
    *,
    audited_at: str,
) -> dict[str, Any]:
    """Build an exact-name descriptive audit without fitting or relabeling."""

    normalized_manifest = validate_exploratory_question_manifest(manifest)
    normalized_capture = validate_exploratory_pre_answer_capture(
        capture, normalized_manifest
    )
    normalized_answers = validate_exploratory_answer_pack(
        answer_pack, normalized_manifest, normalized_capture
    )
    concepts = sorted(
        [
            {"id": str(item.get("id") or ""), "name": str(item.get("name") or "")}
            for item in source_concepts
        ],
        key=lambda item: (item["id"], item["name"]),
    )
    graph_snapshot_sha256 = canonical_json_sha256({"concepts": concepts})
    if graph_snapshot_sha256 != normalized_capture["graph_snapshot_sha256"]:
        raise ValueError("current graph snapshot does not match exploratory capture")
    eligible, _ = classify_candidate_vocabulary(concepts)

    question_results = []
    total_targets = 0
    available_targets = 0
    for answer_item, captured_item in zip(
        normalized_answers["questions"], normalized_capture["questions"]
    ):
        scoped_eligible, _ = exclude_question_cue_surfaces(
            eligible, captured_item["cue_terms"]
        )
        target_availability = _target_availability(
            answer_item["target_concepts"], scoped_eligible
        )
        total_targets += len(target_availability)
        available_targets += sum(
            int(item["available_in_captured_vocabulary"])
            for item in target_availability
        )
        question_results.append({
            "order": captured_item["order"],
            "question_id": captured_item["question_id"],
            "question": captured_item["question"],
            "question_sha256": captured_item["question_sha256"],
            "target_concepts": list(answer_item["target_concepts"]),
            "target_availability": target_availability,
            "graph": _predictor_question_result(
                answer_item["target_concepts"], captured_item["graph_top_k"]
            ),
            "local_core": _predictor_question_result(
                answer_item["target_concepts"], captured_item["local_core_top_k"]
            ),
            "cross_predictor_top_k_overlap_count": captured_item[
                "top_k_overlap_count"
            ],
        })

    graph_summary = _predictor_summary(question_results, "graph")
    local_summary = _predictor_summary(question_results, "local_core")
    graph_hits = graph_summary["exact_target_hit_count"]
    local_hits = local_summary["exact_target_hit_count"]
    if graph_hits == 0 and local_hits == 0:
        signal_status = "no_predeclared_exact_target_hits"
    elif graph_hits > 0 and local_hits == 0:
        signal_status = "graph_only_predeclared_exact_target_hits"
    elif graph_hits == 0 and local_hits > 0:
        signal_status = "local_core_only_predeclared_exact_target_hits"
    else:
        signal_status = "both_predictors_have_predeclared_exact_target_hits"

    result = {
        "exploratory_signal_audit_version": AUDIT_VERSION,
        "phase": EXPLORATORY_PHASE,
        "status": AUDIT_STATUS,
        "evidence_scope": EXPLORATORY_EVIDENCE_SCOPE,
        "audited_at": _require_zoned(audited_at, "audited_at"),
        "manifest_snapshot_sha256": normalized_manifest[
            "manifest_snapshot_sha256"
        ],
        "exploratory_pre_answer_capture_sha256": normalized_capture[
            "exploratory_pre_answer_capture_sha256"
        ],
        "exploratory_answer_pack_sha256": normalized_answers[
            "exploratory_answer_pack_sha256"
        ],
        "graph_snapshot_sha256": graph_snapshot_sha256,
        "generated_answers_before_prediction_review": True,
        "semantic_equivalence_review_performed": False,
        "post_hoc_target_additions": 0,
        "exact_name_matching_only": True,
        "exploratory_only_not_for_claim": True,
        "question_count": len(question_results),
        "declared_target_count": total_targets,
        "available_target_count": available_targets,
        "missing_target_count": total_targets - available_targets,
        "questions": question_results,
        "graph_summary": graph_summary,
        "local_core_summary": local_summary,
        "signal_status": signal_status,
        "exploratory_signal_audit_gate": True,
        "graph_snapshot_match_gate": True,
        "database_writes": False,
        "learning_enabled": False,
        "probabilities_computed": False,
        "calibrator_fit_allowed": False,
        "heldout_gate": False,
        "performance_claim_gate": False,
        "production_promotion_gate": False,
        "confirmatory_reuse_allowed": False,
        "block_reasons": [
            "exploratory_questions_were_public_before_capture",
            "exact_name_matches_are_descriptive_not_semantic_ground_truth",
            "no_predeclared_inferential_threshold",
        ],
        "next_step": (
            "review_missing_or_semantically_ambiguous_targets_without_mutating_"
            "this_audit_then_prioritize_data_and_wake_behavior_work"
        ),
    }
    result["exploratory_signal_audit_sha256"] = canonical_json_sha256(result)
    return validate_exploratory_signal_audit(
        result, normalized_answers, normalized_manifest, normalized_capture
    )


def validate_exploratory_signal_audit(
    payload: Mapping[str, Any],
    answer_pack: Mapping[str, Any],
    manifest: Mapping[str, Any],
    capture: Mapping[str, Any],
) -> dict[str, Any]:
    normalized_manifest = validate_exploratory_question_manifest(manifest)
    normalized_capture = validate_exploratory_pre_answer_capture(
        capture, normalized_manifest
    )
    normalized_answers = validate_exploratory_answer_pack(
        answer_pack, normalized_manifest, normalized_capture
    )
    normalized = _clone(payload)
    if normalized.get("exploratory_signal_audit_version") != AUDIT_VERSION:
        raise ValueError("unsupported exploratory signal audit version")
    if normalized.get("phase") != EXPLORATORY_PHASE:
        raise ValueError("exploratory signal audit phase mismatch")
    if normalized.get("status") != AUDIT_STATUS:
        raise ValueError("exploratory signal audit status mismatch")
    if normalized.get("evidence_scope") != EXPLORATORY_EVIDENCE_SCOPE:
        raise ValueError("exploratory signal audit evidence scope mismatch")
    _require_zoned(normalized.get("audited_at"), "audited_at")
    bindings = {
        "manifest_snapshot_sha256": normalized_manifest[
            "manifest_snapshot_sha256"
        ],
        "exploratory_pre_answer_capture_sha256": normalized_capture[
            "exploratory_pre_answer_capture_sha256"
        ],
        "exploratory_answer_pack_sha256": normalized_answers[
            "exploratory_answer_pack_sha256"
        ],
        "graph_snapshot_sha256": normalized_capture["graph_snapshot_sha256"],
    }
    for field, expected in bindings.items():
        if normalized.get(field) != expected:
            raise ValueError(f"exploratory signal audit {field} mismatch")
    truthy_fields = (
        "generated_answers_before_prediction_review",
        "exact_name_matching_only",
        "exploratory_only_not_for_claim",
        "exploratory_signal_audit_gate",
        "graph_snapshot_match_gate",
    )
    if any(normalized.get(field) is not True for field in truthy_fields):
        raise ValueError("exploratory signal audit truth fields mismatch")
    if normalized.get("semantic_equivalence_review_performed") is not False:
        raise ValueError("initial exploratory audit cannot use semantic relabeling")
    if normalized.get("post_hoc_target_additions") != 0:
        raise ValueError("initial exploratory audit forbids post-hoc targets")
    if any(normalized.get(field) is not False for field in _FALSE_GATES):
        raise ValueError("exploratory signal audit false gates mismatch")

    questions = list(normalized.get("questions") or [])
    if normalized.get("question_count") != len(questions):
        raise ValueError("exploratory signal audit question_count mismatch")
    if len(questions) != len(normalized_answers["questions"]):
        raise ValueError("exploratory signal audit coverage mismatch")
    for result, answer_item in zip(questions, normalized_answers["questions"]):
        for field in ("order", "question_id", "question", "question_sha256"):
            if result.get(field) != answer_item[field]:
                raise ValueError(f"exploratory signal audit {field} mismatch")
        if result.get("target_concepts") != answer_item["target_concepts"]:
            raise ValueError("exploratory signal audit targets mismatch")
        for predictor in ("graph", "local_core"):
            rows = list(result.get(predictor, {}).get("top_k") or [])
            if len(rows) != DEFAULT_TOP_K:
                raise ValueError("exploratory signal audit top-k count mismatch")

    supplied = _require_sha256(
        normalized.get("exploratory_signal_audit_sha256"),
        "exploratory_signal_audit_sha256",
    )
    unhashed = _clone(normalized)
    unhashed.pop("exploratory_signal_audit_sha256", None)
    if supplied != canonical_json_sha256(unhashed):
        raise ValueError("exploratory signal audit sha256 mismatch")
    return normalized
