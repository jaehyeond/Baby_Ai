"""B5.7 user-in-the-loop PendingQuestion train pilot.

The discovery and manifest steps are read-only.  ``create`` is the only mode
that writes to Neo4j, through the B5.6 opt-in API.  Predictions are never
printed or written to the manifest before the user answers.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

import httpx


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from neural.baby.pending_question_outcome import (
    build_pending_question_cue_terms,
    build_pending_question_terms,
    parse_pending_question_action_contract,
)


PILOT_NAME = "b5_7_pending_question_train_a_20260716"
PILOT_SPLIT = "train"
MIN_QUESTION_COUNT = 6
DEFAULT_MANIFEST = (
    PROJECT_ROOT
    / "scripts"
    / "research"
    / "manifests"
    / "b5_7_pending_question_train_a_20260716.json"
)
DEFAULT_ARTIFACT = (
    PROJECT_ROOT
    / "claudedocs"
    / "research"
    / "b5_7_pending_question_train_a_20260716.json"
)
DEFAULT_ANSWERS = (
    PROJECT_ROOT
    / "scripts"
    / "research"
    / "inputs"
    / "b5_7_pending_question_train_a_20260716_answers.json"
)


CANDIDATE_QUERY = """
MATCH (cl:CuriosityLog)
WHERE cl.status = 'pending'
  AND cl.id IS NOT NULL
  AND cl.query IS NOT NULL
  AND trim(toString(cl.query)) <> ''
  AND NOT (cl)-[:GENERATED]->(:PendingQuestion)
RETURN cl.id AS curiosity_log_id,
       toString(cl.query) AS curiosity_query,
       coalesce(cl.source, 'unknown') AS curiosity_source,
       coalesce(cl.query_type, 'unknown') AS query_type,
       coalesce(cl.priority, 0.0) AS priority,
       toString(cl.created_at) AS created_at
ORDER BY CASE WHEN cl.source = 'learning_progress' THEN 0 ELSE 1 END,
         priority DESC, created_at DESC
LIMIT $limit
"""


MANIFEST_QUESTION_AUDIT_QUERY = """
UNWIND $curiosity_log_ids AS curiosity_log_id
MATCH (cl:CuriosityLog {id: curiosity_log_id})-[generated:GENERATED]->(pq:PendingQuestion)
WHERE pq.question_outcome_contract_sha256 = $contract_sha256
RETURN curiosity_log_id,
       pq.id AS question_id,
       pq.question AS question,
       pq.status AS status,
       toString(pq.prediction_captured_at) AS prediction_captured_at,
       toString(pq.asked_at) AS asked_at,
       size(coalesce(pq.curiosity_cue_ids, [])) AS cue_count,
       size(coalesce(pq.predicted_concept_ids, [])) AS prediction_count,
       size(coalesce(pq.external_outcome_concept_ids, [])) AS outcome_count,
       pq.answer IS NOT NULL AS has_answer,
       pq.question_outcome_scoring_mode AS scoring_mode,
       pq.question_outcome_split AS split,
       generated.policy_action_key AS policy_action_key
ORDER BY curiosity_log_id
"""


ANSWER_PREFLIGHT_QUERY = """
UNWIND $answers AS item
MATCH (pq:PendingQuestion {id: item.question_id})
WHERE pq.question_outcome_contract_sha256 = $contract_sha256
UNWIND item.outcome_terms AS outcome_term
OPTIONAL MATCH (concept:Concept)
WHERE concept.name IS NOT NULL
  AND toLower(trim(toString(concept.name))) = outcome_term
  AND concept.created_at IS NOT NULL
  AND datetime(toString(concept.created_at)) <= datetime(toString(pq.prediction_captured_at))
  AND NOT concept.id IN coalesce(pq.curiosity_cue_ids, [])
WITH item, pq,
     [concept IN collect(DISTINCT concept)
      WHERE concept IS NOT NULL |
      {id: concept.id, name: concept.name}] AS outcome_concepts
RETURN item.order AS order,
       pq.id AS question_id,
       pq.status AS status,
       pq.answer AS existing_answer,
       toString(pq.prediction_captured_at) AS prediction_captured_at,
       toString(pq.asked_at) AS asked_at,
       size(coalesce(pq.curiosity_cue_ids, [])) AS cue_count,
       outcome_concepts
