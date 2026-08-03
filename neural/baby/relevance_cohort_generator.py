"""Deterministic J1-R2 development-cohort generation and review contracts.

The generator uses a fixed synthetic fact environment. It never asks the
subject model, Neo4j relations, or an external API for evaluation truth.
Unlisted graph concepts remain unlabeled rather than becoming negatives.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from datetime import datetime
from typing import Any, Iterable, Mapping

from neural.baby.pending_question_semantics import canonical_json_sha256
from neural.baby.relevance_cohort_lifecycle import (
    PHASE,
    seal_cohort_manifest,
    validate_cohort_manifest,
)
from neural.baby.relevance_scorer_contract import graph_vocabulary_partition


GENERATOR_SPEC_VERSION = 1
SAMPLE_SIZE_PLAN_VERSION = 1
REVIEW_PACKET_VERSION = 1
REVIEW_DECISIONS_VERSION = 1
DEVELOPMENT_LABEL_PACK_VERSION = 1
GENERATOR_ID = "j1-r2-korean-closed-world-relations-v1"
DEVELOPMENT_COHORT_ID = "j1-r2-rolling-development-0001"
DEVELOPMENT_GENERATION_ID = "development-generation-0001"
EXPECTED_QUESTION_COUNT = 12
EXPLICIT_NEGATIVES_PER_QUESTION = 3
EXPECTED_PARTITION_COUNTS = {
    "fit_pool": 8,
    "development_challenge_pool": 4,
    "lockbox_challenge_pool": 0,
}
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


_CONCEPTS = {
    "서울": "1416920b-6d2a-4cd6-a630-a0a509752fc1",
    "한국": "32097d72-3b93-4959-b164-7fa253ecec4e",
    "수도": "e8025266-3786-4fcc-8d0b-ac0fbb800142",
    "지구": "a3cd2756-127f-4988-b2fa-997ad77fba64",
    "달": "7d46d662-71c9-4d21-93c3-762a3f7c1dab",
    "구름": "03a8049b-3b54-4a05-9fad-365f3499a3bb",
    "물": "35d1fd6c-802c-4bbc-8743-e232381e9569",
    "최단경로": "a9bdd518-7107-47e1-9aee-63cb4ec9052b",
    "알고리즘": "abbc4367-c58c-4455-83a8-d3ef1b2979ff",
    "문제": "de7dff2a-a5d1-401d-8527-fad94d317b21",
    "청각": "17141819-bea9-41f1-81d2-530353cca91b",
    "소리": "94342976-be82-45f9-b2a3-1cfaa0342302",
    "중력": "1f220254-b38c-4909-8c40-f619df70f4d4",
    "힘": "3a72f280-bb86-4be0-a2b8-c2b83cde2e5d",
    "카메라": "9bb124cb-8a3c-41b9-ba78-718a79e46f89",
    "계산기": "662aaeec-458f-46a0-899d-6386acadab07",
    "계산": "7a40331b-84e2-42bc-819b-0cae429526ec",
    "음악": "45bf8177-6eff-48a8-9efa-e71d262c5be9",
    "로봇": "3d03470b-32cc-435d-88ea-514f630f1a63",
    "프로그램": "e8ddbe83-8661-431e-94bd-73759cf1c367",
    "컴퓨터": "a78c3a98-7f90-472b-ad86-55563d25d6db",
}


_DEVELOPMENT_FACTS = (
    {
        "fact_id": "capital-city",
        "question": "대한민국의 행정 중심이 되는 수도 도시는 어디야?",
        "positive": ("서울",),
        "context": ("한국", "수도"),
        "negative": ("달", "중력", "카메라"),
        "fact": "이 환경에서 한국의 수도 도시는 서울이다.",
        "question_style": "relational_composition",
    },
    {
        "fact_id": "natural-satellite",
        "question": "지구 주위를 공전하는 자연 위성은 무엇이야?",
        "positive": ("달",),
        "context": ("지구",),
        "negative": ("서울", "알고리즘", "음악"),
        "fact": "이 환경에서 지구의 자연 위성은 달이다.",
        "question_style": "relational_composition",
    },
    {
        "fact_id": "water-droplet-cloud",
        "question": "하늘에서 작은 물방울이 모여 보이는 것은 무엇이야?",
        "positive": ("구름",),
        "context": ("물",),
        "negative": ("컴퓨터", "중력", "계산기"),
        "fact": "이 환경에서 하늘의 작은 물방울 집합은 구름이다.",
        "question_style": "single_hop_definition",
    },
    {
        "fact_id": "minimum-cost-route",
        "question": "그래프에서 두 지점 사이의 비용 합이 가장 작은 경로를 무엇이라고 해?",
        "positive": ("최단경로",),
        "context": ("알고리즘", "문제"),
        "negative": ("서울", "카메라", "음악"),
        "fact": "이 환경에서 비용 합이 최소인 경로는 최단경로다.",
        "question_style": "single_hop_definition",
    },
    {
        "fact_id": "sound-sense",
        "question": "귀로 소리를 받아들이는 감각을 무엇이라고 해?",
        "positive": ("청각",),
        "context": ("소리",),
        "negative": ("달", "알고리즘", "계산기"),
        "fact": "이 환경에서 소리를 받아들이는 감각은 청각이다.",
        "question_style": "single_hop_definition",
    },
    {
        "fact_id": "earth-attraction",
        "question": "물체를 지구 쪽으로 끌어당기는 힘은 무엇이야?",
        "positive": ("중력",),
        "context": ("지구", "힘"),
        "negative": ("서울", "카메라", "음악"),
        "fact": "이 환경에서 물체를 지구 쪽으로 끄는 힘은 중력이다.",
        "question_style": "relational_composition",
    },
    {
        "fact_id": "scene-recording-device",
        "question": "빛을 받아 장면을 사진으로 기록하는 장치는 무엇이야?",
        "positive": ("카메라",),
        "context": (),
        "negative": ("중력", "달", "계산기"),
        "fact": "이 환경에서 빛을 받아 장면을 기록하는 장치는 카메라다.",
        "question_style": "single_hop_definition",
    },
    {
        "fact_id": "ordered-solution-procedure",
        "question": "문제를 해결하기 위해 순서대로 정의한 절차를 무엇이라고 해?",
        "positive": ("알고리즘",),
        "context": ("문제",),
        "negative": ("서울", "구름", "음악"),
        "fact": "이 환경에서 순서대로 정의한 해결 절차는 알고리즘이다.",
        "question_style": "single_hop_definition",
    },
    {
        "fact_id": "arithmetic-tool",
        "question": "숫자 연산을 수행하도록 만든 도구는 무엇이야?",
        "positive": ("계산기",),
        "context": ("계산",),
        "negative": ("달", "카메라", "청각"),
        "fact": "이 환경에서 숫자 연산 도구는 계산기다.",
        "question_style": "single_hop_definition",
    },
    {
        "fact_id": "organized-sound-art",
        "question": "리듬과 음을 조합해 듣는 예술을 무엇이라고 해?",
        "positive": ("음악",),
        "context": ("소리",),
        "negative": ("중력", "알고리즘", "서울"),
        "fact": "이 환경에서 리듬과 음을 조합한 예술은 음악이다.",
        "question_style": "single_hop_definition",
    },
    {
        "fact_id": "sensor-action-machine",
        "question": "센서로 환경을 관찰하고 정해진 동작을 수행하는 기계는 무엇이야?",
        "positive": ("로봇",),
        "context": (),
        "negative": ("달", "구름", "수도"),
        "fact": "이 환경에서 센서로 관찰하고 동작하는 기계는 로봇이다.",
        "question_style": "relational_composition",
    },
    {
        "fact_id": "computer-instruction-bundle",
        "question": "컴퓨터가 실행할 수 있도록 작성된 명령의 묶음은 무엇이야?",
        "positive": ("프로그램",),
        "context": ("컴퓨터",),
        "negative": ("서울", "중력", "음악"),
        "fact": "이 환경에서 컴퓨터용 명령 묶음은 프로그램이다.",
        "question_style": "relational_composition",
    },
)


def _clone(value: Mapping[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(value, ensure_ascii=False))


def _require_sha256(value: Any, field: str) -> str:
    raw = str(value or "")
    if not _SHA256_RE.fullmatch(raw):
        raise ValueError(f"{field} must be a lowercase SHA-256")
    return raw


def _zoned_timestamp(value: Any, field: str) -> str:
    raw = str(value or "").strip()
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} must include a timezone")
    return raw


def _question_sha256(question: str) -> str:
    return hashlib.sha256(question.encode("utf-8")).hexdigest()


def _vocabulary_by_id(vocabulary: Mapping[str, Any]) -> dict[str, str]:
    concepts = list(vocabulary.get("eligible_concepts") or [])
    result: dict[str, str] = {}
    for item in concepts:
        concept_id = str(item.get("concept_id") or "")
        concept_name = str(item.get("concept_name") or "")
        if not concept_id or not concept_name or concept_id in result:
            raise ValueError("candidate vocabulary requires unique concept identities")
        result[concept_id] = concept_name
    if not result:
        raise ValueError("candidate vocabulary is empty")
    return result


def _concept_records(
    names: Iterable[str],
    vocabulary_by_id: Mapping[str, str],
) -> list[dict[str, str]]:
    records = []
    for name in names:
        concept_id = _CONCEPTS[name]
        if vocabulary_by_id.get(concept_id) != name:
            raise ValueError(f"bound vocabulary does not contain exact concept: {name}")
        records.append({
            "concept_id": concept_id,
            "concept_name": name,
            "partition": graph_vocabulary_partition(concept_id),
        })
    return records


def build_development_sample_size_plan(
    lifecycle: Mapping[str, Any],
    *,
    created_at: str,
) -> dict[str, Any]:
    plan = {
        "sample_size_plan_version": SAMPLE_SIZE_PLAN_VERSION,
        "phase": PHASE,
        "role": "rolling_development",
        "status": "sample_size_plan_awaiting_user_review",
        "created_at": _zoned_timestamp(created_at, "created_at"),
        "cohort_lifecycle_contract_sha256": _require_sha256(
            lifecycle.get("cohort_lifecycle_contract_sha256"),
            "cohort_lifecycle_contract_sha256",
        ),
        "question_count": EXPECTED_QUESTION_COUNT,
        "positive_label_count": EXPECTED_QUESTION_COUNT,
        "explicit_negative_count_per_question": EXPLICIT_NEGATIVES_PER_QUESTION,
        "explicit_negative_label_count": (
            EXPECTED_QUESTION_COUNT * EXPLICIT_NEGATIVES_PER_QUESTION
        ),
        "target_partition_counts": EXPECTED_PARTITION_COUNTS,
        "candidate_scope": "full_frozen_graph_vocabulary",
        "unlabeled_graph_concept_policy": "ignore_never_assume_negative",
        "evaluation_metrics": [
            "macro_recall_at_8",
            "macro_ndcg_at_8",
            "macro_mrr",
        ],
        "usage": {
            "model_selection_allowed": True,
            "heldout_claim_allowed": False,
            "performance_claim_allowed": False,
            "inferential_claim_allowed": False,
            "descriptive_development_only": True,
        },
        "stop_rules": [
            "reject_if_question_or_label_review_is_incomplete",
            "reject_if_target_partition_counts_change",
            "reject_if_any_question_overlaps_anchor_by_hash",
            "reject_if_any_unlabeled_concept_is_coerced_to_negative",
            "reject_if_generator_uses_subject_model_or_live_graph_relations_as_truth",
        ],
    }
    plan["sample_size_plan_sha256"] = canonical_json_sha256(plan)
    return plan


def validate_development_sample_size_plan(
    payload: Mapping[str, Any],
    lifecycle: Mapping[str, Any],
) -> dict[str, Any]:
    normalized = _clone(payload)
    supplied = _require_sha256(
        normalized.get("sample_size_plan_sha256"),
        "sample_size_plan_sha256",
    )
    unhashed = _clone(normalized)
    unhashed.pop("sample_size_plan_sha256", None)
    if supplied != canonical_json_sha256(unhashed):
        raise ValueError("sample_size_plan_sha256 mismatch")
    expected = build_development_sample_size_plan(
        lifecycle,
        created_at=str(normalized.get("created_at") or ""),
    )
    if normalized != expected:
        raise ValueError("sample-size plan does not match the J1-R2 contract")
    return normalized


def build_development_generator_spec(
    lifecycle: Mapping[str, Any],
    vocabulary: Mapping[str, Any],
    sample_size_plan: Mapping[str, Any],
    *,
    implementation_sha256: str,
    created_at: str,
) -> dict[str, Any]:
    plan = validate_development_sample_size_plan(sample_size_plan, lifecycle)
    vocabulary_by_id = _vocabulary_by_id(vocabulary)
    vocabulary_sha256 = _require_sha256(
        vocabulary.get("candidate_vocabulary_sha256"),
        "candidate_vocabulary_sha256",
    )
    expected_vocabulary_sha256 = lifecycle["evaluation_epoch"][
        "candidate_vocabulary_sha256"
    ]
    if vocabulary_sha256 != expected_vocabulary_sha256:
        raise ValueError("candidate vocabulary does not match evaluation epoch")

    questions = []
    for order, fact in enumerate(_DEVELOPMENT_FACTS):
        positive = _concept_records(fact["positive"], vocabulary_by_id)
        context = _concept_records(fact["context"], vocabulary_by_id)
        negative = _concept_records(fact["negative"], vocabulary_by_id)
        question = str(fact["question"])
        questions.append({
            "order": order,
            "question_id": f"j1-r2-dev-0001-{order:02d}",
            "fact_id": fact["fact_id"],
            "question": question,
            "question_sha256": _question_sha256(question),
            "question_style": fact["question_style"],
            "closed_world_fact": fact["fact"],
            "closed_world_fact_sha256": canonical_json_sha256({
                "fact_id": fact["fact_id"],
                "fact": fact["fact"],
                "positive_concepts": positive,
                "context_concepts": context,
            }),
            "positive_concepts": positive,
            "context_concepts_unscored": context,
            "explicit_negative_concepts": negative,
            "all_other_graph_concepts": "unlabeled",
        })

    spec = {
        "generator_spec_version": GENERATOR_SPEC_VERSION,
        "phase": PHASE,
        "role": "rolling_development",
        "status": "generator_spec_awaiting_user_review",
        "generator_id": GENERATOR_ID,
        "created_at": _zoned_timestamp(created_at, "created_at"),
        "cohort_lifecycle_contract_sha256": lifecycle[
            "cohort_lifecycle_contract_sha256"
        ],
        "candidate_vocabulary_sha256": vocabulary_sha256,
        "sample_size_plan_sha256": plan["sample_size_plan_sha256"],
        "implementation_sha256": _require_sha256(
            implementation_sha256, "implementation_sha256"
        ),
        "source_contract": {
            "source_type": "deterministic_synthetic_environment",
            "environment_id": "j1-r2-closed-world-korean-relations-v1",
            "subject_model_generated_questions": False,
            "subject_model_grades_itself": False,
            "live_graph_relations_used_as_ground_truth": False,
            "external_api_used": False,
            "personal_user_memory_allowed": False,
            "independent_ground_truth_required": True,
        },
        "label_contract": {
            "positive_definition": "explicit_answer_bearing_concept_only",
            "negative_definition": "explicit_closed_world_decoy_only",
            "context_concepts_are_scored": False,
            "unlabeled_graph_concept_policy": "ignore_never_assume_negative",
            "automatic_random_negative_labeling_allowed": False,
        },
        "generation_contract": {
            "algorithm": "ordered_fixed_fact_templates_v1",
            "deterministic": True,
            "question_text_fixed_before_baseline_output": True,
            "question_count": len(questions),
            "plaintext_allowed_for_development_only": True,
        },
        "questions": questions,
        "review_required": True,
        "review_status": "awaiting_user_review",
        "database_writes": False,
        "learning_enabled": False,
        "execution_gate": False,
        "heldout_gate": False,
        "performance_claim_gate": False,
        "production_promotion_gate": False,
    }
    spec["generator_spec_sha256"] = canonical_json_sha256(spec)
    return spec


def validate_development_generator_spec(
    payload: Mapping[str, Any],
    lifecycle: Mapping[str, Any],
    vocabulary: Mapping[str, Any],
    sample_size_plan: Mapping[str, Any],
    *,
    legacy_question_hashes: Iterable[str],
) -> dict[str, Any]:
    normalized = _clone(payload)
    supplied = _require_sha256(
        normalized.get("generator_spec_sha256"), "generator_spec_sha256"
    )
    unhashed = _clone(normalized)
    unhashed.pop("generator_spec_sha256", None)
    if supplied != canonical_json_sha256(unhashed):
        raise ValueError("generator_spec_sha256 mismatch")
    expected = build_development_generator_spec(
        lifecycle,
        vocabulary,
        sample_size_plan,
        implementation_sha256=str(normalized.get("implementation_sha256") or ""),
        created_at=str(normalized.get("created_at") or ""),
    )
    if normalized != expected:
        raise ValueError("generator spec does not match deterministic implementation")

    questions = list(normalized["questions"])
    hashes = [str(item["question_sha256"]) for item in questions]
    if len(hashes) != EXPECTED_QUESTION_COUNT or len(hashes) != len(set(hashes)):
        raise ValueError("development questions must be complete and unique")
    if set(hashes) & {str(value) for value in legacy_question_hashes}:
        raise ValueError("development question hash overlaps anchor")

    partitions: Counter[str] = Counter()
    for item in questions:
        positive_ids = {
            str(row["concept_id"]) for row in item["positive_concepts"]
        }
        negative_ids = {
            str(row["concept_id"]) for row in item["explicit_negative_concepts"]
        }
        context_ids = {
            str(row["concept_id"]) for row in item["context_concepts_unscored"]
        }
        if len(positive_ids) != 1:
            raise ValueError("each development question requires one positive")
        if len(negative_ids) != EXPLICIT_NEGATIVES_PER_QUESTION:
            raise ValueError("development question explicit-negative count mismatch")
        if positive_ids & negative_ids or context_ids & negative_ids:
            raise ValueError("positive/context concepts cannot be explicit negatives")
        positive = item["positive_concepts"][0]
        partitions[str(positive["partition"])] += 1
        if positive["partition"] == "lockbox_challenge_pool":
            raise ValueError("development questions cannot consume lockbox targets")
        if item.get("all_other_graph_concepts") != "unlabeled":
            raise ValueError("unlisted graph concepts must remain unlabeled")
    if dict(partitions) != {
        key: count for key, count in EXPECTED_PARTITION_COUNTS.items() if count
    }:
        raise ValueError("development target partition counts do not match plan")
    return normalized


def build_development_review_packet(
    spec: Mapping[str, Any],
    sample_size_plan: Mapping[str, Any],
    *,
    created_at: str,
) -> dict[str, Any]:
    plan_hash = _require_sha256(
        sample_size_plan.get("sample_size_plan_sha256"),
        "sample_size_plan_sha256",
    )
    if spec.get("sample_size_plan_sha256") != plan_hash:
        raise ValueError("generator spec and sample-size plan are not bound")
    rows = []
    for item in spec["questions"]:
        rows.append({
            "order": item["order"],
            "question_id": item["question_id"],
            "question": item["question"],
            "question_sha256": item["question_sha256"],
            "closed_world_fact": item["closed_world_fact"],
            "positive_concepts": item["positive_concepts"],
            "context_concepts_unscored": item["context_concepts_unscored"],
            "explicit_negative_concepts": item["explicit_negative_concepts"],
            "review_decision": "pending",
        })
    packet = {
        "review_packet_version": REVIEW_PACKET_VERSION,
        "phase": PHASE,
        "role": "rolling_development",
        "status": "development_question_review_pending",
        "created_at": _zoned_timestamp(created_at, "created_at"),
        "generator_spec_sha256": _require_sha256(
            spec.get("generator_spec_sha256"), "generator_spec_sha256"
        ),
        "sample_size_plan_sha256": plan_hash,
        "implementation_sha256": _require_sha256(
            spec.get("implementation_sha256"), "implementation_sha256"
        ),
        "question_count": len(rows),
        "positive_label_count": sum(
            len(item["positive_concepts"]) for item in rows
        ),
        "explicit_negative_label_count": sum(
            len(item["explicit_negative_concepts"]) for item in rows
        ),
        "unlabeled_graph_concepts_are_negative": False,
        "questions": rows,
        "reviewer_role_required": "user",
        "review_gate": False,
        "materialization_gate": False,
        "database_writes": False,
        "learning_enabled": False,
        "heldout_gate": False,
        "performance_claim_gate": False,
        "production_promotion_gate": False,
        "next_step": "obtain_explicit_user_review_decisions_for_all_questions",
    }
    packet["review_packet_sha256"] = canonical_json_sha256(packet)
    return packet


def validate_development_review_packet(
    payload: Mapping[str, Any],
    spec: Mapping[str, Any],
    sample_size_plan: Mapping[str, Any],
) -> dict[str, Any]:
    normalized = _clone(payload)
    supplied = _require_sha256(
        normalized.get("review_packet_sha256"), "review_packet_sha256"
    )
    unhashed = _clone(normalized)
    unhashed.pop("review_packet_sha256", None)
    if supplied != canonical_json_sha256(unhashed):
        raise ValueError("review_packet_sha256 mismatch")
    expected = build_development_review_packet(
        spec,
        sample_size_plan,
        created_at=str(normalized.get("created_at") or ""),
    )
    if normalized != expected:
        raise ValueError("review packet does not match generator inputs")
    return normalized


def validate_development_review_decisions(
    payload: Mapping[str, Any],
    review_packet: Mapping[str, Any],
) -> dict[str, Any]:
    normalized = _clone(payload)
    if normalized.get("review_decisions_version") != REVIEW_DECISIONS_VERSION:
        raise ValueError("unsupported review_decisions_version")
    if normalized.get("phase") != PHASE:
        raise ValueError("review decisions phase must be J1-R2")
    if normalized.get("review_packet_sha256") != review_packet.get(
        "review_packet_sha256"
    ):
        raise ValueError("review decisions are not bound to review packet")
    if normalized.get("reviewer_role") != "user":
        raise ValueError("development review requires reviewer_role=user")
    _zoned_timestamp(normalized.get("reviewed_at"), "reviewed_at")
    supplied = _require_sha256(
        normalized.get("review_decisions_sha256"), "review_decisions_sha256"
    )
    unhashed = _clone(normalized)
    unhashed.pop("review_decisions_sha256", None)
    if supplied != canonical_json_sha256(unhashed):
        raise ValueError("review_decisions_sha256 mismatch")

    expected_ids = [str(item["question_id"]) for item in review_packet["questions"]]
    decisions = list(normalized.get("decisions") or [])
    decision_ids = [str(item.get("question_id") or "") for item in decisions]
    if decision_ids != expected_ids:
        raise ValueError("review decisions must cover every question in order")
    if any(item.get("decision") != "approved" for item in decisions):
        raise ValueError("all planned development questions require explicit approval")
    if normalized.get("overall_decision") != "approved":
        raise ValueError("overall development review must be approved")
    return normalized


def build_reviewed_development_label_pack(
    spec: Mapping[str, Any],
    review_packet: Mapping[str, Any],
    review_decisions: Mapping[str, Any],
    *,
    created_at: str,
) -> dict[str, Any]:
    decisions = validate_development_review_decisions(
        review_decisions, review_packet
    )
    entries = []
    for item in spec["questions"]:
        labels = []
        for concept in item["positive_concepts"]:
            labels.append({
                **concept,
                "decision": "approved",
                "label": 1,
                "provenance": "deterministic_closed_world_fact",
            })
        for concept in item["explicit_negative_concepts"]:
            labels.append({
                **concept,
                "decision": "rejected",
                "label": 0,
                "provenance": "explicit_closed_world_decoy",
            })
        entries.append({
            "question_id": item["question_id"],
            "question_sha256": item["question_sha256"],
            "labels": labels,
            "context_concepts_unscored": item["context_concepts_unscored"],
        })
    pack = {
        "development_label_pack_version": DEVELOPMENT_LABEL_PACK_VERSION,
        "phase": PHASE,
        "role": "rolling_development",
        "status": "user_reviewed_development_labels",
        "created_at": _zoned_timestamp(created_at, "created_at"),
        "generator_spec_sha256": spec["generator_spec_sha256"],
        "review_packet_sha256": review_packet["review_packet_sha256"],
        "review_decisions_sha256": decisions["review_decisions_sha256"],
        "question_count": len(entries),
        "positive_label_count": EXPECTED_QUESTION_COUNT,
        "explicit_negative_label_count": (
            EXPECTED_QUESTION_COUNT * EXPLICIT_NEGATIVES_PER_QUESTION
        ),
        "unlabeled_graph_concept_policy": "ignore_never_assume_negative",
        "entries": entries,
        "database_writes": False,
        "learning_enabled": False,
        "heldout_gate": False,
        "performance_claim_gate": False,
        "production_promotion_gate": False,
    }
    pack["development_label_pack_sha256"] = canonical_json_sha256(pack)
    return pack


def materialize_reviewed_development_manifest(
    lifecycle: Mapping[str, Any],
    planned_manifest: Mapping[str, Any],
    spec: Mapping[str, Any],
    sample_size_plan: Mapping[str, Any],
    review_packet: Mapping[str, Any],
    review_decisions: Mapping[str, Any],
    label_pack: Mapping[str, Any],
    *,
    created_at: str,
) -> dict[str, Any]:
    planned = validate_cohort_manifest(planned_manifest, lifecycle)
    if planned["role"] != "rolling_development":
        raise ValueError("planned manifest must be rolling development")
    decisions = validate_development_review_decisions(
        review_decisions, review_packet
    )
    label_hash = _require_sha256(
        label_pack.get("development_label_pack_sha256"),
        "development_label_pack_sha256",
    )
    unhashed_labels = _clone(label_pack)
    unhashed_labels.pop("development_label_pack_sha256", None)
    if label_hash != canonical_json_sha256(unhashed_labels):
        raise ValueError("development_label_pack_sha256 mismatch")
    expected_labels = build_reviewed_development_label_pack(
        spec,
        review_packet,
        decisions,
        created_at=str(label_pack.get("created_at") or ""),
    )
    if label_pack != expected_labels:
        raise ValueError("development label pack does not match reviewed generator")

    question_hashes = sorted(
        str(item["question_sha256"]) for item in spec["questions"]
    )
    manifest = _clone(planned)
    manifest.update({
        "status": "materialized_user_reviewed_development_not_heldout",
        "lifecycle_state": "active",
        "review_status": "user_reviewed",
        "created_at": _zoned_timestamp(created_at, "created_at"),
        "generator": {
            **manifest["generator"],
            "implementation_sha256": spec["implementation_sha256"],
            "specification_sha256": spec["generator_spec_sha256"],
            "sample_size_plan_sha256": sample_size_plan[
                "sample_size_plan_sha256"
            ],
        },
        "materialization": {
            "materialized": True,
            "question_count": len(question_hashes),
            "question_hashes": question_hashes,
            "question_set_sha256": canonical_json_sha256(question_hashes),
            "plaintext_questions_in_repository": True,
        },
        "development_dataset": {
            "review_packet_sha256": review_packet["review_packet_sha256"],
            "review_decisions_sha256": decisions["review_decisions_sha256"],
            "development_label_pack_sha256": label_hash,
            "unlabeled_graph_concept_policy": "ignore_never_assume_negative",
        },
        "execution_gate": True,
        "block_reasons": [],
        "next_step": "freeze_one_time_lockbox_generator_before_lexical_baseline",
    })
    return validate_cohort_manifest(seal_cohort_manifest(manifest), lifecycle)
