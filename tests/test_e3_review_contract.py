from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from neural.baby.e3_review_contract import (
    FROZEN_AUDIT_SHA256,
    FROZEN_DIAGNOSTIC_ROW_COUNT,
    FROZEN_PRIMARY_ROW_COUNT,
    FROZEN_PROPOSAL_FILE_SHA256,
    FROZEN_REVIEW_PACKET_SHA256,
    build_e3_review_readiness,
    build_pending_review_template,
    file_bytes_sha256,
    seal_e3_review_decisions,
    validate_e3_review_decisions,
    validate_frozen_e3_sources,
)
from neural.baby.pending_question_semantics import canonical_json_sha256


ROOT = Path(__file__).resolve().parents[1]
PACKET_PATH = (
    ROOT
    / "scripts"
    / "research"
    / "inputs"
    / "j1_r2_embedding_hard_negative_review_packet_20260728.json"
)
AUDIT_PATH = (
    ROOT
    / "claudedocs"
    / "research"
    / "j1_r2_embedding_hard_negative_vocabulary_audit_20260728.json"
)
PROPOSAL_PATH = (
    ROOT
    / "claudedocs"
    / "research"
    / "J1_R2_E3_PRIMARY_REVIEW_AGENT_RECOMMENDATIONS_2026-07-28.md"
)
CONTRACT_DOC_PATH = (
    ROOT
    / "claudedocs"
    / "research"
    / "J1_R2_E3_REVIEW_TRAINING_CONTRACT_2026-09-12.md"
)


def _load_sources() -> tuple[dict, dict, str, str]:
    packet = json.loads(PACKET_PATH.read_text(encoding="utf-8"))
    audit = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
    proposal_raw = PROPOSAL_PATH.read_bytes()
    return packet, audit, proposal_raw.decode("utf-8"), file_bytes_sha256(
        proposal_raw
    )


def _pending() -> tuple[dict, dict, str, str, dict]:
    packet, audit, proposal_text, proposal_sha256 = _load_sources()
    decisions = build_pending_review_template(
        packet, audit, proposal_text, proposal_sha256
    )
    return packet, audit, proposal_text, proposal_sha256, decisions


def _reseal_source(payload: dict, field: str) -> dict:
    resealed = deepcopy(payload)
    resealed.pop(field, None)
    resealed[field] = canonical_json_sha256(resealed)
    return resealed


def _reviewed_from_proposals() -> tuple[dict, dict, str, str, dict]:
    packet, audit, proposal_text, proposal_sha256, decisions = _pending()
    decisions["status"] = "user_reviewed"
    decisions["reviewer_role"] = "user"
    decisions["decision_source"] = "explicit_user_review_of_e3_primary_rows"
    decisions["reviewed_at"] = "2026-09-12T12:00:00+09:00"
    decisions["review_evidence_reference"] = "test-only-explicit-review-fixture"
    decisions["review_complete_gate"] = True
    positive_by_question = {
        question["question_id"]: question["positive_references"][0]["concept_id"]
        for question in packet["questions"]
    }
    for entry in decisions["entries"]:
        entry["user_relevance_decision"] = entry[
            "agent_proposal_relevance_decision"
        ]
        entry["user_vocabulary_decision"] = entry[
            "agent_proposal_vocabulary_decision"
        ]
        if entry["user_vocabulary_decision"] == "alias":
            entry["alias_target_concept_id"] = positive_by_question[
                entry["question_id"]
            ]
    decisions = seal_e3_review_decisions(decisions)
    return packet, audit, proposal_text, proposal_sha256, decisions


