"""Fail-closed J1-R2-E3 review and fit-policy preparation.

This module binds the existing E3 agent proposal to the frozen pending-review
packet and read-only audit.  It prepares a decision surface and aggregate fit
eligibility only.  It never assigns user decisions, materializes training
rows, accesses the database, runs a model, or touches the lockbox.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from datetime import datetime
from typing import Any, Mapping

from neural.baby.pending_question_semantics import canonical_json_sha256


PHASE = "J1-R2-E3"
DECISION_VERSION = 1
READINESS_VERSION = 1

FROZEN_REVIEW_PACKET_SHA256 = (
    "aec20a9d0c714e768c560d8eb4d517edf604ca6c03cd7fc01ed8830fbf2339e4"
)
FROZEN_AUDIT_SHA256 = (
    "696fe080b26bbb40af6e433394956b8cf6649ca1aff40d843d11288b2f3a04b4"
)
FROZEN_PROPOSAL_FILE_SHA256 = (
    "e358c84aa3271400241fad6a1117c8375502d0a8a1aee2aeab89dc58b1657708"
)
FROZEN_CANDIDATE_VOCABULARY_SHA256 = (
    "bc06ed54f24420eecdaa0be156f6041d882e80648bc64030baf5ac00bd2abd82"
)
FROZEN_CANDIDATE_UNIVERSE_COUNT = 1069
FROZEN_PRIMARY_ROW_COUNT = 60
FROZEN_DIAGNOSTIC_ROW_COUNT = 24
PRIOR_R1_FIT_CANDIDATE_COUNT = 58

RELEVANCE_DECISIONS = frozenset(
    {"positive", "context", "hard_negative", "unrelated_negative", "uncertain"}
)
VOCABULARY_DECISIONS = frozenset(
    {"canonical", "alias", "fragment", "malformed", "uncertain"}
)
BINARY_NEGATIVE_DECISIONS = frozenset(
    {"hard_negative", "unrelated_negative"}
)
FIT_ELIGIBLE_RELEVANCE_DECISIONS = frozenset(
    {"positive", *BINARY_NEGATIVE_DECISIONS}
)
_HASH_RE = re.compile(r"^[0-9a-f]{64}$")
_SECTION_RE = re.compile(r"^###\s+(\d{2})\s+-\s+(.+?)\s*$")
_TABLE_ROW_RE = re.compile(r"^\|\s*(\d+)\s*\|")


def file_bytes_sha256(raw: bytes) -> str:
    """Return the SHA-256 used to bind the proposal file byte-for-byte."""

    return hashlib.sha256(raw).hexdigest()


def _deepcopy_json(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False))


def _validate_self_hash(
    payload: Mapping[str, Any], field: str, expected: str | None = None
) -> None:
    supplied = str(payload.get(field) or "")
    if not _HASH_RE.fullmatch(supplied):
        raise ValueError(f"{field} must be a SHA-256")
    unhashed = _deepcopy_json(payload)
    unhashed.pop(field, None)
    if supplied != canonical_json_sha256(unhashed):
        raise ValueError(f"{field} mismatch")
    if expected is not None and supplied != expected:
        raise ValueError(f"{field} is not the frozen E3 input")


def _require_zoned_timestamp(value: Any, field: str) -> str:
    raw = str(value or "").strip()
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} must include a timezone")
    return raw


def _source_rows(
    packet: Mapping[str, Any], reason: str
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for question in packet.get("questions") or []:
        for candidate in question.get("review_candidates") or []:
            reasons = list(candidate.get("selection_reasons") or [])
            if reason not in reasons:
                continue
            rows.append(
                {
                    "order": int(question["order"]),
                    "question_id": str(question["question_id"]),
                    "question": str(question["question"]),
                    "question_sha256": str(question["question_sha256"]),
                    "target_partition": str(question["target_partition"]),
                    "candidate_review_id": str(candidate["candidate_review_id"]),
                    "concept_id": str(candidate["concept_id"]),
                    "concept_name": str(candidate["concept_name"]),
                    "embedding_rank": int(candidate["embedding_rank"]),
                    "selection_reasons": reasons,
                }
            )
    return rows


def validate_frozen_e3_sources(
    packet: Mapping[str, Any],
    audit: Mapping[str, Any],
    proposal_text: str,
    proposal_file_sha256: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Validate the exact frozen E3 packet, audit, and proposal bindings."""

    _validate_self_hash(
        packet,
        "hard_negative_review_packet_sha256",
        FROZEN_REVIEW_PACKET_SHA256,
    )
    _validate_self_hash(
        audit,
        "hard_negative_vocabulary_audit_sha256",
        FROZEN_AUDIT_SHA256,
    )
    if proposal_file_sha256 != FROZEN_PROPOSAL_FILE_SHA256:
        raise ValueError("proposal file is not the frozen E3 recommendation")
    if packet.get("phase") != PHASE or audit.get("phase") != PHASE:
        raise ValueError("E3 source phase mismatch")
    if packet.get("status") != "pending_user_review_not_training_data":
        raise ValueError("E3 packet is no longer the pending-review source")
    if audit.get("status") != (
        "development_diagnostic_generated_review_pending_not_training_data"
    ):
        raise ValueError("E3 audit status mismatch")
    if audit.get("bindings", {}).get("hard_negative_review_packet_sha256") != (
        FROZEN_REVIEW_PACKET_SHA256
    ):
        raise ValueError("E3 audit does not bind the frozen packet")
    for source in (packet, audit):
        if source.get("bindings", {}).get("candidate_vocabulary_sha256") != (
            FROZEN_CANDIDATE_VOCABULARY_SHA256
        ):
            raise ValueError("candidate vocabulary binding mismatch")
    if audit.get("vocabulary_quality", {}).get("candidate_count") != (
        FROZEN_CANDIDATE_UNIVERSE_COUNT
    ):
        raise ValueError("candidate universe count drift")
    reason_counts = audit.get("selection_summary", {}).get(
        "selection_reason_counts", {}
    )
    if reason_counts != {
        "positive_rank_neighbor_for_top8_miss": FROZEN_DIAGNOSTIC_ROW_COUNT,
        "top_unjudged": FROZEN_PRIMARY_ROW_COUNT,
    }:
        raise ValueError("E3 source row-role counts drift")
    if packet.get("question_count") != 12 or packet.get("review_row_count") != 84:
        raise ValueError("E3 packet count drift")
    source_gates = (
        "review_complete_gate",
        "training_data_materialization_gate",
        "database_write_gate",
        "learned_head_fit_gate",
        "heldout_gate",
        "performance_claim_gate",
        "production_promotion_gate",
    )
    if any(packet.get(gate) is not False for gate in source_gates):
        raise ValueError("pending E3 packet cannot enable downstream gates")
    if "Status: `agent_proposal_not_user_reviewed_not_training_data`" not in (
        proposal_text
    ):
        raise ValueError("proposal status does not preserve agent-only provenance")
    if FROZEN_REVIEW_PACKET_SHA256 not in proposal_text:
        raise ValueError("proposal does not bind the frozen review packet")
    if FROZEN_AUDIT_SHA256 not in proposal_text:
        raise ValueError("proposal does not bind the frozen audit")

    primary = _source_rows(packet, "top_unjudged")
    diagnostic = _source_rows(
        packet, "positive_rank_neighbor_for_top8_miss"
    )
    if len(primary) != FROZEN_PRIMARY_ROW_COUNT:
        raise ValueError("E3 primary row count drift")
    if len(diagnostic) != FROZEN_DIAGNOSTIC_ROW_COUNT:
        raise ValueError("E3 diagnostic row count drift")
    primary_ids = {row["candidate_review_id"] for row in primary}
    diagnostic_ids = {row["candidate_review_id"] for row in diagnostic}
    if len(primary_ids) != len(primary) or len(diagnostic_ids) != len(diagnostic):
        raise ValueError("duplicate E3 source candidate_review_id")
    if primary_ids & diagnostic_ids:
        raise ValueError("diagnostic-only rows overlap the primary review rows")
    return primary, diagnostic


