"""Offline probability snapshots from the J1.1B train-only calibrator.

The snapshot replays a sealed train-only calibrator over the sealed candidate
unions.  It is an audit artifact for later question-selection design; it is not
a runtime probability service and must not write DB, learn, or promote.
"""

from __future__ import annotations

import json
import math
from typing import Any, Mapping

from neural.baby.calibrator_design import validate_calibrator_design_audit
from neural.baby.calibrator_fit import (
    validate_train_only_calibrator_fit,
    _predict_probability,
)
from neural.baby.pending_question_semantics import canonical_json_sha256


CALIBRATOR_PROBABILITY_SNAPSHOT_VERSION = 1
SNAPSHOT_SCOPE = "train_calibration_replay_only"
SNAPSHOT_POLICY = "calibrated_relevance_probability_replay"


def _clone(value: Mapping[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(value, ensure_ascii=False))


def _entropy_binary(probability: float) -> float:
    if probability <= 0.0 or probability >= 1.0:
        return 0.0
    return -(
        probability * math.log2(probability)
        + (1.0 - probability) * math.log2(1.0 - probability)
    )


def _seal_snapshot(payload: Mapping[str, Any]) -> dict[str, Any]:
    normalized = _clone(payload)
    normalized.pop("calibrator_probability_snapshot_sha256", None)
    normalized["calibrator_probability_snapshot_sha256"] = canonical_json_sha256(
        normalized
    )
    return normalized


def _all_design_rows(design: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = [_clone(row) for row in design.get("fit_rows") or []]
    rows.extend(_clone(row) for row in design.get("excluded_rows") or [])
    rows.sort(key=lambda item: (int(item["order"]), str(item["concept_id"])))
    return rows


def build_calibrator_probability_snapshot(
    design_audit: Mapping[str, Any],
    fit_artifact: Mapping[str, Any],
) -> dict[str, Any]:
    """Replay the final train-only calibrator over every sealed union row."""

    design = validate_calibrator_design_audit(design_audit)
    fit = validate_train_only_calibrator_fit(fit_artifact, design)
    rows = _all_design_rows(design)
    if len(rows) != int(design["candidate_label_count"]):
        raise ValueError("probability snapshot must cover every candidate label")
    final_model = fit["final_train_only_model"]
    by_order: dict[int, list[dict[str, Any]]] = {}
    for row in rows:
        probability = _predict_probability(final_model, row)
        order = int(row["order"])
        by_order.setdefault(order, []).append({
            "concept_id": row["concept_id"],
            "probability": probability,
            "source_row_type": (
                "fit_row" if row.get("target") in (0, 1) else "excluded_uncertain"
            ),
            "feature_values_sha256": canonical_json_sha256(row["feature_values"]),
        })

    question_snapshots = []
    for order in sorted(by_order):
        probabilities = sorted(
            by_order[order],
            key=lambda item: (-float(item["probability"]), item["concept_id"]),
        )
        entropy_values = [
            _entropy_binary(float(item["probability"])) for item in probabilities
        ]
        question_snapshots.append({
            "order": order,
            "candidate_count": len(probabilities),
            "top_concept_id": probabilities[0]["concept_id"],
            "top_probability": probabilities[0]["probability"],
            "mean_probability": sum(
                float(item["probability"]) for item in probabilities
            ) / len(probabilities),
            "mean_binary_entropy": sum(entropy_values) / len(entropy_values),
            "uncertainty_band_count_0_4_to_0_6": sum(
                1 for item in probabilities
                if 0.4 <= float(item["probability"]) <= 0.6
            ),
            "concept_probabilities": probabilities,
        })

    selected = max(
        question_snapshots,
        key=lambda item: (
            item["mean_binary_entropy"],
            item["uncertainty_band_count_0_4_to_0_6"],
            -item["order"],
        ),
    )
    snapshot = _seal_snapshot({
        "calibrator_probability_snapshot_version": (
            CALIBRATOR_PROBABILITY_SNAPSHOT_VERSION
        ),
        "phase": "J1.1B",
        "status": "offline_probability_snapshot_ready_not_runtime",
        "snapshot_scope": SNAPSHOT_SCOPE,
        "snapshot_policy": SNAPSHOT_POLICY,
        "question_selection_policy_preview": (
            "max_mean_binary_entropy_tie_uncertainty_band_then_order"
        ),
        "calibrator_design_audit_sha256": design[
            "calibrator_design_audit_sha256"
        ],
        "train_only_calibrator_fit_sha256": fit[
            "train_only_calibrator_fit_sha256"
        ],
        "independent_score_capture_sha256": design[
            "independent_score_capture_sha256"
        ],
        "union_label_pack_sha256": design["union_label_pack_sha256"],
        "question_count": len(question_snapshots),
        "candidate_label_count": design["candidate_label_count"],
        "probability_count": sum(
            item["candidate_count"] for item in question_snapshots
        ),
        "question_snapshots": question_snapshots,
        "selected_order_preview": selected["order"],
        "selected_order_preview_reason": (
            "highest_mean_binary_entropy_in_train_calibration_replay"
        ),
        "offline_probability_snapshot_gate": True,
        "runtime_probability_snapshot_gate": False,
        "question_selection_runtime_gate": False,
        "database_writes": False,
        "learning_enabled": False,
        "heldout_gate": False,
        "performance_claim_gate": False,
        "production_promotion_gate": False,
        "block_reasons": [],
        "next_step": "design_runtime_question_selection_contract_without_db_write",
    })
    return validate_calibrator_probability_snapshot(snapshot, design, fit)


def validate_calibrator_probability_snapshot(
    payload: Mapping[str, Any],
    design_audit: Mapping[str, Any] | None = None,
    fit_artifact: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    normalized = _clone(payload)
    if normalized.get("calibrator_probability_snapshot_version") != (
        CALIBRATOR_PROBABILITY_SNAPSHOT_VERSION
    ):
        raise ValueError("unsupported calibrator_probability_snapshot_version")
    if normalized.get("phase") != "J1.1B":
        raise ValueError("probability snapshot must be J1.1B")
    if normalized.get("snapshot_scope") != SNAPSHOT_SCOPE:
        raise ValueError("probability snapshot scope mismatch")
    if normalized.get("snapshot_policy") != SNAPSHOT_POLICY:
        raise ValueError("probability snapshot policy mismatch")
    if design_audit is not None:
        design = validate_calibrator_design_audit(design_audit)
        if normalized.get("calibrator_design_audit_sha256") != design.get(
            "calibrator_design_audit_sha256"
        ):
            raise ValueError("probability snapshot design binding mismatch")
        if normalized.get("candidate_label_count") != design.get(
            "candidate_label_count"
        ):
            raise ValueError("probability snapshot candidate count mismatch")
    if fit_artifact is not None:
        fit = validate_train_only_calibrator_fit(
            fit_artifact,
            design_audit if design_audit is not None else None,
        )
        if normalized.get("train_only_calibrator_fit_sha256") != fit.get(
            "train_only_calibrator_fit_sha256"
        ):
            raise ValueError("probability snapshot fit binding mismatch")

    question_snapshots = list(normalized.get("question_snapshots") or [])
    if normalized.get("question_count") != len(question_snapshots):
        raise ValueError("probability snapshot question_count mismatch")
    probability_count = 0
    seen_orders: set[int] = set()
    for question in question_snapshots:
        order = int(question["order"])
        if order in seen_orders:
            raise ValueError("probability snapshot has duplicate question order")
        seen_orders.add(order)
        probabilities = list(question.get("concept_probabilities") or [])
        if question.get("candidate_count") != len(probabilities):
            raise ValueError("probability snapshot candidate_count mismatch")
        probability_count += len(probabilities)
        seen_ids: set[str] = set()
        for item in probabilities:
            concept_id = str(item.get("concept_id") or "")
            probability = float(item.get("probability"))
            if not concept_id or concept_id in seen_ids:
                raise ValueError("probability snapshot concept IDs must be unique")
            if not math.isfinite(probability) or not 0.0 <= probability <= 1.0:
                raise ValueError("snapshot probabilities must be finite and in [0, 1]")
            if item.get("source_row_type") not in {"fit_row", "excluded_uncertain"}:
                raise ValueError("unsupported probability snapshot source row type")
            seen_ids.add(concept_id)
    if normalized.get("probability_count") != probability_count:
        raise ValueError("probability snapshot probability_count mismatch")

    required_false = (
        "runtime_probability_snapshot_gate",
        "question_selection_runtime_gate",
        "database_writes",
        "learning_enabled",
        "heldout_gate",
        "performance_claim_gate",
        "production_promotion_gate",
    )
    if any(normalized.get(field) is not False for field in required_false):
        raise ValueError("probability snapshot cannot enable runtime gates")
    if normalized.get("offline_probability_snapshot_gate") is not True:
        raise ValueError("offline probability snapshot gate must be true")
    supplied_hash = str(
        normalized.get("calibrator_probability_snapshot_sha256") or ""
    )
    unhashed = _clone(normalized)
    unhashed.pop("calibrator_probability_snapshot_sha256", None)
    if supplied_hash != canonical_json_sha256(unhashed):
        raise ValueError("calibrator_probability_snapshot_sha256 mismatch")
    return normalized