def test_real_frozen_inputs_generate_only_pending_primary_review_rows() -> None:
    packet, audit, proposal_text, proposal_sha256, decisions = _pending()

    primary, diagnostic = validate_frozen_e3_sources(
        packet, audit, proposal_text, proposal_sha256
    )
    assert packet["hard_negative_review_packet_sha256"] == (
        FROZEN_REVIEW_PACKET_SHA256
    )
    assert audit["hard_negative_vocabulary_audit_sha256"] == FROZEN_AUDIT_SHA256
    assert proposal_sha256 == FROZEN_PROPOSAL_FILE_SHA256
    assert len(primary) == FROZEN_PRIMARY_ROW_COUNT
    assert len(diagnostic) == FROZEN_DIAGNOSTIC_ROW_COUNT
    assert len(decisions["entries"]) == FROZEN_PRIMARY_ROW_COUNT
    assert decisions["status"] == "awaiting_user_review"
    assert decisions["review_complete_gate"] is False
    assert all(
        entry["user_relevance_decision"] is None
        and entry["user_vocabulary_decision"] is None
        for entry in decisions["entries"]
    )
    assert {entry["selection_reason"] for entry in decisions["entries"]} == {
        "top_unjudged"
    }
    primary_ids = {
        entry["candidate_review_id"] for entry in decisions["entries"]
    }
    assert all(
        candidate["candidate_review_id"] not in primary_ids
        for candidate in diagnostic
    )
    readiness = build_e3_review_readiness(
        packet, audit, proposal_text, proposal_sha256, decisions
    )
    assert readiness["fit_eligibility_summary"][
        "e3_development_rows_reserved_count"
    ] == 20


def test_agent_proposals_remain_proposals_with_expected_source_counts() -> None:
    *_, decisions = _pending()

    assert decisions["reviewer_role"] is None
    assert decisions["decision_source"] is None
    assert decisions["review_evidence_reference"] is None
    assert {
        decision: sum(
            entry["agent_proposal_relevance_decision"] == decision
            for entry in decisions["entries"]
        )
        for decision in (
            "positive",
            "context",
            "hard_negative",
            "unrelated_negative",
        )
    } == {
        "positive": 1,
        "context": 52,
        "hard_negative": 4,
        "unrelated_negative": 3,
    }
    assert {
        decision: sum(
            entry["agent_proposal_vocabulary_decision"] == decision
            for entry in decisions["entries"]
        )
        for decision in ("canonical", "alias", "fragment", "malformed")
    } == {"canonical": 36, "alias": 1, "fragment": 16, "malformed": 7}


def test_resealed_source_id_tamper_is_rejected_by_frozen_hash() -> None:
    packet, audit, proposal_text, proposal_sha256 = _load_sources()
    tampered = deepcopy(packet)
    tampered["questions"][0]["review_candidates"][0][
        "candidate_review_id"
    ] = "f" * 64
    tampered = _reseal_source(tampered, "hard_negative_review_packet_sha256")

    with pytest.raises(ValueError, match="not the frozen E3 input"):
        validate_frozen_e3_sources(
            tampered, audit, proposal_text, proposal_sha256
        )


def test_decision_binding_hash_tamper_is_rejected() -> None:
    packet, audit, proposal_text, proposal_sha256, decisions = _pending()
    decisions["bindings"]["candidate_vocabulary_sha256"] = "f" * 64

    with pytest.raises(ValueError, match="e3_review_decisions_sha256 mismatch"):
        validate_e3_review_decisions(
            packet, audit, proposal_text, proposal_sha256, decisions
        )


@pytest.mark.parametrize("mutation", ["missing", "duplicate"])
def test_missing_or_duplicate_primary_decision_is_rejected(mutation: str) -> None:
    packet, audit, proposal_text, proposal_sha256, decisions = _pending()
    if mutation == "missing":
        decisions["entries"].pop()
    else:
        decisions["entries"][-1] = deepcopy(decisions["entries"][0])
    decisions = seal_e3_review_decisions(decisions)

    with pytest.raises(ValueError, match="60 primary rows|duplicate"):
        validate_e3_review_decisions(
            packet, audit, proposal_text, proposal_sha256, decisions
        )


def test_diagnostic_row_cannot_be_inserted_as_a_negative() -> None:
    packet, audit, proposal_text, proposal_sha256, decisions = _pending()
    _, diagnostic = validate_frozen_e3_sources(
        packet, audit, proposal_text, proposal_sha256
    )
    injected = deepcopy(decisions["entries"][0])
    injected.update(
        {
            "candidate_review_id": diagnostic[0]["candidate_review_id"],
            "concept_id": diagnostic[0]["concept_id"],
            "concept_name": diagnostic[0]["concept_name"],
            "selection_reason": "positive_rank_neighbor_for_top8_miss",
            "user_relevance_decision": "hard_negative",
            "user_vocabulary_decision": "canonical",
        }
    )
    decisions["entries"][0] = injected
    decisions = seal_e3_review_decisions(decisions)

    with pytest.raises(ValueError, match="frozen primary rows"):
        validate_e3_review_decisions(
            packet, audit, proposal_text, proposal_sha256, decisions
        )