def parse_agent_proposal(proposal_text: str) -> list[dict[str, Any]]:
    """Parse the fixed recommendation tables without promoting their labels."""

    rows: list[dict[str, Any]] = []
    current_order: int | None = None
    current_question: str | None = None
    seen_orders: set[int] = set()
    for raw_line in proposal_text.splitlines():
        section_match = _SECTION_RE.match(raw_line)
        if section_match:
            current_order = int(section_match.group(1))
            current_question = section_match.group(2).strip()
            if current_order in seen_orders:
                raise ValueError("duplicate proposal question section")
            seen_orders.add(current_order)
            continue
        if not _TABLE_ROW_RE.match(raw_line):
            continue
        if current_order is None or current_question is None:
            raise ValueError("proposal table row appears before a question section")
        cells = [cell.strip() for cell in raw_line.strip().strip("|").split("|")]
        if len(cells) != 5:
            raise ValueError("proposal table row must contain five columns")
        rank_raw, name, relevance, vocabulary, rationale = cells
        if relevance not in RELEVANCE_DECISIONS:
            raise ValueError("proposal relevance decision is invalid")
        if vocabulary not in VOCABULARY_DECISIONS:
            raise ValueError("proposal vocabulary decision is invalid")
        if not rationale:
            raise ValueError("proposal rationale is required")
        rows.append(
            {
                "order": current_order,
                "question": current_question,
                "embedding_rank": int(rank_raw),
                "concept_name": name.strip("`"),
                "agent_proposal_relevance_decision": relevance,
                "agent_proposal_vocabulary_decision": vocabulary,
                "agent_proposal_rationale": rationale,
            }
        )
    if len(rows) != FROZEN_PRIMARY_ROW_COUNT or len(seen_orders) != 12:
        raise ValueError("proposal must contain 12 sections and 60 primary rows")
    return rows