ORDER BY order
"""


POST_ANSWER_EVALUATION_QUERY = """
UNWIND $curiosity_log_ids AS curiosity_log_id
MATCH (cl:CuriosityLog {id: curiosity_log_id})-[generated:GENERATED]->(pq:PendingQuestion)
WHERE pq.question_outcome_contract_sha256 = $contract_sha256
RETURN curiosity_log_id,
       pq.id AS question_id,
       pq.status AS status,
       pq.answer IS NOT NULL AS has_answer,
       toString(pq.prediction_captured_at) AS prediction_captured_at,
       toString(pq.asked_at) AS asked_at,
       toString(pq.answered_at) AS answered_at,
       coalesce(pq.curiosity_cue_ids, []) AS cue_ids,
       coalesce(pq.predicted_concept_ids, []) AS predicted_ids,
       coalesce(pq.external_outcome_concept_ids, []) AS outcome_ids,
       pq.question_outcome_scoring_mode AS scoring_mode,
       pq.question_outcome_split AS split,
       generated.policy_action_key AS policy_action_key
ORDER BY curiosity_log_id
"""


CURIOSITY_STATE_QUERY = """
UNWIND $curiosity_log_ids AS curiosity_log_id
MATCH (cl:CuriosityLog {id: curiosity_log_id})
RETURN curiosity_log_id,
       cl.status AS status,
       cl.prediction_error AS prediction_error,
       cl.learning_progress AS learning_progress,
       cl.integration_priority AS integration_priority,
       toString(cl.updated_at) AS updated_at
