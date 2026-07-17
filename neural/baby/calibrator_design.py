"""Pure audit contracts for J1.1B train-only calibrator design.

The audit joins sealed independent-union scores with user-reviewed labels and
defines the feature/target/split contract for a later fit step.  It deliberately
does not fit a model, write the database, enable learning, or promote runtime
behavior.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from typing import Any, Mapping

from neural.baby.candidate_universe import (
    build_union_label_readiness_report,
    validate_union_label_pack,
)
from neural.baby.pending_question_semantics import canonical_json_sha256


CALIBRATOR_DESIGN_AUDIT_VERSION = 1
CALIBRATOR_DESIGN_FEATURE_NAMES = (
    "graph_raw_score",
    "local_core_raw_score",
    "graph_rank",
    "local_core_rank",
    "graph_rank_percentile",
    "local_core_rank_percentile",
    "in_graph_top_k",
    "in_local_core_top_k",
    "in_both_top_k",
)
FORBIDDEN_FEATURE_NAMES = frozenset({
    "answer",
    "answer_sha256",
    "concept_id",
    "concept_name",
    "decision",
    "label",
    "question",
    "question_id",
    "question_sha256",
    "rationale",
    "review_status",
})


def _clone(value: Mapping[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(value, ensure_ascii=False))


def _rank_percentile(rank: int, eligible_count: int) -> float:
    if eligible_count <= 1:
        return 1.0
    return 1.0 - ((rank - 1) / (eligible_count - 1))


def _target_from_decision(decision: str) -> int | None:
    if decision == "approved":
        return 1
    if decision == "rejected":
        return 0
    if decision == "uncertain":
        return None
    raise ValueError("unsupported reviewed label decision")


def _seal_calibrator_design_audit(payload: Mapping[str, Any]) -> dict[str, Any]:
    normalized = _clone(payload)
    normalized.pop("calibrator_design_audit_sha256", None)
    normalized["calibrator_design_audit_sha256"] = canonical_json_sha256(normalized)
    return normalized


def _build_feature_values(
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


def build_calibrator_design_audit(
    capture: Mapping[str, Any],
    answer_pack: Mapping[str, Any],
    reviewed_label_pack: Mapping[str, Any],
) -> dict[str, Any]:
    """Build a sealed design audit without fitting a calibrator."""

    labels = validate_union_label_pack(
        capture,
        answer_pack,
        reviewed_label_pack,
        require_user_review=True,
    )
    readiness = build_union_label_readiness_report(capture, answer_pack, labels)
    if readiness["explicit_user_review_gate"] is not True:
        raise ValueError("reviewed labels are required before calibrator design")

    feature_names = list(CALIBRATOR_DESIGN_FEATURE_NAMES)
    forbidden = sorted(FORBIDDEN_FEATURE_NAMES & set(feature_names))
    leakage_guard_gate = not forbidden
    capture_by_order = {
        int(item["order"]): item for item in capture.get("questions") or []
    }

    fit_rows: list[dict[str, Any]] = []
    excluded_rows: list[dict[str, Any]] = []
    label_counts: Counter[str] = Counter()
    for entry in sorted(labels["entries"], key=lambda item: int(item["order"])):
        order = int(entry["order"])
        captured = capture_by_order[order]
        union = captured["independent_union"]
        graph_top_ids = set(union["graph_top_k_ids"])
        local_top_ids = set(union["local_core_top_k_ids"])
        candidates = {
            item["concept_id"]: item for item in union["union"]
        }
        for label in entry["labels"]:
            decision = str(label["decision"])
            label_counts[decision] += 1
            target = _target_from_decision(decision)
            row = {
                "order": order,
                "question_id": entry["question_id"],
                "concept_id": label["concept_id"],
                "target": target,
                "feature_values": _build_feature_values(
                    candidates[label["concept_id"]],
                    eligible_count=int(union["eligible_concept_count"]),
                    graph_top_ids=graph_top_ids,
                    local_top_ids=local_top_ids,
                ),
            }
            if target is None:
                row["excluded_reason"] = "uncertain_label"
                excluded_rows.append(row)
            else:
                fit_rows.append(row)

    rows_by_order: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in fit_rows:
        rows_by_order[int(row["order"])].append(row)
    folds = []
    for order in sorted(capture_by_order):
        validation_rows = rows_by_order.get(order, [])
        train_rows = [
            row for row in fit_rows if int(row["order"]) != order
        ]
        train_counts = Counter(row["target"] for row in train_rows)
        validation_counts = Counter(row["target"] for row in validation_rows)
        folds.append({
            "fold": f"leave_order_{order}_out",
            "validation_order": order,
            "train_row_count": len(train_rows),
            "validation_row_count": len(validation_rows),
            "train_positive_count": train_counts[1],
            "train_negative_count": train_counts[0],
            "validation_positive_count": validation_counts[1],
            "validation_negative_count": validation_counts[0],
            "fold_gate": (
                train_counts[1] > 0
                and train_counts[0] > 0
                and validation_counts[1] > 0
                and validation_counts[0] > 0
            ),
        })

    positive_count = label_counts["approved"]
    negative_count = label_counts["rejected"]
    uncertain_count = label_counts["uncertain"]
    minimum_label_gate = positive_count > 0 and negative_count > 0
    question_grouped_split_gate = all(item["fold_gate"] for item in folds)
    design_gate = (
        leakage_guard_gate
        and readiness["dual_predictor_positive_coverage_gate"] is True
        and minimum_label_gate
        and question_grouped_split_gate
    )
    block_reasons = []
    if not leakage_guard_gate:
        block_reasons.append("forbidden_feature_names_present")
    if readiness["dual_predictor_positive_coverage_gate"] is not True:
        block_reasons.append("dual_predictor_positive_coverage_missing")
    if not minimum_label_gate:
        block_reasons.append("positive_and_negative_labels_required")
    if not question_grouped_split_gate:
        block_reasons.append("leave_one_question_out_fold_not_trainable")

    audit = _seal_calibrator_design_audit({
        "calibrator_design_audit_version": CALIBRATOR_DESIGN_AUDIT_VERSION,
        "phase": "J1.1B",
        "status": (
            "train_only_calibrator_design_ready_fit_not_executed"
            if design_gate else
            "calibrator_design_blocked"
        ),
        "independent_score_capture_sha256": capture[
            "independent_score_capture_sha256"
        ],
        "union_label_pack_sha256": labels["union_label_pack_sha256"],
        "reviewed_reference_answer_pack_sha256": answer_pack[
            "reference_answer_pack_sha256"
        ],
        "feature_names": feature_names,
        "forbidden_feature_names": forbidden,
        "target_mapping": {
            "approved": 1,
            "rejected": 0,
            "uncertain": "excluded_from_fit",
        },
        "split_strategy": "leave_one_question_out_grouped_by_question_order",
        "question_count": readiness["question_count"],
        "candidate_label_count": readiness["candidate_label_count"],
        "fit_row_count": len(fit_rows),
        "excluded_uncertain_count": uncertain_count,
        "positive_count": positive_count,
        "negative_count": negative_count,
        "decision_counts": {
            "approved": positive_count,
            "rejected": negative_count,
            "uncertain": uncertain_count,
        },
        "fold_count": len(folds),
        "folds": folds,
        "fit_rows": fit_rows,
        "excluded_rows": excluded_rows,
        "reviewed_label_gate": True,
        "dual_predictor_positive_coverage_gate": readiness[
            "dual_predictor_positive_coverage_gate"
        ],
        "leakage_guard_gate": leakage_guard_gate,
        "minimum_label_gate": minimum_label_gate,
        "question_grouped_split_gate": question_grouped_split_gate,
        "calibrator_design_gate": design_gate,
        "fit_execution_gate": False,
        "calibrator_fit_gate": False,
        "database_writes": False,
        "learning_enabled": False,
        "probabilities_computed": False,
        "heldout_gate": False,
        "performance_claim_gate": False,
        "production_promotion_gate": False,
        "block_reasons": block_reasons,
        "next_step": (
            "implement_train_only_calibrator_fit_script"
            if design_gate else
            "repair_calibrator_design_inputs_before_fit"
        ),
    })
    return validate_calibrator_design_audit(audit)


def validate_calibrator_design_audit(payload: Mapping[str, Any]) -> dict[str, Any]:
    normalized = _clone(payload)
    if normalized.get("calibrator_design_audit_version") != (
        CALIBRATOR_DESIGN_AUDIT_VERSION
    ):
        raise ValueError("unsupported calibrator_design_audit_version")
    if normalized.get("phase") != "J1.1B":
        raise ValueError("calibrator design audit must be J1.1B")
    feature_names = list(normalized.get("feature_names") or [])
    if feature_names != list(CALIBRATOR_DESIGN_FEATURE_NAMES):
        raise ValueError("calibrator feature schema mismatch")
    if FORBIDDEN_FEATURE_NAMES & set(feature_names):
        raise ValueError("calibrator feature schema includes forbidden fields")
    for row in list(normalized.get("fit_rows") or []):
        if sorted((row.get("feature_values") or {}).keys()) != sorted(feature_names):
            raise ValueError("calibrator fit row feature schema mismatch")
        if row.get("target") not in (0, 1):
            raise ValueError("calibrator fit rows require binary targets")
    for row in list(normalized.get("excluded_rows") or []):
        if row.get("target") is not None:
            raise ValueError("excluded rows must not have fit targets")
        if row.get("excluded_reason") != "uncertain_label":
            raise ValueError("unsupported calibrator exclusion reason")
    required_false = (
        "fit_execution_gate",
        "calibrator_fit_gate",
        "database_writes",
        "learning_enabled",
        "probabilities_computed",
        "heldout_gate",
        "performance_claim_gate",
        "production_promotion_gate",
    )
    if any(normalized.get(field) is not False for field in required_false):
        raise ValueError("calibrator design audit cannot enable downstream gates")
    supplied_hash = str(normalized.get("calibrator_design_audit_sha256") or "")
    unhashed = _clone(normalized)
    unhashed.pop("calibrator_design_audit_sha256", None)
    if supplied_hash != canonical_json_sha256(unhashed):
        raise ValueError("calibrator_design_audit_sha256 mismatch")
    return normalized
