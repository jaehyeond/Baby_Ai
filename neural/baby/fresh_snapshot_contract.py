"""Offline input contract for fresh pre-question J1.1B snapshots.

This contract defines the inputs a future fresh pre-question snapshot must
provide before any runtime question selection is allowed.  It does not compute
runtime probabilities, select a question at runtime, write the database, learn,
or promote production behavior.
"""

from __future__ import annotations

from datetime import datetime
import json
from typing import Any, Mapping

from neural.baby.calibrator_design import (
    CALIBRATOR_DESIGN_FEATURE_NAMES,
    validate_calibrator_design_audit,
)
from neural.baby.pending_question_semantics import canonical_json_sha256
from neural.baby.question_selection_contract import (
    SELECTION_POLICY,
    validate_question_selection_contract,
)


FRESH_PRE_QUESTION_SNAPSHOT_INPUT_CONTRACT_VERSION = 1
FRESH_PRE_QUESTION_INPUT_PACK_VERSION = 1
FRESH_PRE_QUESTION_INPUT_CONTRACT_SCOPE = (
    "fresh_pre_question_shadow_input_contract"
)
FRESH_PRE_QUESTION_INPUT_PACK_SCOPE = "fresh_pre_question_shadow_input_pack"
FRESH_PRE_QUESTION_INPUT_STATUS = (
    "fresh_pre_question_snapshot_input_contract_ready_not_runtime"
)
REQUIRED_MIN_CANDIDATE_QUESTIONS = 2

REQUIRED_QUESTION_FIELDS = (
    "order",
    "question_id",
    "question_sha256",
    "pre_question_captured_at",
    "candidate_rows",
)
REQUIRED_CANDIDATE_ROW_FIELDS = (
    "concept_id",
    "feature_values",
)
FORBIDDEN_FRESH_INPUT_FIELDS = frozenset({
    "answer",
    "answer_sha256",
    "answer_text",
    "calibrated_probability",
    "decision",
    "label",
    "outcome",
    "post_question_captured_at",
    "probability",
    "rationale",
    "review_status",
    "selected_order",
    "selected_question_id",
    "target",
    "user_review",
})


