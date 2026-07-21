"""Read-only capture path for genuinely fresh (never-labeled) J1 questions.

The J1.1B fresh-shadow chain proved the plumbing by *replaying* the sealed train
capture: its input pack carries
``source_scope = "sealed_train_capture_shadow_not_runtime_fresh"``.  That replay
can never satisfy the sealed input contract's freshness requirement
``features_must_be_captured_before_question_is_shown`` because those questions
were already shown, answered, and labeled.

This module supplies the missing pieces for a real fresh capture:

* a never-labeled guard that refuses any question already present in the train
  manifest or the reviewed label pack, cue terms included;
* a fresh candidate vocabulary that binds to the fresh manifest and the graph
  snapshot **without** requiring reviewed answer/label packs (requiring them
  would be self-contradictory for a question that has no answer yet);
* a real fresh input pack whose ``source_scope`` records that it was captured
  rather than replayed, while keeping ``input_pack_scope`` bound to the sealed
  contract so the existing probability and selection validators still apply.

Nothing here writes the database, runs a model, computes a probability, or
promotes anything.  Scoring itself is performed by the caller and passed in.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime
import json
from typing import Any, Iterable, Mapping

from neural.baby.candidate_universe import DEFAULT_TOP_K
from neural.baby.fresh_snapshot_contract import (
    seal_fresh_pre_question_snapshot_input_pack,
    validate_fresh_pre_question_snapshot_input_contract,
    validate_fresh_pre_question_snapshot_input_pack,
)
from neural.baby.pending_question_semantics import canonical_json_sha256
from neural.baby.question_calibration import (
    QUESTION_CALIBRATION_MANIFEST_VERSION,
    PHASE as QUESTION_CALIBRATION_PHASE,
    # Imported rather than reimplemented on purpose: the fresh manifest must hash
    # question text with exactly the same function the train manifest used, so
    # that a hash collision with a train question is detectable.
    _question_sha256 as question_text_sha256,
)


FRESH_MANIFEST_SPLIT = "fresh_selection"
FRESH_MANIFEST_PURPOSE = "never_labeled_question_selection_only"
REQUIRED_USER_APPROVAL_SCOPE = frozenset({
    "local_core_gpu_read_only_inference",
    "new_question_answer_collection",
})
REQUIRED_FALSE_MANIFEST_CONSTRAINTS = (
    "database_writes",
    "learning_enabled",
    "heldout_collection",
    "production_promotion",
    "questions_revealed_before_raw_capture",
    "calibrator_fit_before_reviewed_answers",
)

FRESH_CANDIDATE_VOCABULARY_VERSION = 1
FRESH_PHASE = "J1.1B"
FRESH_VOCABULARY_STATUS = "fresh_preflight_only_no_answers_no_labels"
FRESH_VOCABULARY_SCOPE = "fresh_never_labeled_question_vocabulary"
REAL_FRESH_SOURCE_SCOPE = "real_fresh_pre_question_capture_not_replay"
REAL_FRESH_PACK_STATUS = "real_fresh_pre_question_input_pack_ready_not_runtime"

FRESH_SELECTION_CONTRACT = {
    "source_vocabulary": "neo4j_full_concept_snapshot",
    "validity_filter_precedes_predictor_scoring": True,
    "semantic_labels_used_for_filtering": False,
    "graph_scores_required_for_full_question_vocabulary": True,
    "local_core_scores_required_for_full_question_vocabulary": True,
    "top_k": DEFAULT_TOP_K,
    "union_rule": "graph_top_k_union_local_core_top_k",
    "both_predictors_rescore_union": True,
}

REQUIRED_FALSE_PREFLIGHT_FIELDS = (
    "database_writes",
    "learning_enabled",
    "gpu_inference_executed",
    "probabilities_computed",
    "calibrator_fit_allowed",
    "heldout_gate",
    "performance_claim_gate",
    "production_promotion_gate",
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


def _hex_sha256(value: Any, field: str) -> str:
    text = str(value or "")
    if len(text) != 64 or any(char not in "0123456789abcdef" for char in text):
        raise ValueError(f"{field} must be lowercase hex sha256")
    return text


def _question_records(manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    records = list(manifest.get("questions") or [])
    if not records:
        raise ValueError("manifest carries no questions")
    return records


def _validate_fresh_manifest_body(manifest: Mapping[str, Any]) -> dict[str, Any]:
    """Mirror the train manifest discipline with a fresh split and purpose.

    Deliberately a separate validator rather than a widening of
    ``question_calibration``: the train manifests already sealed against that
    module must keep meaning exactly what they meant when they were sealed.
    Everything else - the required user approval scope, the all-false
    constraints, the per-question hash binding - is enforced identically.
    """

    normalized = _clone(manifest)
    if normalized.get("question_calibration_manifest_version") != (
        QUESTION_CALIBRATION_MANIFEST_VERSION
    ):
        raise ValueError("unsupported question_calibration_manifest_version")
    if normalized.get("phase") != QUESTION_CALIBRATION_PHASE:
        raise ValueError("fresh manifest phase must be J1.1")
    if normalized.get("split") != FRESH_MANIFEST_SPLIT:
        raise ValueError("fresh manifest split must be fresh_selection")
    if normalized.get("purpose") != FRESH_MANIFEST_PURPOSE:
        raise ValueError(
            "fresh manifest purpose must be never_labeled_question_selection_only"
        )
    if not str(normalized.get("manifest_id") or "").strip():
        raise ValueError("manifest_id is required")
    _require_zoned(normalized.get("created_at"), "created_at")
    _require_zoned(normalized.get("approval_recorded_at"), "approval_recorded_at")

    approvals = set(normalized.get("user_approval_scope") or [])
    if not REQUIRED_USER_APPROVAL_SCOPE.issubset(approvals):
        raise ValueError(
            "fresh manifest is missing explicit user approval scope: "
            + ",".join(sorted(REQUIRED_USER_APPROVAL_SCOPE - approvals))
        )

    constraints = dict(normalized.get("constraints") or {})
    offending = [
        field
        for field in REQUIRED_FALSE_MANIFEST_CONSTRAINTS
        if constraints.get(field) is not False
    ]
    if offending:
        raise ValueError(
            "fresh manifest constraints must stay false: " + ",".join(sorted(offending))
        )

    questions = _question_records(normalized)
    if len(questions) < 2:
        raise ValueError("a fresh manifest requires at least two questions")
    if normalized.get("question_count") != len(questions):
        raise ValueError("question_count does not match questions")
    if [item.get("order") for item in questions] != list(range(len(questions))):
        raise ValueError("question orders must be contiguous and zero-based")

    seen_ids: set[str] = set()
    seen_text: set[str] = set()
    for item in questions:
        question_id = str(item.get("question_id") or "").strip()
        text = str(item.get("question") or "").strip()
        cue_terms = [str(term).strip() for term in item.get("cue_terms") or []]
        if not question_id or question_id in seen_ids:
            raise ValueError("question_id must be non-empty and unique")
        if not text or text in seen_text:
            raise ValueError("question text must be non-empty and unique")
        if not 1 <= len(cue_terms) <= 4 or any(not term for term in cue_terms):
            raise ValueError("each question requires one to four non-empty cue terms")
        if len(set(cue_terms)) != len(cue_terms):
            raise ValueError("cue terms must be unique within a question")
        if item.get("question_sha256") != question_text_sha256(text):
            raise ValueError("question_sha256 mismatch")
        seen_ids.add(question_id)
        seen_text.add(text)
    return normalized


def seal_fresh_question_manifest(draft: Mapping[str, Any]) -> dict[str, Any]:
    """Add exact question hashes and a canonical contract hash to a fresh draft.

    Sealing is the pre-registration act.  It fails closed unless the draft
    already carries the user approval scope, so a manifest cannot be
    pre-registered on the user's behalf.
    """

    normalized = _clone(draft)
    normalized.pop("contract_sha256", None)
    for item in normalized.get("questions") or []:
        text = str(item.get("question") or "").strip()
        item["question"] = text
        item["question_sha256"] = question_text_sha256(text)
    _validate_fresh_manifest_body(normalized)
    normalized["contract_sha256"] = canonical_json_sha256(normalized)
    return validate_fresh_preregistered_manifest(normalized)


def validate_fresh_preregistered_manifest(
    manifest: Mapping[str, Any],
) -> dict[str, Any]:
    normalized = _validate_fresh_manifest_body(manifest)
    unhashed = _clone(normalized)
    unhashed.pop("contract_sha256", None)
    expected = canonical_json_sha256(unhashed)
    actual = _hex_sha256(normalized.get("contract_sha256"), "contract_sha256")
    if actual != expected:
        raise ValueError("fresh manifest contract_sha256 mismatch")
    return normalized


def _collect_labeled_question_hashes(
    reviewed_label_pack: Mapping[str, Any] | None,
) -> set[str]:
    """Every question hash that already has a reviewed label anywhere in the pack."""

    if reviewed_label_pack is None:
        return set()
    found: set[str] = set()

    def walk(value: Any) -> None:
        if isinstance(value, Mapping):
            for key, child in value.items():
                if key == "question_sha256" and isinstance(child, str):
                    found.add(child)
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(reviewed_label_pack)
    return found


def assert_fresh_questions_never_labeled(
    fresh_manifest: Mapping[str, Any],
    train_manifest: Mapping[str, Any],
    reviewed_label_pack: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Fail closed unless every fresh question is genuinely unseen.

    Reusing a train question would make the whole exercise in-sample: the
    train-only calibrator was fit on labels derived from exactly those
    questions.  Cue overlap is treated as a hard failure too, because a shared
    cue means the calibrator was fit over the same graph neighbourhood the
    "fresh" question would probe.
    """

    fresh = _question_records(fresh_manifest)
    train = _question_records(train_manifest)

    fresh_ids = [str(item.get("question_id") or "") for item in fresh]
    if any(not item for item in fresh_ids):
        raise ValueError("fresh questions require non-empty question_id")
    if len(set(fresh_ids)) != len(fresh_ids):
        raise ValueError("fresh question IDs must be unique")

    train_ids = {str(item.get("question_id") or "") for item in train}
    shared_ids = sorted(set(fresh_ids) & train_ids)
    if shared_ids:
        raise ValueError(
            "fresh manifest reuses train question IDs: " + ",".join(shared_ids)
        )

    fresh_hashes = {
        _hex_sha256(item.get("question_sha256"), "question_sha256") for item in fresh
    }
    train_hashes = {str(item.get("question_sha256") or "") for item in train}
    shared_hashes = sorted(fresh_hashes & train_hashes)
    if shared_hashes:
        raise ValueError(
            "fresh manifest reuses train question hashes: " + ",".join(shared_hashes)
        )

    labeled_hashes = _collect_labeled_question_hashes(reviewed_label_pack)
    already_labeled = sorted(fresh_hashes & labeled_hashes)
    if already_labeled:
        raise ValueError(
            "fresh manifest reuses already-labeled questions: "
            + ",".join(already_labeled)
        )

    fresh_cues: set[str] = set()
    for item in fresh:
        terms = [str(term) for term in (item.get("cue_terms") or [])]
        if len(terms) < 1:
            raise ValueError("fresh questions require at least one cue term")
        fresh_cues.update(terms)
    train_cues: set[str] = set()
    for item in train:
        train_cues.update(str(term) for term in (item.get("cue_terms") or []))
    shared_cues = sorted(fresh_cues & train_cues)
    if shared_cues:
        raise ValueError(
            "fresh manifest reuses train cue terms: " + ",".join(shared_cues)
        )

    if str(fresh_manifest.get("contract_sha256") or "") == str(
        train_manifest.get("contract_sha256") or ""
    ):
        raise ValueError("fresh manifest must not reuse the train contract hash")

    return {
        "never_labeled_gate": True,
        "fresh_question_count": len(fresh),
        "train_question_count": len(train),
        "shared_question_ids": [],
        "shared_question_sha256": [],
        "shared_cue_terms": [],
        "labeled_question_hashes_checked": len(labeled_hashes),
        "fresh_cue_terms": sorted(fresh_cues),
        "train_cue_terms_excluded": sorted(train_cues),
    }