def test_user_review_cannot_leave_a_primary_label_missing() -> None:
    packet, audit, proposal_text, proposal_sha256, decisions = (
        _reviewed_from_proposals()
    )
    decisions["entries"][0]["user_relevance_decision"] = None
    decisions = seal_e3_review_decisions(decisions)

    with pytest.raises(ValueError, match="requires a user relevance decision"):
        validate_e3_review_decisions(
            packet,
            audit,
            proposal_text,
            proposal_sha256,
            decisions,
            require_user_review=True,
        )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("status", "agent_approved", "status must be"),
        ("reviewer_role", "assistant", "reviewer_role=user"),
        ("decision_source", "agent_proposal", "explicit user provenance"),
        ("review_evidence_reference", None, "review_evidence_reference"),
    ],
)
def test_unauthorized_or_incomplete_review_provenance_is_rejected(
    field: str, value: str | None, message: str
) -> None:
    packet, audit, proposal_text, proposal_sha256, decisions = (
        _reviewed_from_proposals()
    )
    decisions[field] = value
    decisions = seal_e3_review_decisions(decisions)

    with pytest.raises(ValueError, match=message):
        validate_e3_review_decisions(
            packet,
            audit,
            proposal_text,
            proposal_sha256,
            decisions,
            require_user_review=True,
        )


def test_context_and_uncertain_are_excluded_from_binary_fit_summary() -> None:
    packet, audit, proposal_text, proposal_sha256, decisions = (
        _reviewed_from_proposals()
    )
    first_fit_context = next(
        entry
        for entry in decisions["entries"]
        if entry["target_partition"] == "fit_pool"
        and entry["user_relevance_decision"] == "context"
    )
    first_fit_context["user_relevance_decision"] = "uncertain"
    decisions = seal_e3_review_decisions(decisions)
    validated = validate_e3_review_decisions(
        packet,
        audit,
        proposal_text,
        proposal_sha256,
        decisions,
        require_user_review=True,
    )
    readiness = build_e3_review_readiness(
        packet, audit, proposal_text, proposal_sha256, validated
    )
    fit_rows = [
        entry
        for entry in validated["entries"]
        if entry["target_partition"] == "fit_pool"
    ]
    expected_context = sum(
        entry["user_relevance_decision"] == "context" for entry in fit_rows
    )
    expected_uncertain = sum(
        entry["user_relevance_decision"] == "uncertain" for entry in fit_rows
    )
    expected_binary = sum(
        entry["user_relevance_decision"]
        in {"positive", "hard_negative", "unrelated_negative"}
        for entry in fit_rows
    )

    summary = readiness["fit_eligibility_summary"]
    assert summary["e3_fit_context_excluded_count"] == expected_context
    assert summary["e3_fit_uncertain_excluded_count"] == expected_uncertain
    assert expected_context > 0
    assert expected_uncertain == 1
    assert summary["e3_fit_eligible_row_count"] == expected_binary
    assert summary["e3_diagnostic_rows_excluded_count"] == 24
    assert readiness["fit_row_contract_eligible_gate"] is True
    assert readiness["fit_data_sufficiency_gate"] is False
    assert readiness["training_data_materialization_gate"] is False
    assert readiness["learned_head_fit_gate"] is False
    assert readiness["live_graph_cleanup_gate"] is False


def test_contract_document_preserves_review_and_no_effect_boundaries() -> None:
    document = CONTRACT_DOC_PATH.read_text(encoding="utf-8")

    for required in (
        "이번 진행 지시는 60개 의미 라벨의",
        "승인이 아니다",
        "frozen evaluation universe: 1,069 concepts",
        "fit pool 40행",
        "development challenge pool 20행",
        "rank 주변 24행은 score-band 진단 전용",
        "context는 관련된 의미 이웃이므로 binary negative로 만들지 않는다",
        "uncertain은 fit에서 제외한다",
        "live graph merge/delete/cleanup 권한을 주지 않는다",
        "DB read/write",
        "inference/download",
        "lockbox 생성/소비",
    ):
        assert required in document