def _clone(value: Mapping[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(value, ensure_ascii=False))


def _feature_schema_sha256() -> str:
    return canonical_json_sha256({
        "feature_names": list(CALIBRATOR_DESIGN_FEATURE_NAMES),
    })


def _seal_contract(payload: Mapping[str, Any]) -> dict[str, Any]:
    normalized = _clone(payload)
    normalized.pop("fresh_pre_question_snapshot_input_contract_sha256", None)
    normalized["fresh_pre_question_snapshot_input_contract_sha256"] = (
        canonical_json_sha256(normalized)
    )
    return normalized


def seal_fresh_pre_question_snapshot_input_pack(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    normalized = _clone(payload)
    normalized.pop("fresh_pre_question_input_pack_sha256", None)
    normalized["fresh_pre_question_input_pack_sha256"] = canonical_json_sha256(
        normalized
    )
    return normalized


def _require_zoned_iso_timestamp(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field_name} must be a non-empty ISO timestamp")
    parse_value = value[:-1] + "+00:00" if value.endswith("Z") else value
    parsed = datetime.fromisoformat(parse_value)
    if parsed.tzinfo is None or parsed.tzinfo.utcoffset(parsed) is None:
        raise ValueError(f"{field_name} must include timezone offset")
    return value


def _validate_hex_sha256(value: Any, field_name: str) -> str:
    text = str(value or "")
    if len(text) != 64 or any(char not in "0123456789abcdef" for char in text):
        raise ValueError(f"{field_name} must be lowercase hex sha256")
    return text


def _walk_forbidden_fields(value: Any, path: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            key_text = str(key)
            if key_text in FORBIDDEN_FRESH_INPUT_FIELDS:
                raise ValueError(f"fresh input forbidden field present: {path}.{key}")
            _walk_forbidden_fields(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _walk_forbidden_fields(child, f"{path}[{index}]")


def _validate_feature_values(value: Any) -> dict[str, float | int]:
    if not isinstance(value, Mapping):
        raise ValueError("candidate feature_values must be an object")
    expected = list(CALIBRATOR_DESIGN_FEATURE_NAMES)
    if sorted(value.keys()) != sorted(expected):
        raise ValueError("fresh input feature schema mismatch")
    clean: dict[str, float | int] = {}
    for key in expected:
        raw = value[key]
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            raise ValueError("fresh input feature values must be numeric")
        clean[key] = raw
    return clean


def _rank_percentile(rank: int, eligible_count: int) -> float:
    if eligible_count <= 1:
        return 1.0
    return 1.0 - ((rank - 1) / (eligible_count - 1))


def _feature_values_from_union_candidate(
    candidate: Mapping[str, Any],
    *,
    eligible_count: int,
    graph_top_ids: set[str],
    local_top_ids: set[str],
) -> dict[str, float | int]:
    concept_id = str(candidate["concept_id"])
    graph_rank = int(candidate["graph_rank"])
    local_rank = int(candidate["local_core_rank"])
    in_graph = concept_id in graph_top_ids
    in_local = concept_id in local_top_ids
    return {
        "graph_raw_score": float(candidate["graph_raw_score"]),
        "local_core_raw_score": float(candidate["local_core_raw_score"]),
        "graph_rank": graph_rank,
        "local_core_rank": local_rank,
        "graph_rank_percentile": _rank_percentile(graph_rank, eligible_count),
        "local_core_rank_percentile": _rank_percentile(local_rank, eligible_count),
        "in_graph_top_k": int(in_graph),
        "in_local_core_top_k": int(in_local),
        "in_both_top_k": int(in_graph and in_local),
    }


def build_fresh_pre_question_snapshot_input_contract(
    question_selection_contract: Mapping[str, Any],
    calibrator_design_audit: Mapping[str, Any],
) -> dict[str, Any]:
    """Build a sealed offline contract for future fresh snapshot inputs."""

    selection = validate_question_selection_contract(question_selection_contract)
    design = validate_calibrator_design_audit(calibrator_design_audit)
    if selection["calibrator_design_audit_sha256"] != design[
        "calibrator_design_audit_sha256"
    ]:
        raise ValueError("fresh input contract design binding mismatch")

    contract = _seal_contract({
        "fresh_pre_question_snapshot_input_contract_version": (
            FRESH_PRE_QUESTION_SNAPSHOT_INPUT_CONTRACT_VERSION
        ),
        "phase": "J1.1B",
        "status": FRESH_PRE_QUESTION_INPUT_STATUS,
        "input_contract_scope": FRESH_PRE_QUESTION_INPUT_CONTRACT_SCOPE,
        "input_pack_version": FRESH_PRE_QUESTION_INPUT_PACK_VERSION,
        "input_pack_scope": FRESH_PRE_QUESTION_INPUT_PACK_SCOPE,
        "selection_policy": SELECTION_POLICY,
        "question_selection_contract_sha256": selection[
            "question_selection_contract_sha256"
        ],
        "calibrator_probability_snapshot_sha256": selection[
            "calibrator_probability_snapshot_sha256"
        ],
        "calibrator_design_audit_sha256": selection[
            "calibrator_design_audit_sha256"
        ],
        "train_only_calibrator_fit_sha256": selection[
            "train_only_calibrator_fit_sha256"
        ],
        "feature_schema_sha256": _feature_schema_sha256(),
        "feature_names": list(CALIBRATOR_DESIGN_FEATURE_NAMES),
        "required_candidate_question_count_min": (
            REQUIRED_MIN_CANDIDATE_QUESTIONS
        ),
        "required_question_fields": list(REQUIRED_QUESTION_FIELDS),
        "required_candidate_row_fields": list(REQUIRED_CANDIDATE_ROW_FIELDS),
        "forbidden_input_fields": sorted(FORBIDDEN_FRESH_INPUT_FIELDS),
        "freshness_requirements": {
            "pre_question_captured_at_requires_timezone": True,
            "question_text_must_be_hash_bound_not_included": True,
            "features_must_be_captured_before_question_is_shown": True,
            "answers_labels_reviews_and_probabilities_forbidden": True,
        },
        "fresh_pre_question_snapshot_input_contract_gate": True,
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
            "capture_fresh_pre_question_snapshot_shadow_read_only_"
            "before_runtime_selection"
        ),
    })
    return validate_fresh_pre_question_snapshot_input_contract(
        contract,
        question_selection_contract,
        calibrator_design_audit,
    )


def build_shadow_fresh_pre_question_snapshot_input_pack(
    input_contract: Mapping[str, Any],
    independent_score_capture: Mapping[str, Any],
    *,
    captured_at: str | None = None,
) -> dict[str, Any]:
    """Convert a sealed score capture into a no-runtime shadow input pack."""

    contract = validate_fresh_pre_question_snapshot_input_contract(input_contract)
    source_captured_at = _require_zoned_iso_timestamp(
        captured_at or independent_score_capture.get("captured_at"),
        "pre_question_captured_at",
    )
    questions = []
    candidate_row_count = 0
    for question in sorted(
        list(independent_score_capture.get("questions") or []),
        key=lambda item: int(item["order"]),
    ):
        union = dict(question["independent_union"])
        graph_top_ids = set(union["graph_top_k_ids"])
        local_top_ids = set(union["local_core_top_k_ids"])
        eligible_count = int(union["eligible_concept_count"])
        rows = []
        for candidate in union["union"]:
            rows.append({
                "concept_id": candidate["concept_id"],
                "feature_values": _feature_values_from_union_candidate(
                    candidate,
                    eligible_count=eligible_count,
                    graph_top_ids=graph_top_ids,
                    local_top_ids=local_top_ids,
                ),
            })
        candidate_row_count += len(rows)
        questions.append({
            "order": question["order"],
            "question_id": question["question_id"],
            "question_sha256": question["question_sha256"],
            "pre_question_captured_at": source_captured_at,
            "candidate_rows": rows,
        })

    pack = seal_fresh_pre_question_snapshot_input_pack({
        "fresh_pre_question_input_pack_version": (
            FRESH_PRE_QUESTION_INPUT_PACK_VERSION
        ),
        "phase": "J1.1B",
        "status": "fresh_pre_question_shadow_input_pack_ready_not_runtime",
        "input_pack_scope": FRESH_PRE_QUESTION_INPUT_PACK_SCOPE,
        "source_scope": "sealed_train_capture_shadow_not_runtime_fresh",
        "selection_policy": contract["selection_policy"],
        "feature_schema_sha256": contract["feature_schema_sha256"],
        "feature_names": contract["feature_names"],
        "fresh_pre_question_snapshot_input_contract_sha256": contract[
            "fresh_pre_question_snapshot_input_contract_sha256"
        ],
        "source_independent_score_capture_sha256": independent_score_capture[
            "independent_score_capture_sha256"
        ],
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
            "compute_fresh_pre_question_shadow_probabilities_offline_"
            "before_runtime_selection"
        ),
    })
    return validate_fresh_pre_question_snapshot_input_pack(pack, contract)


def validate_fresh_pre_question_snapshot_input_contract(
    payload: Mapping[str, Any],
    question_selection_contract: Mapping[str, Any] | None = None,
    calibrator_design_audit: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    normalized = _clone(payload)
    if normalized.get("fresh_pre_question_snapshot_input_contract_version") != (
        FRESH_PRE_QUESTION_SNAPSHOT_INPUT_CONTRACT_VERSION
    ):
        raise ValueError("unsupported fresh input contract version")
    if normalized.get("phase") != "J1.1B":
        raise ValueError("fresh input contract must be J1.1B")
    if normalized.get("status") != FRESH_PRE_QUESTION_INPUT_STATUS:
        raise ValueError("fresh input contract status mismatch")
    if normalized.get("input_contract_scope") != (
        FRESH_PRE_QUESTION_INPUT_CONTRACT_SCOPE
    ):
        raise ValueError("fresh input contract scope mismatch")
    if normalized.get("input_pack_version") != FRESH_PRE_QUESTION_INPUT_PACK_VERSION:
        raise ValueError("fresh input pack version mismatch")
    if normalized.get("input_pack_scope") != FRESH_PRE_QUESTION_INPUT_PACK_SCOPE:
        raise ValueError("fresh input pack scope mismatch")
    if normalized.get("selection_policy") != SELECTION_POLICY:
        raise ValueError("fresh input selection policy mismatch")
    if normalized.get("feature_names") != list(CALIBRATOR_DESIGN_FEATURE_NAMES):
        raise ValueError("fresh input feature schema mismatch")
    if normalized.get("feature_schema_sha256") != _feature_schema_sha256():
        raise ValueError("fresh input feature schema hash mismatch")
    if normalized.get("required_candidate_question_count_min") != (
        REQUIRED_MIN_CANDIDATE_QUESTIONS
    ):
        raise ValueError("fresh input minimum question count mismatch")
    if normalized.get("required_question_fields") != list(REQUIRED_QUESTION_FIELDS):
        raise ValueError("fresh input required question fields mismatch")
    if normalized.get("required_candidate_row_fields") != list(
        REQUIRED_CANDIDATE_ROW_FIELDS
    ):
        raise ValueError("fresh input required candidate fields mismatch")
    if normalized.get("forbidden_input_fields") != sorted(
        FORBIDDEN_FRESH_INPUT_FIELDS
    ):
        raise ValueError("fresh input forbidden fields mismatch")

    if question_selection_contract is not None:
        selection = validate_question_selection_contract(question_selection_contract)
        for field in (
            "question_selection_contract_sha256",
            "calibrator_probability_snapshot_sha256",
            "calibrator_design_audit_sha256",
            "train_only_calibrator_fit_sha256",
        ):
            if normalized.get(field) != selection.get(field):
                raise ValueError(f"fresh input {field} binding mismatch")
    if calibrator_design_audit is not None:
        design = validate_calibrator_design_audit(calibrator_design_audit)
        if normalized.get("calibrator_design_audit_sha256") != design.get(
            "calibrator_design_audit_sha256"
        ):
            raise ValueError("fresh input design binding mismatch")

    required_false = (
        "fresh_snapshot_runtime_gate",
        "question_selection_runtime_gate",
        "runtime_probability_snapshot_gate",
        "database_writes",
        "learning_enabled",
        "heldout_gate",
        "performance_claim_gate",
        "production_promotion_gate",
    )
    if any(normalized.get(field) is not False for field in required_false):
        raise ValueError("fresh input contract cannot enable runtime gates")
    if normalized.get("fresh_pre_question_snapshot_input_contract_gate") is not True:
        raise ValueError("fresh input contract gate must be true")

    supplied_hash = str(
        normalized.get("fresh_pre_question_snapshot_input_contract_sha256") or ""
    )
    unhashed = _clone(normalized)
    unhashed.pop("fresh_pre_question_snapshot_input_contract_sha256", None)
    if supplied_hash != canonical_json_sha256(unhashed):
        raise ValueError("fresh input contract sha256 mismatch")
    return normalized


def validate_fresh_pre_question_snapshot_input_pack(
    payload: Mapping[str, Any],
    input_contract: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate a future fresh input pack without computing probabilities."""

    contract = validate_fresh_pre_question_snapshot_input_contract(input_contract)
    normalized = _clone(payload)
    _walk_forbidden_fields(normalized)

    if normalized.get("fresh_pre_question_input_pack_version") != (
        FRESH_PRE_QUESTION_INPUT_PACK_VERSION
    ):
        raise ValueError("unsupported fresh input pack version")
    if normalized.get("phase") != "J1.1B":
        raise ValueError("fresh input pack must be J1.1B")
    if normalized.get("input_pack_scope") != FRESH_PRE_QUESTION_INPUT_PACK_SCOPE:
        raise ValueError("fresh input pack scope mismatch")
    if normalized.get("selection_policy") != contract["selection_policy"]:
        raise ValueError("fresh input pack selection policy mismatch")
    if normalized.get("feature_schema_sha256") != contract["feature_schema_sha256"]:
        raise ValueError("fresh input pack feature schema hash mismatch")
    if normalized.get("feature_names") != contract["feature_names"]:
        raise ValueError("fresh input pack feature schema mismatch")
    if normalized.get("fresh_pre_question_snapshot_input_contract_sha256") != (
        contract["fresh_pre_question_snapshot_input_contract_sha256"]
    ):
        raise ValueError("fresh input pack contract binding mismatch")
    _require_zoned_iso_timestamp(
        normalized.get("pre_question_captured_at"),
        "pre_question_captured_at",
    )

    candidate_questions = list(normalized.get("candidate_questions") or [])
    if len(candidate_questions) < contract["required_candidate_question_count_min"]:
        raise ValueError("fresh input pack requires at least two questions")
    if (
        "question_count" in normalized
        and normalized.get("question_count") != len(candidate_questions)
    ):
        raise ValueError("fresh input pack question_count mismatch")

    seen_orders: set[int] = set()
    seen_question_ids: set[str] = set()
    candidate_row_count = 0
    for question in candidate_questions:
        if sorted(question.keys()) != sorted(REQUIRED_QUESTION_FIELDS):
            raise ValueError("fresh input question field set mismatch")
        order = int(question["order"])
        if order in seen_orders:
            raise ValueError("fresh input question orders must be unique")
        seen_orders.add(order)
        question_id = str(question["question_id"] or "")
        if not question_id or question_id in seen_question_ids:
            raise ValueError("fresh input question IDs must be unique")
        seen_question_ids.add(question_id)
        _validate_hex_sha256(question["question_sha256"], "question_sha256")
        _require_zoned_iso_timestamp(
            question["pre_question_captured_at"],
            "candidate_question.pre_question_captured_at",
        )

        rows = list(question.get("candidate_rows") or [])
        if not rows:
            raise ValueError("fresh input questions require candidate rows")
        candidate_row_count += len(rows)
        seen_concept_ids: set[str] = set()
        for row in rows:
            if sorted(row.keys()) != sorted(REQUIRED_CANDIDATE_ROW_FIELDS):
                raise ValueError("fresh input candidate field set mismatch")
            concept_id = str(row["concept_id"] or "")
            if not concept_id or concept_id in seen_concept_ids:
                raise ValueError("fresh input concept IDs must be unique per question")
            seen_concept_ids.add(concept_id)
            _validate_feature_values(row["feature_values"])

    required_false = (
        "fresh_snapshot_runtime_gate",
        "question_selection_runtime_gate",
        "runtime_probability_snapshot_gate",
        "database_writes",
        "learning_enabled",
        "heldout_gate",
        "performance_claim_gate",
        "production_promotion_gate",
    )
    if any(normalized.get(field) is not False for field in required_false):
        raise ValueError("fresh input pack cannot enable runtime gates")
    if normalized.get("fresh_pre_question_input_pack_gate") is not True:
        raise ValueError("fresh input pack gate must be true")
    if (
        "candidate_row_count" in normalized
        and normalized.get("candidate_row_count") != candidate_row_count
    ):
        raise ValueError("fresh input pack candidate_row_count mismatch")
    supplied_hash = str(normalized.get("fresh_pre_question_input_pack_sha256") or "")
    if supplied_hash:
        unhashed = _clone(normalized)
        unhashed.pop("fresh_pre_question_input_pack_sha256", None)
        if supplied_hash != canonical_json_sha256(unhashed):
            raise ValueError("fresh input pack sha256 mismatch")
    return normalized