def _seal_fresh_vocabulary(payload: Mapping[str, Any]) -> dict[str, Any]:
    normalized = _clone(payload)
    normalized.pop("fresh_candidate_vocabulary_sha256", None)
    normalized["fresh_candidate_vocabulary_sha256"] = canonical_json_sha256(normalized)
    return normalized


def build_fresh_candidate_vocabulary(
    fresh_manifest: Mapping[str, Any],
    source_concepts: Iterable[Mapping[str, Any]],
    eligible: Iterable[Mapping[str, Any]],
    rejected: Iterable[Mapping[str, Any]],
    question_scopes: Iterable[Mapping[str, Any]],
    *,
    created_at: str,
    never_labeled_evidence: Mapping[str, Any],
) -> dict[str, Any]:
    """Seal a fresh vocabulary bound to the manifest and graph, not to labels."""

    # The never-labeled gate is the precondition for everything else: a fresh
    # vocabulary built over an already-labeled question is in-sample no matter
    # how well-formed the rest of the payload is.  Check it first.
    if dict(never_labeled_evidence).get("never_labeled_gate") is not True:
        raise ValueError("fresh vocabulary requires a passing never-labeled gate")
    concepts = list(source_concepts)
    eligible_list = list(eligible)
    rejected_list = list(rejected)
    scopes = list(question_scopes)
    if not scopes:
        raise ValueError("fresh vocabulary requires question scopes")
    if len(concepts) != len(eligible_list) + len(rejected_list):
        raise ValueError("fresh vocabulary concept counts do not sum")

    payload = {
        "fresh_candidate_vocabulary_version": FRESH_CANDIDATE_VOCABULARY_VERSION,
        "phase": FRESH_PHASE,
        "status": FRESH_VOCABULARY_STATUS,
        "vocabulary_scope": FRESH_VOCABULARY_SCOPE,
        "created_at": _require_zoned(created_at, "created_at"),
        "manifest_id": fresh_manifest["manifest_id"],
        "manifest_contract_sha256": _hex_sha256(
            fresh_manifest.get("contract_sha256"), "manifest_contract_sha256"
        ),
        "graph_snapshot_sha256": canonical_json_sha256({"concepts": concepts}),
        "selection_contract": dict(FRESH_SELECTION_CONTRACT),
        "never_labeled_evidence": dict(never_labeled_evidence),
        "reviewed_answer_pack_required": False,
        "reviewed_label_pack_required": False,
        "reviewed_packs_absent_because_questions_are_unanswered": True,
        "source_concept_count": len(concepts),
        "eligible_concept_count": len(eligible_list),
        "rejected_concept_count": len(rejected_list),
        "rejection_counts": dict(
            Counter(str(item.get("reason") or "") for item in rejected_list)
        ),
        "eligible_concepts": eligible_list,
        "rejected_concepts": rejected_list,
        "question_scopes": scopes,
    }
    for field in REQUIRED_FALSE_PREFLIGHT_FIELDS:
        payload[field] = False
    sealed = _seal_fresh_vocabulary(payload)
    return validate_fresh_candidate_vocabulary(sealed, fresh_manifest)