ORDER BY curiosity_log_id
"""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _has_final_consonant(text: str) -> bool:
    for char in reversed(text.strip()):
        code = ord(char)
        if 0xAC00 <= code <= 0xD7A3:
            return (code - 0xAC00) % 28 != 0
        if char.isalnum():
            return False
    return False


def question_from_curiosity_query(query: str) -> str:
    """Convert an existing policy query into a deterministic user question."""

    topic = " ".join(str(query or "").strip().split())
    if not topic:
        raise ValueError("curiosity query must not be empty")
    if len(topic) > 160:
        raise ValueError("curiosity query must be at most 160 characters")
    topic = topic.rstrip(".?! ")
    if topic.endswith("더 알아보자"):
        return f"{topic[:-len('더 알아보자')]}설명해줘"
    if topic.endswith(("설명해줘", "알려줘", "말해줘")):
        return topic
    particle = "을" if _has_final_consonant(topic) else "를"
    return f"{topic}{particle} 설명해줘"


def _contract_payload(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "manifest_version": manifest.get("manifest_version"),
        "pilot_name": manifest.get("pilot_name"),
        "split": manifest.get("split"),
        "questions": [
            {
                "order": item.get("order"),
                "curiosity_log_id": item.get("curiosity_log_id"),
                "curiosity_source": item.get("curiosity_source"),
                "question": item.get("question"),
            }
            for item in manifest.get("questions", [])
        ],
    }


def contract_sha256(manifest: dict[str, Any]) -> str:
    rendered = json.dumps(
        _contract_payload(manifest),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()


def build_manifest(candidates: Iterable[dict[str, Any]]) -> dict[str, Any]:
    eligible = [dict(item) for item in candidates if item.get("eligible")]
    if len(eligible) < MIN_QUESTION_COUNT:
        raise ValueError(
            f"need at least {MIN_QUESTION_COUNT} eligible CuriosityLog actions; "
            f"found {len(eligible)}"
        )
    selected = eligible[:MIN_QUESTION_COUNT]
    manifest = {
        "manifest_version": 1,
        "phase": "B5.7",
        "pilot_name": PILOT_NAME,
        "split": PILOT_SPLIT,
        "question_count": MIN_QUESTION_COUNT,
        "created_at": _now_iso(),
        "selection_rule": (
            "unused pending CuriosityLog; learning_progress first, then priority/recency; "
            "known cue and non-empty prediction required; prediction identities sealed"
        ),
        "questions": [
            {
                "order": index,
                "curiosity_log_id": item["curiosity_log_id"],
                "curiosity_source": item["curiosity_source"],
                "query_type": item["query_type"],
                "question": item["question"],
                "preflight_cue_count": item["cue_count"],
                "preflight_prediction_count": item["prediction_count"],
            }
            for index, item in enumerate(selected)
        ],
    }
    manifest["contract_sha256"] = contract_sha256(manifest)
    return manifest


def validate_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    raw = dict(manifest)
    if raw.get("manifest_version") != 1:
        raise ValueError("manifest_version must be 1")
    if raw.get("pilot_name") != PILOT_NAME:
        raise ValueError(f"pilot_name must be {PILOT_NAME}")
    if raw.get("split") != PILOT_SPLIT:
        raise ValueError("B5.7 pilot split must be train")
    questions = [dict(item) for item in raw.get("questions", [])]
    if len(questions) != MIN_QUESTION_COUNT:
        raise ValueError(f"manifest must contain {MIN_QUESTION_COUNT} questions")
    if [item.get("order") for item in questions] != list(range(MIN_QUESTION_COUNT)):
        raise ValueError("manifest question order must be contiguous from zero")
    curiosity_ids = [str(item.get("curiosity_log_id") or "").strip() for item in questions]
    question_texts = [str(item.get("question") or "").strip() for item in questions]
    if any(not item for item in curiosity_ids) or len(set(curiosity_ids)) != len(curiosity_ids):
        raise ValueError("manifest CuriosityLog IDs must be non-empty and unique")
    if any(not item for item in question_texts) or len(set(question_texts)) != len(question_texts):
        raise ValueError("manifest questions must be non-empty and unique")
    expected_hash = contract_sha256(raw)
    if raw.get("contract_sha256") != expected_hash:
        raise ValueError("manifest contract_sha256 does not match immutable fields")
    return raw


def build_create_payload(entry: dict[str, Any], contract_hash: str) -> dict[str, Any]:
    return {
        "question": entry["question"],
        "source": "b5_7_curiosity_train",
        "curiosity_log_id": entry["curiosity_log_id"],
        "question_outcome_evaluation": True,
        "question_outcome_split": PILOT_SPLIT,
        "question_outcome_contract_sha256": contract_hash,
    }


def validate_answer_pack(
    manifest: dict[str, Any],
    answer_pack: dict[str, Any],
) -> dict[str, Any]:
    """Bind six explicitly approved answers to the sealed question contract."""

    validated_manifest = validate_manifest(manifest)
    raw = dict(answer_pack)
    if raw.get("answer_pack_version") != 1:
        raise ValueError("answer_pack_version must be 1")
    if raw.get("pilot_name") != PILOT_NAME:
        raise ValueError(f"answer pilot_name must be {PILOT_NAME}")
    if raw.get("contract_sha256") != validated_manifest["contract_sha256"]:
        raise ValueError("answer contract_sha256 does not match the manifest")
    if raw.get("answer_role") != "user_final":
        raise ValueError("answer_role must be user_final")
    if raw.get("answer_provenance") != "user_reviewed_adopted":
        raise ValueError("answer_provenance must be user_reviewed_adopted")
    if not str(raw.get("approved_at") or "").strip():
        raise ValueError("approved_at must not be empty")

    answers = [dict(item) for item in raw.get("answers", [])]
    if len(answers) != MIN_QUESTION_COUNT:
        raise ValueError(f"answer pack must contain {MIN_QUESTION_COUNT} answers")
    if [item.get("order") for item in answers] != list(range(MIN_QUESTION_COUNT)):
        raise ValueError("answer order must be contiguous from zero")

    question_ids: list[str] = []
    for manifest_entry, answer_entry in zip(
        validated_manifest["questions"], answers
    ):
        if answer_entry.get("curiosity_log_id") != manifest_entry["curiosity_log_id"]:
            raise ValueError(
                f"answer curiosity_log_id mismatch at order {manifest_entry['order']}"
            )
        question_id = str(answer_entry.get("question_id") or "").strip()
        answer = str(answer_entry.get("answer") or "").strip()
        confidence = answer_entry.get("answer_confidence", 1.0)
        if not question_id:
            raise ValueError("answer question_id must not be empty")
        if not answer:
            raise ValueError("answer text must not be empty")
        if not isinstance(confidence, (int, float)) or not 0.0 <= confidence <= 1.0:
            raise ValueError("answer_confidence must be between 0 and 1")
        question_ids.append(question_id)
    if len(set(question_ids)) != MIN_QUESTION_COUNT:
        raise ValueError("answer question IDs must be unique")
    return raw


def build_answer_payload(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "answer": str(entry["answer"]).strip(),
        "answer_confidence": float(entry.get("answer_confidence", 1.0)),
    }


def evaluate_completed_answers(
    manifest: dict[str, Any],
    records: Iterable[dict[str, Any]],
    *,
    answer_provenance: str,
    learning_state_unchanged: bool,
    reviewed_outcome_ids_by_order: Mapping[int, Iterable[str]] | None = None,
) -> dict[str, Any]:
    """Evaluate only the completed train contract; never promote from train data."""

    validated = validate_manifest(manifest)
    by_curiosity = {
        str(item.get("curiosity_log_id")): dict(item) for item in records
    }
    question_results: list[dict[str, Any]] = []
    unique_outcomes: set[str] = set()
    all_contracts_valid = True
    all_content_labels_valid = reviewed_outcome_ids_by_order is not None
    total_hits = 0

    for entry in validated["questions"]:
        record = by_curiosity.get(entry["curiosity_log_id"], {})
        predicted_ids = {
            str(item) for item in record.get("predicted_ids", []) if item
        }
        outcome_ids = {
            str(item) for item in record.get("outcome_ids", []) if item
        }
        unique_outcomes.update(outcome_ids)
        matched_count = len(predicted_ids & outcome_ids)
        total_hits += matched_count
        prediction_at = str(record.get("prediction_captured_at") or "")
        asked_at = str(record.get("asked_at") or "")
        answered_at = str(record.get("answered_at") or "")
        ordered = bool(
            prediction_at and asked_at and answered_at
            and prediction_at <= asked_at <= answered_at
        )
        valid = bool(
            record
            and record.get("status") == "answered"
            and record.get("has_answer")
            and record.get("split") == PILOT_SPLIT
            and record.get("scoring_mode") == "external_recorded"
            and record.get("policy_action_key")
            and record.get("cue_ids")
            and predicted_ids
            and outcome_ids
            and ordered
        )
        all_contracts_valid = all_contracts_valid and valid
        reviewed_outcome_ids = {
            str(item) for item in (
                (reviewed_outcome_ids_by_order or {}).get(entry["order"], [])
            ) if item
        }
        content_valid = bool(
            reviewed_outcome_ids
            and reviewed_outcome_ids <= outcome_ids
        )
        all_content_labels_valid = all_content_labels_valid and content_valid
        question_results.append({
            "order": entry["order"],
            "question_id": record.get("question_id"),
            "contract_valid": valid,
            "reviewed_outcome_content_valid": content_valid,
            "prediction_count": len(predicted_ids),
            "outcome_count": len(outcome_ids),
            "matched_prediction_count": matched_count,
            "prediction_recall_error": (
                round(1.0 - matched_count / len(outcome_ids), 6)
                if outcome_ids else None
            ),
        })

    structural_contract_gate = bool(
        len(by_curiosity) == MIN_QUESTION_COUNT
        and all_contracts_valid
        and len(unique_outcomes) >= 4
    )
    outcome_content_validity_gate = bool(
        structural_contract_gate and all_content_labels_valid
    )
    target_validity_gate = bool(
        structural_contract_gate and outcome_content_validity_gate
    )
    exploratory_train_overlap_signal = bool(
        target_validity_gate and total_hits > 0
    )
    return {
        "structural_contract_gate": structural_contract_gate,
        "outcome_content_validity_gate": outcome_content_validity_gate,
        "target_validity_gate": target_validity_gate,
        "target_validity_reason": (
            None if target_validity_gate
            else (
                "structural_contract_invalid"
                if not structural_contract_gate
                else (
                    "reviewed_outcome_labels_not_supplied"
                    if reviewed_outcome_ids_by_order is None
                    else "reviewed_outcome_labels_invalid"
                )
            )
        ),
        "target_validity_scope": (
            "structural_contract_plus_independently_reviewed_outcome_ids"
        ),
        "target_validity_criteria": {
            "six_action_linked_ordered_answers": (
                len(by_curiosity) == MIN_QUESTION_COUNT and all_contracts_valid
            ),
            "minimum_four_unique_outcomes": len(unique_outcomes) >= 4,
            "reviewed_outcome_ids_for_every_answer": all_content_labels_valid,
            "learning_state_unchanged": learning_state_unchanged,
        },
        "answer_provenance": answer_provenance,
        "question_count": len(question_results),
        "unique_outcome_count": len(unique_outcomes),
        "total_prediction_hit_count": total_hits,
        "exploratory_train_overlap_signal": exploratory_train_overlap_signal,
        "predictor_frozen": False,
        "heldout_collection_started": False,
        "evaluation_readiness_gate": False,
        "production_promotion_gate": False,
        "questions": question_results,
    }


async def discover_candidates(limit: int = 100) -> list[dict[str, Any]]:
    """Read unused policy actions and preflight counts without exposing predictions."""

    from neural.baby.neo4j_db import (
        BrainDatabase,
        _DB_NAME,
        close_driver,
        get_driver,
        init_driver,
    )

    await init_driver()
    try:
        async with get_driver().session(database=_DB_NAME) as session:
            result = await session.run(CANDIDATE_QUERY, limit=max(MIN_QUESTION_COUNT, limit))
            records = [dict(item) async for item in result]

        db = BrainDatabase()
        candidates: list[dict[str, Any]] = []
        for record in records:
            try:
                question = question_from_curiosity_query(record["curiosity_query"])
                cue_terms = build_pending_question_cue_terms(question)
                snapshot = await db.prepare_curiosity_prediction(
                    question,
                    cue_terms=cue_terms,
                )
                cue_count = len((snapshot or {}).get("cue_concepts") or [])
                prediction_count = len((snapshot or {}).get("predicted_concepts") or [])
                reason = None if cue_count > 0 and prediction_count > 0 else (
                    "no_known_cue" if cue_count == 0 else "no_graph_prediction"
                )
            except ValueError as exc:
                question = None
                cue_count = 0
                prediction_count = 0
                reason = str(exc)
            candidates.append({
                **record,
                "question": question,
                "cue_count": cue_count,
                "prediction_count": prediction_count,
                "eligible": reason is None,
                "rejection_reason": reason,
            })
        return candidates
    finally:
        await close_driver()


async def audit_manifest(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    from neural.baby.neo4j_db import (
        _DB_NAME,
        close_driver,
        get_driver,
        init_driver,
    )

    validated = validate_manifest(manifest)
    await init_driver()
    try:
        async with get_driver().session(database=_DB_NAME) as session:
            result = await session.run(
                MANIFEST_QUESTION_AUDIT_QUERY,
                curiosity_log_ids=[
                    item["curiosity_log_id"] for item in validated["questions"]
                ],
                contract_sha256=validated["contract_sha256"],
            )
            return [dict(item) async for item in result]
    finally:
        await close_driver()


async def preflight_answers(
    manifest: dict[str, Any],
    answer_pack: dict[str, Any],
) -> list[dict[str, Any]]:
    """Resolve every answer against pre-prediction non-cue concepts, read-only."""

    from neural.baby.neo4j_db import (
        _DB_NAME,
        close_driver,
        get_driver,
        init_driver,
    )

    validated_manifest = validate_manifest(manifest)
    validated_answers = validate_answer_pack(validated_manifest, answer_pack)
    answer_inputs = [
        {
            "order": item["order"],
            "question_id": item["question_id"],
            "outcome_terms": build_pending_question_terms(item["answer"]),
        }
        for item in validated_answers["answers"]
    ]
    if any(not item["outcome_terms"] for item in answer_inputs):
        raise RuntimeError("answer preflight found an answer without outcome terms")

    await init_driver()
    try:
        async with get_driver().session(database=_DB_NAME) as session:
            result = await session.run(
                ANSWER_PREFLIGHT_QUERY,
                answers=answer_inputs,
                contract_sha256=validated_manifest["contract_sha256"],
            )
            records = [dict(item) async for item in result]
    finally:
        await close_driver()

    if len(records) != MIN_QUESTION_COUNT:
        raise RuntimeError(
            f"answer preflight expected {MIN_QUESTION_COUNT} questions; "
            f"found {len(records)}"
        )
    expected_by_order = {
        item["order"]: item for item in validated_answers["answers"]
    }
    invalid: list[str] = []
    sanitized: list[dict[str, Any]] = []
    for record in records:
        expected = expected_by_order[record["order"]]
        status = record.get("status")
        existing_answer = record.get("existing_answer")
        state_valid = (
            status == "pending" and existing_answer is None
        ) or (
            status == "answered" and existing_answer == expected["answer"]
        )
        prediction_at = str(record.get("prediction_captured_at") or "")
        asked_at = str(record.get("asked_at") or "")
        outcome_concepts = [
            dict(item) for item in (record.get("outcome_concepts") or [])
            if item and item.get("id")
        ]
        valid = bool(
            state_valid
            and prediction_at
            and asked_at
            and prediction_at <= asked_at
            and int(record.get("cue_count") or 0) > 0
            and outcome_concepts
        )
        if not valid:
            invalid.append(str(record.get("question_id") or record.get("order")))
        sanitized.append({
            "order": record["order"],
            "question_id": record["question_id"],
            "status": status,
            "prediction_before_question": bool(
                prediction_at and asked_at and prediction_at <= asked_at
            ),
            "outcome_count": len(outcome_concepts),
            "outcome_names": [item.get("name") for item in outcome_concepts],
            "valid": valid,
        })
    if invalid:
        raise RuntimeError(
            "answer preflight rejected question IDs: " + ", ".join(invalid)
        )
    return sanitized


async def _fetch_post_answer_records(
    manifest: dict[str, Any],
) -> list[dict[str, Any]]:
    from neural.baby.neo4j_db import (
        _DB_NAME,
        close_driver,
        get_driver,
        init_driver,
    )

    validated = validate_manifest(manifest)
    await init_driver()
    try:
        async with get_driver().session(database=_DB_NAME) as session:
            result = await session.run(
                POST_ANSWER_EVALUATION_QUERY,
                curiosity_log_ids=[
                    item["curiosity_log_id"] for item in validated["questions"]
                ],
                contract_sha256=validated["contract_sha256"],
            )
            return [dict(item) async for item in result]
    finally:
        await close_driver()


async def _fetch_curiosity_state(
    manifest: dict[str, Any],
) -> list[dict[str, Any]]:
    from neural.baby.neo4j_db import (
        _DB_NAME,
        close_driver,
        get_driver,
        init_driver,
    )

    validated = validate_manifest(manifest)
    await init_driver()
    try:
        async with get_driver().session(database=_DB_NAME) as session:
            result = await session.run(
                CURIOSITY_STATE_QUERY,
                curiosity_log_ids=[
                    item["curiosity_log_id"] for item in validated["questions"]
                ],
            )
            return [dict(item) async for item in result]
    finally:
        await close_driver()


async def preflight_manifest_actions(
    manifest: dict[str, Any],
    *,
    skip_curiosity_ids: Iterable[str] = (),
) -> list[dict[str, Any]]:
    """Recheck every new action and prediction before the first live write."""

    from neural.baby.neo4j_db import BrainDatabase, close_driver, init_driver

    validated = validate_manifest(manifest)
    skip = set(skip_curiosity_ids)
    await init_driver()
    try:
        db = BrainDatabase()
        results: list[dict[str, Any]] = []
        for entry in validated["questions"]:
            if entry["curiosity_log_id"] in skip:
                continue
            contract = parse_pending_question_action_contract({
                "curiosity_log_id": entry["curiosity_log_id"],
                "question_outcome_split": PILOT_SPLIT,
                "question_outcome_contract_sha256": validated["contract_sha256"],
            })
            state = await db.validate_pending_question_action(contract)
            if state.get("status") != "valid":
                raise RuntimeError(
                    f"action preflight rejected order {entry['order']}: "
                    f"{state.get('reason')}"
                )
            snapshot = await db.prepare_curiosity_prediction(
                entry["question"],
                cue_terms=build_pending_question_cue_terms(entry["question"]),
            )
            cue_count = len((snapshot or {}).get("cue_concepts") or [])
            prediction_count = len((snapshot or {}).get("predicted_concepts") or [])
            if cue_count < 1 or prediction_count < 1:
                raise RuntimeError(
                    f"prediction preflight rejected order {entry['order']}"
                )
            results.append({
                "order": entry["order"],
                "cue_count": cue_count,
                "prediction_count": prediction_count,
            })
        return results
    finally:
        await close_driver()


async def ping_redis() -> bool:
    """Verify SSE publication can reach Redis before creating any question."""

    from neural.baby.redis_client import close_redis, init_redis

    client = init_redis()
    try:
        return bool(await client.ping())
    finally:
        await close_redis()


async def create_questions(
    manifest: dict[str, Any],
    *,
    base_url: str,
) -> dict[str, Any]:
    """Publish the fixed train questions; answers remain a separate user step."""

    validated = validate_manifest(manifest)
    if not await ping_redis():
        raise RuntimeError("Redis ping failed before B5.7 collection")
    before = await audit_manifest(validated)
    existing_by_curiosity = {item["curiosity_log_id"]: item for item in before}
    action_preflight = await preflight_manifest_actions(
        validated,
        skip_curiosity_ids=existing_by_curiosity,
    )

    created: list[dict[str, Any]] = []
    async with httpx.AsyncClient(base_url=base_url, timeout=60.0) as client:
        health_response = await client.get("/health")
        health_response.raise_for_status()
        health = health_response.json()
        if not health.get("curiosity_pending_question_outcome_eval_enabled"):
            raise RuntimeError("server B5.6 question-outcome opt-in is disabled")
        if not health.get("curiosity_pending_question_outcome_contract_required"):
            raise RuntimeError("server B5.6 question-outcome contract is not required")

        for entry in validated["questions"]:
            existing = existing_by_curiosity.get(entry["curiosity_log_id"])
            if existing:
                if (
                    existing.get("question") != entry["question"]
                    or existing.get("split") != PILOT_SPLIT
                ):
                    raise RuntimeError(
                        f"existing question mismatch for order {entry['order']}"
                    )
                created.append({
                    "order": entry["order"],
                    "question_id": existing["question_id"],
                    "question": entry["question"],
                    "status": "existing",
                })
                continue

            response = await client.post(
                "/api/pending-questions",
                json=build_create_payload(entry, validated["contract_sha256"]),
            )
            response.raise_for_status()
            question = response.json()["question"]
            created.append({
                "order": entry["order"],
                "question_id": question["id"],
                "question": entry["question"],
                "status": "created",
                "cue_count": len(question.get("curiosity_cue_ids") or []),
                "prediction_count": len(question.get("predicted_concept_ids") or []),
            })

    audit = await audit_manifest(validated)
    if len(audit) != MIN_QUESTION_COUNT:
        raise RuntimeError(
            f"post-create audit expected {MIN_QUESTION_COUNT} questions; found {len(audit)}"
        )
    invalid = [
        item for item in audit
        if item.get("status") != "pending"
        or int(item.get("cue_count") or 0) < 1
        or int(item.get("prediction_count") or 0) < 1
        or item.get("split") != PILOT_SPLIT
        or item.get("scoring_mode") != "external_deferred"
        or not item.get("prediction_captured_at")
        or not item.get("asked_at")
        or item["prediction_captured_at"] > item["asked_at"]
    ]
    if invalid:
        raise RuntimeError(
            "post-create contract audit failed for question IDs: "
            + ", ".join(item["question_id"] for item in invalid)
        )

    return {
        "status": "questions_published_waiting_for_external_answers",
        "phase": "B5.7",
        "pilot_name": PILOT_NAME,
        "split": PILOT_SPLIT,
        "contract_sha256": validated["contract_sha256"],
        "created_at": _now_iso(),
        "database_writes": sum(item["status"] == "created" for item in created),
        "live_collection_started": True,
        "heldout_collection_started": False,
        "existing_answer_reuse": False,
        "prediction_scoring_started": False,
        "learning_state_updates": False,
        "production_promotion_gate": False,
        "target_validity_gate": False,
        "evaluation_readiness_gate": False,
        "question_count": len(created),
        "answer_count": sum(bool(item.get("has_answer")) for item in audit),
        "questions": created,
        "preflight": action_preflight,
        "audit": [
            {
                "question_id": item["question_id"],
                "status": item["status"],
                "cue_count": item["cue_count"],
                "prediction_count": item["prediction_count"],
                "outcome_count": item["outcome_count"],
                "has_answer": item["has_answer"],
                "prediction_before_question": (
                    item["prediction_captured_at"] <= item["asked_at"]
                ),
                "scoring_mode": item["scoring_mode"],
            }
            for item in audit
        ],
        "next_step": "collect_real_user_answers",
    }


async def submit_answers(
    manifest: dict[str, Any],
    answer_pack: dict[str, Any],
    *,
    base_url: str,
) -> dict[str, Any]:
    """Submit all approved answers, then unseal aggregate train diagnostics."""

    validated_manifest = validate_manifest(manifest)
    validated_answers = validate_answer_pack(validated_manifest, answer_pack)
    if not await ping_redis():
        raise RuntimeError("Redis ping failed before B5.7 answer submission")
    preflight = await preflight_answers(validated_manifest, validated_answers)
    before_curiosity_state = await _fetch_curiosity_state(validated_manifest)
    preflight_by_order = {item["order"]: item for item in preflight}

    submitted: list[dict[str, Any]] = []
    async with httpx.AsyncClient(base_url=base_url, timeout=60.0) as client:
        health_response = await client.get("/health")
        health_response.raise_for_status()
        health = health_response.json()
        if not health.get("curiosity_pending_question_outcome_eval_enabled"):
            raise RuntimeError("server B5.6 question-outcome opt-in is disabled")
        if not health.get("curiosity_pending_question_outcome_contract_required"):
            raise RuntimeError("server B5.6 question-outcome contract is not required")

        for entry in validated_answers["answers"]:
            preflight_entry = preflight_by_order[entry["order"]]
            if preflight_entry["status"] == "answered":
                submitted.append({
                    "order": entry["order"],
                    "question_id": entry["question_id"],
                    "status": "existing_exact_answer",
                })
                continue
            response = await client.post(
                f"/api/pending-questions/{entry['question_id']}/answer",
                json=build_answer_payload(entry),
            )
            response.raise_for_status()
            payload = response.json()
            question = payload.get("question") or {}
            if not payload.get("success") or question.get("status") != "answered":
                raise RuntimeError(
                    f"answer endpoint did not confirm order {entry['order']}"
                )
            submitted.append({
                "order": entry["order"],
                "question_id": entry["question_id"],
                "status": "recorded",
            })

    completed_records = await _fetch_post_answer_records(validated_manifest)
    after_curiosity_state = await _fetch_curiosity_state(validated_manifest)
    learning_state_unchanged = before_curiosity_state == after_curiosity_state
    evaluation = evaluate_completed_answers(
        validated_manifest,
        completed_records,
        answer_provenance=validated_answers["answer_provenance"],
        learning_state_unchanged=learning_state_unchanged,
    )
    if not evaluation["target_validity_gate"]:
        status = "answers_recorded_target_gate_failed"
        next_step = "diagnose_invalid_train_contract_before_more_collection"
    elif not evaluation["exploratory_train_overlap_signal"]:
        status = "train_target_valid_no_prediction_overlap"
        next_step = "diagnose_predictor_before_freeze_or_heldout_collection"
    else:
        status = "train_target_valid_with_exploratory_overlap"
        next_step = "preregister_predictor_freeze_before_separate_heldout_collection"

    return {
        "status": status,
        "phase": "B5.7",
        "pilot_name": PILOT_NAME,
        "split": PILOT_SPLIT,
        "contract_sha256": validated_manifest["contract_sha256"],
        "completed_at": _now_iso(),
        "answer_role": validated_answers["answer_role"],
        "answer_provenance": validated_answers["answer_provenance"],
        "approved_at": validated_answers["approved_at"],
        "question_count": MIN_QUESTION_COUNT,
        "answer_count": sum(
            item.get("status") == "answered" for item in completed_records
        ),
        "database_writes": sum(item["status"] == "recorded" for item in submitted),
        "existing_exact_answer_count": sum(
            item["status"] == "existing_exact_answer" for item in submitted
        ),
        "prediction_scoring_started": True,
        "learning_state_updates": not learning_state_unchanged,
        "preflight": preflight,
        "submissions": submitted,
        "evaluation": evaluation,
        "next_step": next_step,
    }


def _read_manifest(path: Path) -> dict[str, Any]:
    return validate_manifest(json.loads(path.read_text(encoding="utf-8")))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    path.write_text(f"{rendered}\n", encoding="utf-8")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="B5.7 action-conditioned PendingQuestion train pilot"
    )
    parser.add_argument(
        "action",
        choices=("discover", "prepare", "create", "answer", "audit"),
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--artifact", type=Path, default=DEFAULT_ARTIFACT)
    parser.add_argument("--answers", type=Path, default=DEFAULT_ANSWERS)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--limit", type=int, default=100)
    return parser.parse_args()


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = _parse_args()

    if args.action == "discover":
        candidates = asyncio.run(discover_candidates(args.limit))
        payload = {
            "status": "discovery_complete",
            "database_writes": False,
            "candidate_count": len(candidates),
            "eligible_count": sum(item["eligible"] for item in candidates),
            "candidates": candidates,
        }
    elif args.action == "prepare":
        candidates = asyncio.run(discover_candidates(args.limit))
        manifest = build_manifest(candidates)
        _write_json(args.manifest, manifest)
        payload = {
            "status": "manifest_prepared",
            "database_writes": False,
            "manifest": str(args.manifest),
            "pilot_name": manifest["pilot_name"],
            "split": manifest["split"],
            "contract_sha256": manifest["contract_sha256"],
            "question_count": manifest["question_count"],
            "questions": manifest["questions"],
        }
    elif args.action == "create":
        payload = asyncio.run(create_questions(
            _read_manifest(args.manifest),
            base_url=args.base_url,
        ))
        _write_json(args.artifact, payload)
    elif args.action == "answer":
        payload = asyncio.run(submit_answers(
            _read_manifest(args.manifest),
            json.loads(args.answers.read_text(encoding="utf-8")),
            base_url=args.base_url,
        ))
        _write_json(args.artifact, payload)
    else:
        manifest = _read_manifest(args.manifest)
        audit = asyncio.run(audit_manifest(manifest))
        payload = {
            "status": "audit_complete",
            "database_writes": False,
            "question_count": len(audit),
            "answer_count": sum(bool(item.get("has_answer")) for item in audit),
            "outcome_count": sum(int(item.get("outcome_count") or 0) for item in audit),
            "questions": audit,
        }

    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