def _proposal_by_source_key(
    proposal_rows: list[dict[str, Any]],
) -> dict[tuple[int, int, str], dict[str, Any]]:
    result: dict[tuple[int, int, str], dict[str, Any]] = {}
    for row in proposal_rows:
        key = (
            int(row["order"]),
            int(row["embedding_rank"]),
            str(row["concept_name"]),
        )
        if key in result:
            raise ValueError("duplicate proposal candidate key")
        result[key] = row
    return result


def seal_e3_review_decisions(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Seal an E3 decision document after its fields have been edited."""

    normalized = _deepcopy_json(payload)
    normalized.pop("e3_review_decisions_sha256", None)
    normalized["e3_review_decisions_sha256"] = canonical_json_sha256(normalized)
    return normalized


def build_pending_review_template(
    packet: Mapping[str, Any],
    audit: Mapping[str, Any],
    proposal_text: str,
    proposal_file_sha256: str,
) -> dict[str, Any]:
    """Build a self-hashed 60-row template with every user decision blank."""

    primary, diagnostic = validate_frozen_e3_sources(
        packet, audit, proposal_text, proposal_file_sha256
    )
    proposals = _proposal_by_source_key(parse_agent_proposal(proposal_text))
    entries: list[dict[str, Any]] = []
    for source in primary:
        key = (
            int(source["order"]),
            int(source["embedding_rank"]),
            str(source["concept_name"]),
        )
        proposal = proposals.pop(key, None)
        if proposal is None or proposal["question"] != source["question"]:
            raise ValueError("proposal row does not match the frozen E3 candidate")
        entries.append(
            {
                "order": source["order"],
                "question_id": source["question_id"],
                "question": source["question"],
                "question_sha256": source["question_sha256"],
                "target_partition": source["target_partition"],
                "candidate_review_id": source["candidate_review_id"],
                "concept_id": source["concept_id"],
                "concept_name": source["concept_name"],
                "embedding_rank": source["embedding_rank"],
                "selection_reason": "top_unjudged",
                "agent_proposal_relevance_decision": proposal[
                    "agent_proposal_relevance_decision"
                ],
                "agent_proposal_vocabulary_decision": proposal[
                    "agent_proposal_vocabulary_decision"
                ],
                "agent_proposal_rationale": proposal[
                    "agent_proposal_rationale"
                ],
                "user_relevance_decision": None,
                "user_vocabulary_decision": None,
                "alias_target_concept_id": None,
                "reviewer_note": None,
            }
        )
    if proposals:
        raise ValueError("proposal contains rows outside the frozen primary scope")

    partition_counts = Counter(row["target_partition"] for row in primary)
    payload = {
        "e3_review_decision_version": DECISION_VERSION,
        "phase": PHASE,
        "status": "awaiting_user_review",
        "reviewer_role": None,
        "decision_source": None,
        "reviewed_at": None,
        "review_evidence_reference": None,
        "bindings": {
            "hard_negative_review_packet_sha256": FROZEN_REVIEW_PACKET_SHA256,
            "hard_negative_vocabulary_audit_sha256": FROZEN_AUDIT_SHA256,
            "agent_proposal_file_sha256": proposal_file_sha256,
            "candidate_vocabulary_sha256": packet["bindings"][
                "candidate_vocabulary_sha256"
            ],
            "development_label_pack_sha256": packet["bindings"][
                "development_label_pack_sha256"
            ],
            "generator_spec_sha256": packet["bindings"][
                "generator_spec_sha256"
            ],
            "embedding_baseline_artifact_sha256": packet["bindings"][
                "embedding_baseline_artifact_sha256"
            ],
        },
        "scope": {
            "frozen_candidate_universe_count": FROZEN_CANDIDATE_UNIVERSE_COUNT,
            "primary_review_row_count": len(primary),
            "diagnostic_only_row_count": len(diagnostic),
            "question_count": int(packet["question_count"]),
            "primary_question_partition_counts": dict(sorted(partition_counts.items())),
            "original_target_partition_roles_preserved": True,
            "diagnostic_rows_are_review_or_training_entries": False,
        },
        "training_policy": {
            "task": "question_plus_candidate_concept_to_relevance",
            "positive_target": 1,
            "binary_negative_decisions": sorted(BINARY_NEGATIVE_DECISIONS),
            "context_handling": "exclude_from_binary_negative",
            "uncertain_handling": "exclude_from_fit",
            "development_challenge_pool_handling": "evaluation_only_not_fit",
            "unreviewed_graph_concepts_are_negatives": False,
            "diagnostic_only_rows_are_negatives": False,
            "reviewed_aliases_are_live_graph_cleanup": False,
            "causal_lm_graph_neighbor_replay_reused": False,
        },
        "entries": entries,
        "review_complete_gate": False,
        "training_data_materialization_gate": False,
        "learned_head_fit_gate": False,
        "database_write_gate": False,
        "lockbox_materialization_gate": False,
        "heldout_gate": False,
        "performance_claim_gate": False,
        "production_promotion_gate": False,
    }
    return seal_e3_review_decisions(payload)


def _source_entry_map(
    packet: Mapping[str, Any],
    proposal_text: str,
    proposal_file_sha256: str,
    audit: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    template = build_pending_review_template(
        packet, audit, proposal_text, proposal_file_sha256
    )
    return {
        str(entry["candidate_review_id"]): entry
        for entry in template["entries"]
    }


def validate_e3_review_decisions(
    packet: Mapping[str, Any],
    audit: Mapping[str, Any],
    proposal_text: str,
    proposal_file_sha256: str,
    decisions: Mapping[str, Any],
    *,
    require_user_review: bool = False,
) -> dict[str, Any]:
    """Validate exact row coverage, provenance, and review-state semantics."""

    validate_frozen_e3_sources(packet, audit, proposal_text, proposal_file_sha256)
    normalized = _deepcopy_json(decisions)
    _validate_self_hash(normalized, "e3_review_decisions_sha256")
    if normalized.get("e3_review_decision_version") != DECISION_VERSION:
        raise ValueError("unsupported e3_review_decision_version")
    if normalized.get("phase") != PHASE:
        raise ValueError("E3 decision phase mismatch")
    expected_bindings = build_pending_review_template(
        packet, audit, proposal_text, proposal_file_sha256
    )["bindings"]
    if normalized.get("bindings") != expected_bindings:
        raise ValueError("E3 decision input bindings mismatch")
    expected_scope = build_pending_review_template(
        packet, audit, proposal_text, proposal_file_sha256
    )["scope"]
    if normalized.get("scope") != expected_scope:
        raise ValueError("E3 decision scope mismatch")
    expected_policy = build_pending_review_template(
        packet, audit, proposal_text, proposal_file_sha256
    )["training_policy"]
    if normalized.get("training_policy") != expected_policy:
        raise ValueError("E3 training policy mismatch")

    source_by_id = _source_entry_map(
        packet, proposal_text, proposal_file_sha256, audit
    )
    entries = list(normalized.get("entries") or [])
    entry_ids = [str(entry.get("candidate_review_id") or "") for entry in entries]
    if len(entries) != FROZEN_PRIMARY_ROW_COUNT:
        raise ValueError("E3 decisions must cover all 60 primary rows")
    if len(set(entry_ids)) != len(entry_ids):
        raise ValueError("duplicate E3 decision candidate_review_id")
    if set(entry_ids) != set(source_by_id):
        raise ValueError("E3 decisions must exactly cover the frozen primary rows")
    immutable_fields = (
        "order",
        "question_id",
        "question",
        "question_sha256",
        "target_partition",
        "candidate_review_id",
        "concept_id",
        "concept_name",
        "embedding_rank",
        "selection_reason",
        "agent_proposal_relevance_decision",
        "agent_proposal_vocabulary_decision",
        "agent_proposal_rationale",
    )
    known_concept_ids = {
        str(candidate["concept_id"])
        for question in packet["questions"]
        for candidate in question["review_candidates"]
    }
    known_concept_ids.update(
        str(reference["concept_id"])
        for question in packet["questions"]
        for field in (
            "positive_references",
            "existing_context_references",
            "existing_explicit_negative_references",
        )
        for reference in question.get(field) or []
    )
    for entry in entries:
        source = source_by_id[str(entry["candidate_review_id"])]
        if any(entry.get(field) != source.get(field) for field in immutable_fields):
            raise ValueError("E3 decision row changed a frozen source or proposal field")

    status = normalized.get("status")
    if status == "awaiting_user_review":
        if any(
            normalized.get(field) is not None
            for field in (
                "reviewer_role",
                "decision_source",
                "reviewed_at",
                "review_evidence_reference",
            )
        ):
            raise ValueError("pending E3 review cannot claim reviewer provenance")
        for entry in entries:
            if any(
                entry.get(field) is not None
                for field in (
                    "user_relevance_decision",
                    "user_vocabulary_decision",
                    "alias_target_concept_id",
                    "reviewer_note",
                )
            ):
                raise ValueError("pending E3 review must leave user decisions blank")
    elif status == "user_reviewed":
        if normalized.get("reviewer_role") != "user":
            raise ValueError("reviewed E3 decisions require reviewer_role=user")
        if normalized.get("decision_source") != (
            "explicit_user_review_of_e3_primary_rows"
        ):
            raise ValueError("reviewed E3 decisions require explicit user provenance")
        _require_zoned_timestamp(normalized.get("reviewed_at"), "reviewed_at")
        if not str(normalized.get("review_evidence_reference") or "").strip():
            raise ValueError("review_evidence_reference is required")
        for entry in entries:
            relevance = entry.get("user_relevance_decision")
            vocabulary = entry.get("user_vocabulary_decision")
            if relevance not in RELEVANCE_DECISIONS:
                raise ValueError("every primary row requires a user relevance decision")
            if vocabulary not in VOCABULARY_DECISIONS:
                raise ValueError("every primary row requires a user vocabulary decision")
            alias_target = entry.get("alias_target_concept_id")
            if vocabulary == "alias":
                if (
                    alias_target not in known_concept_ids
                    or alias_target == entry.get("concept_id")
                ):
                    raise ValueError("reviewed alias requires a known distinct target")
            elif alias_target is not None:
                raise ValueError("non-alias decision cannot set alias_target_concept_id")
    else:
        raise ValueError("E3 status must be awaiting_user_review or user_reviewed")
    if require_user_review and status != "user_reviewed":
        raise ValueError("E3 decisions require explicit user review")

    required_false = (
        "training_data_materialization_gate",
        "learned_head_fit_gate",
        "database_write_gate",
        "lockbox_materialization_gate",
        "heldout_gate",
        "performance_claim_gate",
        "production_promotion_gate",
    )
    if any(normalized.get(field) is not False for field in required_false):
        raise ValueError("E3 review contract cannot enable downstream effects")
    if normalized.get("review_complete_gate") is not (status == "user_reviewed"):
        raise ValueError("review_complete_gate does not match review status")
    return normalized


def _seal_readiness(payload: Mapping[str, Any]) -> dict[str, Any]:
    normalized = _deepcopy_json(payload)
    normalized.pop("e3_review_readiness_sha256", None)
    normalized["e3_review_readiness_sha256"] = canonical_json_sha256(normalized)
    return normalized


def build_e3_review_readiness(
    packet: Mapping[str, Any],
    audit: Mapping[str, Any],
    proposal_text: str,
    proposal_file_sha256: str,
    decisions: Mapping[str, Any],
) -> dict[str, Any]:
    """Summarize review and potential fit rows without materializing them."""

    reviewed = validate_e3_review_decisions(
        packet,
        audit,
        proposal_text,
        proposal_file_sha256,
        decisions,
    )
    is_reviewed = reviewed["status"] == "user_reviewed"
    relevance_counts: Counter[str] = Counter()
    vocabulary_counts: Counter[str] = Counter()
    fit_eligible_counts: Counter[str] = Counter()
    context_excluded = 0
    uncertain_excluded = 0
    development_reserved = sum(
        entry["target_partition"] == "development_challenge_pool"
        for entry in reviewed["entries"]
    )
    for entry in reviewed["entries"]:
        if not is_reviewed:
            continue
        relevance = str(entry["user_relevance_decision"])
        vocabulary = str(entry["user_vocabulary_decision"])
        relevance_counts[relevance] += 1
        vocabulary_counts[vocabulary] += 1
        if entry["target_partition"] == "development_challenge_pool":
            continue
        if relevance == "context":
            context_excluded += 1
        elif relevance == "uncertain":
            uncertain_excluded += 1
        elif relevance in FIT_ELIGIBLE_RELEVANCE_DECISIONS:
            fit_eligible_counts[relevance] += 1

    fit_eligible_count = sum(fit_eligible_counts.values())
    fit_rows_eligible = is_reviewed and fit_eligible_count > 0
    pending_count = 0 if is_reviewed else FROZEN_PRIMARY_ROW_COUNT
    payload = {
        "e3_review_readiness_version": READINESS_VERSION,
        "phase": PHASE,
        "status": (
            "user_review_complete_fit_policy_summary_only"
            if is_reviewed
            else "user_review_incomplete_fit_ineligible"
        ),
        "bindings": {
            **reviewed["bindings"],
            "e3_review_decisions_sha256": reviewed[
                "e3_review_decisions_sha256"
            ],
        },
        "review_summary": {
            "required_primary_row_count": FROZEN_PRIMARY_ROW_COUNT,
            "reviewed_primary_row_count": (
                FROZEN_PRIMARY_ROW_COUNT if is_reviewed else 0
            ),
            "pending_primary_row_count": pending_count,
            "diagnostic_only_row_count": FROZEN_DIAGNOSTIC_ROW_COUNT,
            "relevance_decision_counts": dict(sorted(relevance_counts.items())),
            "vocabulary_decision_counts": dict(sorted(vocabulary_counts.items())),
        },
        "fit_eligibility_summary": {
            "prior_r1_fit_candidate_count": PRIOR_R1_FIT_CANDIDATE_COUNT,
            "prior_r1_count_is_sufficient_training_evidence": False,
            "e3_fit_eligible_row_count": fit_eligible_count,
            "e3_fit_eligible_decision_counts": dict(
                sorted(fit_eligible_counts.items())
            ),
            "e3_fit_context_excluded_count": context_excluded,
            "e3_fit_uncertain_excluded_count": uncertain_excluded,
            "e3_development_rows_reserved_count": development_reserved,
            "e3_diagnostic_rows_excluded_count": FROZEN_DIAGNOSTIC_ROW_COUNT,
            "fit_eligibility_assessed": is_reviewed,
            "fit_data_sufficiency_assessed": False,
        },
        "review_complete_gate": is_reviewed,
        "fit_row_contract_eligible_gate": fit_rows_eligible,
        "fit_data_sufficiency_gate": False,
        "training_data_materialization_gate": False,
        "learned_head_fit_gate": False,
        "database_write_gate": False,
        "live_graph_cleanup_gate": False,
        "lockbox_materialization_gate": False,
        "heldout_gate": False,
        "performance_claim_gate": False,
        "production_promotion_gate": False,
        "next_step": (
            "assess_reviewed_fit_distribution_and_seek_separate_training_approval"
            if is_reviewed
            else "user_must_review_all_60_primary_rows"
        ),
    }
    return _seal_readiness(payload)


def validate_e3_review_readiness(
    packet: Mapping[str, Any],
    audit: Mapping[str, Any],
    proposal_text: str,
    proposal_file_sha256: str,
    decisions: Mapping[str, Any],
    readiness: Mapping[str, Any],
) -> dict[str, Any]:
    """Rebuild the readiness report and reject drift or optimistic gates."""

    normalized = _deepcopy_json(readiness)
    _validate_self_hash(normalized, "e3_review_readiness_sha256")
    expected = build_e3_review_readiness(
        packet, audit, proposal_text, proposal_file_sha256, decisions
    )
    if normalized != expected:
        raise ValueError("E3 review readiness does not match validated decisions")
    return normalized