def validate_fresh_candidate_vocabulary(
    payload: Mapping[str, Any],
    fresh_manifest: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    normalized = _clone(payload)
    if normalized.get("fresh_candidate_vocabulary_version") != (
        FRESH_CANDIDATE_VOCABULARY_VERSION
    ):
        raise ValueError("unsupported fresh_candidate_vocabulary_version")
    if normalized.get("phase") != FRESH_PHASE:
        raise ValueError("fresh vocabulary must be J1.1B")
    if normalized.get("status") != FRESH_VOCABULARY_STATUS:
        raise ValueError("fresh vocabulary status mismatch")
    if normalized.get("vocabulary_scope") != FRESH_VOCABULARY_SCOPE:
        raise ValueError("fresh vocabulary scope mismatch")
    _require_zoned(normalized.get("created_at"), "created_at")
    _hex_sha256(normalized.get("manifest_contract_sha256"), "manifest_contract_sha256")
    _hex_sha256(normalized.get("graph_snapshot_sha256"), "graph_snapshot_sha256")

    if normalized.get("selection_contract") != dict(FRESH_SELECTION_CONTRACT):
        raise ValueError("fresh vocabulary selection contract mismatch")
    if normalized.get("reviewed_packs_absent_because_questions_are_unanswered") is not (
        True
    ):
        raise ValueError("fresh vocabulary must record why reviewed packs are absent")
    for forbidden in (
        "reviewed_reference_answer_pack_sha256",
        "reviewed_candidate_label_pack_sha256",
    ):
        if forbidden in normalized:
            raise ValueError(
                "fresh vocabulary must not bind reviewed packs: " + forbidden
            )
    evidence = dict(normalized.get("never_labeled_evidence") or {})
    if evidence.get("never_labeled_gate") is not True:
        raise ValueError("fresh vocabulary requires a passing never-labeled gate")
    for field in ("shared_question_ids", "shared_question_sha256", "shared_cue_terms"):
        if list(evidence.get(field) or []):
            raise ValueError(f"fresh vocabulary never-labeled evidence has {field}")

    eligible = list(normalized.get("eligible_concepts") or [])
    rejected = list(normalized.get("rejected_concepts") or [])
    if normalized.get("eligible_concept_count") != len(eligible):
        raise ValueError("fresh eligible_concept_count mismatch")
    if normalized.get("rejected_concept_count") != len(rejected):
        raise ValueError("fresh rejected_concept_count mismatch")
    if normalized.get("source_concept_count") != len(eligible) + len(rejected):
        raise ValueError("fresh source_concept_count mismatch")
    ids = [str(item.get("concept_id") or "") for item in eligible]
    if not ids or len(ids) != len(set(ids)) or any(not item for item in ids):
        raise ValueError("fresh eligible concepts require unique non-empty IDs")
    expected_rejections = dict(
        Counter(str(item.get("reason") or "") for item in rejected)
    )
    if normalized.get("rejection_counts") != expected_rejections:
        raise ValueError("fresh rejection_counts mismatch")

    scopes = list(normalized.get("question_scopes") or [])
    if not scopes:
        raise ValueError("fresh vocabulary question scopes are required")
    if any(
        int(item.get("eligible_concept_count", 0)) < DEFAULT_TOP_K for item in scopes
    ):
        raise ValueError("each fresh scope requires at least top_k eligible concepts")

    for field in REQUIRED_FALSE_PREFLIGHT_FIELDS:
        if normalized.get(field) is not False:
            raise ValueError(f"{field} must remain false at fresh preflight")

    if fresh_manifest is not None:
        if normalized.get("manifest_contract_sha256") != str(
            fresh_manifest.get("contract_sha256") or ""
        ):
            raise ValueError("fresh vocabulary manifest binding mismatch")
        if normalized.get("manifest_id") != fresh_manifest.get("manifest_id"):
            raise ValueError("fresh vocabulary manifest_id mismatch")
        scope_orders = sorted(int(item["order"]) for item in scopes)
        manifest_orders = sorted(
            int(item["order"]) for item in _question_records(fresh_manifest)
        )
        if scope_orders != manifest_orders:
            raise ValueError("fresh vocabulary scopes do not cover the manifest")

    supplied = str(normalized.get("fresh_candidate_vocabulary_sha256") or "")
    unhashed = _clone(normalized)
    unhashed.pop("fresh_candidate_vocabulary_sha256", None)
    if supplied != canonical_json_sha256(unhashed):
        raise ValueError("fresh_candidate_vocabulary_sha256 mismatch")
    return normalized


def build_real_fresh_pre_question_snapshot_input_pack(
    input_contract: Mapping[str, Any],
    fresh_vocabulary: Mapping[str, Any],
    scored_questions: Iterable[Mapping[str, Any]],
    *,
    captured_at: str,
) -> dict[str, Any]:
    """Build a real (captured, not replayed) fresh pre-question input pack.

    ``input_pack_scope`` stays bound to the sealed contract so the existing
    probability-snapshot and selection validators keep applying unchanged; only
    ``source_scope`` distinguishes a real capture from the earlier replay.
    """

    contract = validate_fresh_pre_question_snapshot_input_contract(input_contract)
    vocabulary = validate_fresh_candidate_vocabulary(fresh_vocabulary)
    source_captured_at = _require_zoned(captured_at, "pre_question_captured_at")

    questions: list[dict[str, Any]] = []
    candidate_row_count = 0
    for question in sorted(
        list(scored_questions), key=lambda item: int(item["order"])
    ):
        rows = [
            {
                "concept_id": str(row["concept_id"]),
                "feature_values": dict(row["feature_values"]),
            }
            for row in question["candidate_rows"]
        ]
        if not rows:
            raise ValueError("real fresh questions require candidate rows")
        candidate_row_count += len(rows)
        questions.append({
            "order": int(question["order"]),
            "question_id": str(question["question_id"]),
            "question_sha256": _hex_sha256(
                question.get("question_sha256"), "question_sha256"
            ),
            "pre_question_captured_at": source_captured_at,
            "candidate_rows": rows,
        })

    if len(questions) < contract["required_candidate_question_count_min"]:
        raise ValueError("real fresh pack requires at least two questions")

    pack = seal_fresh_pre_question_snapshot_input_pack({
        "fresh_pre_question_input_pack_version": contract["input_pack_version"],
        "phase": FRESH_PHASE,
        "status": REAL_FRESH_PACK_STATUS,
        "input_pack_scope": contract["input_pack_scope"],
        "source_scope": REAL_FRESH_SOURCE_SCOPE,
        "captured_not_replayed": True,
        "selection_policy": contract["selection_policy"],
        "feature_schema_sha256": contract["feature_schema_sha256"],
        "feature_names": contract["feature_names"],
        "fresh_pre_question_snapshot_input_contract_sha256": contract[
            "fresh_pre_question_snapshot_input_contract_sha256"
        ],
        "fresh_candidate_vocabulary_sha256": vocabulary[
            "fresh_candidate_vocabulary_sha256"
        ],
        "fresh_manifest_contract_sha256": vocabulary["manifest_contract_sha256"],
        "graph_snapshot_sha256": vocabulary["graph_snapshot_sha256"],
        "never_labeled_gate": True,
        "pre_question_captured_at": source_captured_at,
        "question_count": len(questions),
        "candidate_row_count": candidate_row_count,
        "candidate_questions": questions,
        "fresh_pre_question_input_pack_gate": True,
        "fresh_snapshot_runtime_gate": False,
        "question_selection_runtime_gate": False,
        "runtime_probability_snapshot_gate": False,
        "database_writes": False,
        "learning_enabled": False,
        "heldout_gate": False,
        "performance_claim_gate": False,
        "production_promotion_gate": False,
        "block_reasons": [],
        "next_step": (
            "compute_real_fresh_pre_question_probabilities_offline_"
            "before_runtime_selection"
        ),
    })
    return validate_real_fresh_pre_question_snapshot_input_pack(
        pack, contract, vocabulary
    )


def validate_real_fresh_pre_question_snapshot_input_pack(
    payload: Mapping[str, Any],
    input_contract: Mapping[str, Any],
    fresh_vocabulary: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Structural validation plus the real-capture and never-labeled guarantees."""

    normalized = validate_fresh_pre_question_snapshot_input_pack(
        payload, input_contract
    )
    if normalized.get("status") != REAL_FRESH_PACK_STATUS:
        raise ValueError("real fresh pack status mismatch")
    if normalized.get("source_scope") != REAL_FRESH_SOURCE_SCOPE:
        raise ValueError("real fresh pack must not be a replay of a sealed capture")
    if normalized.get("captured_not_replayed") is not True:
        raise ValueError("real fresh pack must declare it was captured")
    if normalized.get("never_labeled_gate") is not True:
        raise ValueError("real fresh pack requires a passing never-labeled gate")
    _hex_sha256(
        normalized.get("fresh_candidate_vocabulary_sha256"),
        "fresh_candidate_vocabulary_sha256",
    )
    _hex_sha256(normalized.get("graph_snapshot_sha256"), "graph_snapshot_sha256")

    if fresh_vocabulary is not None:
        vocabulary = validate_fresh_candidate_vocabulary(fresh_vocabulary)
        for field in (
            "fresh_candidate_vocabulary_sha256",
            "graph_snapshot_sha256",
        ):
            if normalized.get(field) != vocabulary.get(field):
                raise ValueError(f"real fresh pack {field} binding mismatch")
        if normalized.get("fresh_manifest_contract_sha256") != vocabulary.get(
            "manifest_contract_sha256"
        ):
            raise ValueError("real fresh pack manifest binding mismatch")
        scope_orders = sorted(
            int(item["order"]) for item in vocabulary["question_scopes"]
        )
        pack_orders = sorted(
            int(item["order"]) for item in normalized["candidate_questions"]
        )
        if scope_orders != pack_orders:
            raise ValueError("real fresh pack does not cover the fresh vocabulary")
    return normalized
