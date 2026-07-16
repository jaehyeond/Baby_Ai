"""Fail-closed J1 Question-as-Experiment contracts and offline metrics.

The contract compares graph and local-core *pre-question* probability
snapshots.  Ranked IDs or post-hoc scores are deliberately not converted into
probabilities.  This module is offline-only: it does not import the database,
the API server, or the protected conversation handler.
"""

from __future__ import annotations

import json
import math
import re
from datetime import datetime, timezone
from statistics import mean
from typing import Any, Iterable, Mapping

from neural.baby.pending_question_semantics import canonical_json_sha256


QUESTION_EXPERIMENT_PACK_VERSION = 1
QUESTION_EXPERIMENT_MODE = "offline_shadow_no_learning"
QUESTION_SELECTION_POLICY = "max_jensen_shannon_disagreement"
REQUIRED_PREDICTORS = ("graph", "local_core")
CALIBRATION_METHODS = frozenset({"platt", "isotonic", "temperature_scaling"})
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_EPSILON = 1e-9


def _zoned_datetime(value: Any, field: str) -> datetime:
    raw = str(value or "").strip()
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} must include a timezone")
    return parsed.astimezone(timezone.utc)


def _require_sha256(value: Any, field: str) -> str:
    raw = str(value or "").strip().lower()
    if not _SHA256_PATTERN.fullmatch(raw):
        raise ValueError(f"{field} must be a lowercase SHA-256")
    return raw


def _probability_map(
    items: Iterable[Mapping[str, Any]],
    *,
    field: str,
) -> dict[str, float]:
    probabilities: dict[str, float] = {}
    for raw_item in items:
        item = dict(raw_item)
        concept_id = str(item.get("concept_id") or "").strip()
        if not concept_id or concept_id in probabilities:
            raise ValueError(f"{field} has a duplicate or empty concept_id")
        try:
            probability = float(item.get("probability"))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{field} probability must be numeric") from exc
        if not math.isfinite(probability) or not 0.0 <= probability <= 1.0:
            raise ValueError(f"{field} probability must be finite and in [0, 1]")
        probabilities[concept_id] = probability
    if not probabilities:
        raise ValueError(f"{field} requires concept probabilities")
    if sum(probabilities.values()) <= 0.0:
        raise ValueError(f"{field} cannot be an all-zero probability snapshot")
    return probabilities


def jensen_shannon_divergence(
    left: Mapping[str, float],
    right: Mapping[str, float],
) -> float:
    """Return base-2 JSD in [0, 1] after normalizing relevance probabilities."""

    if set(left) != set(right) or not left:
        raise ValueError("predictors must use the same non-empty concept universe")
    left_total = sum(float(value) for value in left.values())
    right_total = sum(float(value) for value in right.values())
    if left_total <= 0.0 or right_total <= 0.0:
        raise ValueError("predictor probability totals must be positive")

    divergence = 0.0
    for concept_id in sorted(left):
        p_value = float(left[concept_id]) / left_total
        q_value = float(right[concept_id]) / right_total
        midpoint = (p_value + q_value) / 2.0
        if p_value > 0.0:
            divergence += 0.5 * p_value * math.log2(p_value / midpoint)
        if q_value > 0.0:
            divergence += 0.5 * q_value * math.log2(q_value / midpoint)
    return max(0.0, min(1.0, divergence))


def _candidate_disagreement(candidate: Mapping[str, Any]) -> float:
    predictors = dict(candidate.get("predictors") or {})
    if set(predictors) != set(REQUIRED_PREDICTORS):
        raise ValueError("every candidate requires graph and local_core predictors")
    probability_maps = {
        name: _probability_map(
            dict(predictors[name]).get("concept_probabilities") or [],
            field=f"{name}.concept_probabilities",
        )
        for name in REQUIRED_PREDICTORS
    }
    return jensen_shannon_divergence(
        probability_maps["graph"],
        probability_maps["local_core"],
    )


def select_question_by_disagreement(
    candidates: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    """Select deterministically by maximum graph/core JSD, then question order."""

    scored: list[dict[str, Any]] = []
    for raw_candidate in candidates:
        candidate = dict(raw_candidate)
        scored.append({
            "order": int(candidate["order"]),
            "question": str(candidate.get("question") or ""),
            "disagreement": _candidate_disagreement(candidate),
        })
    if len(scored) < 2:
        raise ValueError("a question decision requires at least two candidates")
    scored.sort(key=lambda item: (
        -item["disagreement"],
        item["order"],
        item["question"],
    ))
    return {
        "selected_order": scored[0]["order"],
        "selected_disagreement": round(scored[0]["disagreement"], 8),
        "runner_up_disagreement": round(scored[1]["disagreement"], 8),
        "candidate_scores": [
            {
                **item,
                "disagreement": round(item["disagreement"], 8),
            }
            for item in scored
        ],
    }


def score_multilabel_probabilities(
    probabilities: Mapping[str, float],
    approved_target_ids: Iterable[str],
    *,
    calibration_bins: int = 5,
) -> dict[str, float]:
    """Score independent relevance probabilities against reviewed multi-label truth."""

    if calibration_bins < 2:
        raise ValueError("calibration_bins must be at least 2")
    targets = {str(item) for item in approved_target_ids if str(item)}
    if not probabilities or not targets:
        raise ValueError("probabilities and approved targets must be non-empty")
    if not targets.issubset(probabilities):
        raise ValueError("approved targets must be inside the predictor concept universe")

    samples: list[tuple[float, int]] = []
    for concept_id in sorted(probabilities):
        probability = float(probabilities[concept_id])
        if not math.isfinite(probability) or not 0.0 <= probability <= 1.0:
            raise ValueError("probabilities must be finite and in [0, 1]")
        samples.append((probability, int(concept_id in targets)))

    brier = mean((probability - label) ** 2 for probability, label in samples)
    binary_log_loss = mean(
        -(
            label * math.log(max(probability, _EPSILON))
            + (1 - label) * math.log(max(1.0 - probability, _EPSILON))
        )
        for probability, label in samples
    )
    expected_calibration_error = 0.0
    for bin_index in range(calibration_bins):
        lower = bin_index / calibration_bins
        upper = (bin_index + 1) / calibration_bins
        bucket = [
            (probability, label)
            for probability, label in samples
            if lower <= probability < upper
            or (bin_index == calibration_bins - 1 and probability == 1.0)
        ]
        if not bucket:
            continue
        confidence = mean(item[0] for item in bucket)
        accuracy = mean(item[1] for item in bucket)
        expected_calibration_error += (
            len(bucket) / len(samples)
        ) * abs(confidence - accuracy)

    ranked = sorted(probabilities, key=lambda concept_id: (
        -float(probabilities[concept_id]),
        concept_id,
    ))
    top_k = set(ranked[: len(targets)])
    top_k_recall = len(top_k & targets) / len(targets)
    return {
        "brier": round(brier, 8),
        "binary_log_loss": round(binary_log_loss, 8),
        "expected_calibration_error": round(expected_calibration_error, 8),
        "top_k_recall": round(top_k_recall, 8),
    }


def _approved_targets_by_order(
    label_pack: Mapping[str, Any],
) -> tuple[dict[int, set[str]], dict[int, str]]:
    if label_pack.get("review_status") != "user_reviewed":
        raise ValueError("J1 evaluation requires user_reviewed semantic labels")
    targets: dict[int, set[str]] = {}
    question_ids: dict[int, str] = {}
    for raw_entry in label_pack.get("entries") or []:
        entry = dict(raw_entry)
        order = int(entry["order"])
        approved = {
            str(label.get("concept_id") or "").strip()
            for label in entry.get("labels") or []
            if label.get("decision") == "approved"
        }
        approved.discard("")
        if not approved:
            raise ValueError(f"reviewed labels require an approved target at order {order}")
        targets[order] = approved
        question_ids[order] = str(entry.get("question_id") or "").strip()
    return targets, question_ids


def validate_question_experiment_pack(
    manifest: Mapping[str, Any],
    label_pack: Mapping[str, Any],
    experiment_pack: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate exact question binding and sealed no-learning prediction decisions."""

    normalized = json.loads(json.dumps(experiment_pack, ensure_ascii=False))
    if normalized.get("question_experiment_pack_version") != QUESTION_EXPERIMENT_PACK_VERSION:
        raise ValueError("unsupported question_experiment_pack_version")
    contract_sha256 = _require_sha256(
        manifest.get("contract_sha256"),
        "manifest.contract_sha256",
    )
    if label_pack.get("contract_sha256") != contract_sha256:
        raise ValueError("semantic label contract_sha256 mismatch")
    if normalized.get("contract_sha256") != contract_sha256:
        raise ValueError("experiment contract_sha256 mismatch")
    expected_label_hash = canonical_json_sha256(label_pack)
    if normalized.get("semantic_label_pack_sha256") != expected_label_hash:
        raise ValueError("semantic_label_pack_sha256 mismatch")
    if normalized.get("mode") != QUESTION_EXPERIMENT_MODE:
        raise ValueError("J1 pack must use offline_shadow_no_learning mode")
    if normalized.get("learning_enabled") is not False:
        raise ValueError("J1 first pass must keep learning disabled")
    if normalized.get("split") != "train":
        raise ValueError("J1 initial contract is train-only")
    _zoned_datetime(normalized.get("created_at"), "created_at")

    manifest_by_order = {
        int(item["order"]): dict(item)
        for item in manifest.get("questions") or []
    }
    targets_by_order, question_ids_by_order = _approved_targets_by_order(label_pack)
    decisions = list(normalized.get("decisions") or [])
    if not decisions:
        raise ValueError("J1 pack requires at least one sealed decision")

    seen_decision_ids: set[str] = set()
    for decision in decisions:
        decision_id = str(decision.get("decision_id") or "").strip()
        if not decision_id or decision_id in seen_decision_ids:
            raise ValueError("decision_id must be non-empty and unique")
        seen_decision_ids.add(decision_id)
        if decision.get("selection_policy") != QUESTION_SELECTION_POLICY:
            raise ValueError("unsupported question selection policy")
        selection_at = _zoned_datetime(
            decision.get("selection_captured_at"),
            f"{decision_id}.selection_captured_at",
        )
        asked_at = _zoned_datetime(
            decision.get("asked_at"),
            f"{decision_id}.asked_at",
        )
        if selection_at > asked_at:
            raise ValueError("question selection must precede the asked timestamp")

        candidates = list(decision.get("candidate_questions") or [])
        if len(candidates) < 2:
            raise ValueError("a sealed decision requires at least two question candidates")
        candidate_orders: set[int] = set()
        for candidate in candidates:
            order = int(candidate["order"])
            if order in candidate_orders or order not in manifest_by_order:
                raise ValueError("candidate question order is duplicate or unknown")
            candidate_orders.add(order)
            expected_question = str(manifest_by_order[order].get("question") or "")
            if candidate.get("question") != expected_question:
                raise ValueError(f"question text mismatch at order {order}")

            predictors = dict(candidate.get("predictors") or {})
            if set(predictors) != set(REQUIRED_PREDICTORS):
                raise ValueError("every candidate requires graph and local_core predictors")
            probability_maps: dict[str, dict[str, float]] = {}
            for predictor_name in REQUIRED_PREDICTORS:
                snapshot = dict(predictors[predictor_name])
                if snapshot.get("predictor") != predictor_name:
                    raise ValueError("predictor identity mismatch")
                if not str(snapshot.get("snapshot_id") or "").strip():
                    raise ValueError("predictor snapshot_id is required")
                _require_sha256(
                    snapshot.get("model_snapshot_sha256"),
                    f"{predictor_name}.model_snapshot_sha256",
                )
                captured_at = _zoned_datetime(
                    snapshot.get("captured_at"),
                    f"{predictor_name}.captured_at",
                )
                if captured_at > selection_at:
                    raise ValueError("predictor snapshots must precede question selection")
                calibration = dict(snapshot.get("calibration") or {})
                if calibration.get("method") not in CALIBRATION_METHODS:
                    raise ValueError("predictor probabilities require a supported calibration method")
                _require_sha256(
                    calibration.get("dataset_sha256"),
                    f"{predictor_name}.calibration.dataset_sha256",
                )
                _require_sha256(
                    calibration.get("calibrator_sha256"),
                    f"{predictor_name}.calibration.calibrator_sha256",
                )
                try:
                    calibration_count = int(calibration.get("sample_count"))
                    positive_count = int(calibration.get("positive_count"))
                    negative_count = int(calibration.get("negative_count"))
                except (TypeError, ValueError) as exc:
                    raise ValueError("calibration counts must be integers") from exc
                if (
                    calibration_count < 2
                    or positive_count < 1
                    or negative_count < 1
                    or positive_count + negative_count != calibration_count
                ):
                    raise ValueError("calibration requires sealed positive and negative samples")
                fitted_at = _zoned_datetime(
                    calibration.get("fitted_at"),
                    f"{predictor_name}.calibration.fitted_at",
                )
                if fitted_at > captured_at:
                    raise ValueError("calibrator must be fitted before predictor capture")
                probability_maps[predictor_name] = _probability_map(
                    snapshot.get("concept_probabilities") or [],
                    field=f"{predictor_name}.concept_probabilities",
                )
            if set(probability_maps["graph"]) != set(probability_maps["local_core"]):
                raise ValueError("graph and local_core must score the same concept universe")
            if not targets_by_order[order].issubset(probability_maps["graph"]):
                raise ValueError("candidate universe must include every reviewed target")

        selection = select_question_by_disagreement(candidates)
        selected_order = int(decision.get("selected_order", -1))
        if selected_order != selection["selected_order"]:
            raise ValueError("selected_order does not match deterministic disagreement policy")
        if decision.get("selected_question_id") != question_ids_by_order[selected_order]:
            raise ValueError("selected_question_id does not match reviewed outcome provenance")

    return normalized


def evaluate_question_experiment_pack(
    manifest: Mapping[str, Any],
    label_pack: Mapping[str, Any],
    experiment_pack: Mapping[str, Any],
) -> dict[str, Any]:
    """Evaluate a valid train-only shadow pack without updating learning state."""

    validated = validate_question_experiment_pack(
        manifest,
        label_pack,
        experiment_pack,
    )
    targets_by_order, _ = _approved_targets_by_order(label_pack)
    decision_reports: list[dict[str, Any]] = []
    predictor_metrics: dict[str, list[dict[str, float]]] = {
        name: [] for name in REQUIRED_PREDICTORS
    }

    for decision in validated["decisions"]:
        selection = select_question_by_disagreement(decision["candidate_questions"])
        selected_order = selection["selected_order"]
        selected_candidate = next(
            item
            for item in decision["candidate_questions"]
            if int(item["order"]) == selected_order
        )
        scored_predictors: dict[str, dict[str, float]] = {}
        for predictor_name in REQUIRED_PREDICTORS:
            snapshot = selected_candidate["predictors"][predictor_name]
            probability_map = _probability_map(
                snapshot["concept_probabilities"],
                field=f"{predictor_name}.concept_probabilities",
            )
            metrics = score_multilabel_probabilities(
                probability_map,
                targets_by_order[selected_order],
            )
            predictor_metrics[predictor_name].append(metrics)
            scored_predictors[predictor_name] = metrics
        decision_reports.append({
            "decision_id": decision["decision_id"],
            "selected_order": selected_order,
            "selected_question_id": decision["selected_question_id"],
            **selection,
            "predictor_metrics": scored_predictors,
        })

    aggregates = {
        predictor_name: {
            metric_name: round(mean(item[metric_name] for item in metrics), 8)
            for metric_name in metrics[0]
        }
        for predictor_name, metrics in predictor_metrics.items()
    }
    return {
        "status": "completed",
        "mode": QUESTION_EXPERIMENT_MODE,
        "contract_gate": True,
        "decision_count": len(decision_reports),
        "decisions": decision_reports,
        "aggregate_predictor_metrics": aggregates,
        "learning_enabled": False,
        "database_writes": False,
        "heldout_gate": False,
        "performance_claim_gate": False,
        "production_promotion_gate": False,
        "block_reasons": [
            "same_six_train_questions",
            "no_sealed_future_heldout",
            "shadow_measurement_only",
        ],
    }


def audit_legacy_j1_readiness(
    manifest: Mapping[str, Any],
    b5_7_artifact: Mapping[str, Any],
    b5_8_artifact: Mapping[str, Any],
    label_pack: Mapping[str, Any],
) -> dict[str, Any]:
    """Audit why the six B5.9 questions cannot be reused as a J1 experiment."""

    manifest_orders = {int(item["order"]) for item in manifest.get("questions") or []}
    targets_by_order, _ = _approved_targets_by_order(label_pack)
    b5_8_by_order = {
        int(item["order"]): dict(item)
        for item in b5_8_artifact.get("questions") or []
        if item.get("order") is not None
    }
    ranked_id_snapshots = all(
        bool(b5_8_by_order.get(order, {}).get("baseline_predicted_ids"))
        for order in manifest_orders
    )
    graph_probabilities = all(
        bool(b5_8_by_order.get(order, {}).get("graph_probability_snapshot"))
        for order in manifest_orders
    )
    local_core_probabilities = all(
        bool(b5_8_by_order.get(order, {}).get("local_core_probability_snapshot"))
        for order in manifest_orders
    )
    reviewed_orders = set(targets_by_order)
    learning_disabled = b5_7_artifact.get("learning_state_updates") is False
    gates = {
        "question_texts_bound": all(
            str(item.get("question") or "").strip()
            for item in manifest.get("questions") or []
        ),
        "reviewed_semantic_targets": reviewed_orders == manifest_orders,
        "historical_ranked_graph_ids_present": ranked_id_snapshots,
        "calibrated_graph_probability_snapshots": graph_probabilities,
        "local_core_probability_snapshots": local_core_probabilities,
        "two_or_more_candidates_per_decision": False,
        "predictor_snapshot_hashes_sealed_before_question": False,
        "sealed_probability_calibrators": False,
        "learning_disabled": learning_disabled,
    }
    return {
        "status": "blocked",
        "phase": "J1.0",
        "mode": "legacy_readiness_audit",
        "question_count": len(manifest_orders),
        "approved_semantic_target_count": sum(len(items) for items in targets_by_order.values()),
        "readiness_gates": gates,
        "contract_gate": all(gates.values()),
        "database_writes": False,
        "learning_enabled": False,
        "heldout_gate": False,
        "production_promotion_gate": False,
        "block_reasons": [
            "ranked_graph_ids_are_not_calibrated_probabilities",
            "local_core_pre_question_probabilities_missing",
            "historical_questions_were_not_a_multi_candidate_decision",
            "predictor_snapshot_hashes_not_sealed_before_question",
            "probability_calibration_provenance_missing",
        ],
        "next_step": (
            "preregister_new_train_calibration_questions_and_capture_graph_and_"
            "local_core_raw_scores_before_asking_then_fit_sealed_calibrators"
        ),
    }
