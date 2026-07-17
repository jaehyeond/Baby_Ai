"""Train-only J1.1B calibrator fit contract.

This module fits a deterministic offline logistic calibrator from a sealed
calibrator design audit.  It may compute train-calibration probabilities inside
the artifact, but it never writes the database, enables learning, evaluates
held-out data, or promotes runtime behavior.
"""

from __future__ import annotations

import json
import math
from typing import Any, Iterable, Mapping

from neural.baby.calibrator_design import validate_calibrator_design_audit
from neural.baby.pending_question_semantics import canonical_json_sha256


CALIBRATOR_FIT_ARTIFACT_VERSION = 1
MODEL_TYPE = "l2_logistic_regression_binary_relevance_v1"
DEFAULT_L2 = 0.1
DEFAULT_LEARNING_RATE = 0.1
DEFAULT_MAX_ITERATIONS = 1200
DEFAULT_ECE_BINS = 5
EPSILON = 1e-12


def _clone(value: Mapping[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(value, ensure_ascii=False))


def _sigmoid(value: float) -> float:
    if value >= 0:
        z = math.exp(-value)
        return 1.0 / (1.0 + z)
    z = math.exp(value)
    return z / (1.0 + z)


def _safe_probability(value: float) -> float:
    return min(1.0 - EPSILON, max(EPSILON, value))


def _standardization(rows: list[Mapping[str, Any]], feature_names: list[str]) -> dict[str, dict[str, float]]:
    means: dict[str, float] = {}
    scales: dict[str, float] = {}
    for name in feature_names:
        values = [float(row["feature_values"][name]) for row in rows]
        mean = sum(values) / len(values)
        variance = sum((value - mean) ** 2 for value in values) / len(values)
        scale = math.sqrt(variance)
        means[name] = mean
        scales[name] = scale if scale > 1e-12 else 1.0
    return {"means": means, "scales": scales}


def _vector(
    row: Mapping[str, Any],
    feature_names: list[str],
    standardization: Mapping[str, Mapping[str, float]],
) -> list[float]:
    means = standardization["means"]
    scales = standardization["scales"]
    return [
        (float(row["feature_values"][name]) - float(means[name]))
        / float(scales[name])
        for name in feature_names
    ]


def _fit_logistic(
    rows: list[Mapping[str, Any]],
    feature_names: list[str],
    *,
    l2: float,
    learning_rate: float,
    max_iterations: int,
) -> dict[str, Any]:
    if not rows:
        raise ValueError("calibrator fit requires rows")
    targets = [int(row["target"]) for row in rows]
    if set(targets) != {0, 1}:
        raise ValueError("calibrator fit requires both positive and negative rows")
    standardization = _standardization(rows, feature_names)
    vectors = [_vector(row, feature_names, standardization) for row in rows]
    weights = [0.0 for _ in feature_names]
    intercept = math.log(sum(targets) / (len(targets) - sum(targets)))
    n = float(len(rows))
    for _ in range(max_iterations):
        grad_w = [0.0 for _ in feature_names]
        grad_b = 0.0
        for x_vec, target in zip(vectors, targets):
            logit = intercept + sum(weight * value for weight, value in zip(weights, x_vec))
            error = _sigmoid(logit) - target
            grad_b += error
            for index, value in enumerate(x_vec):
                grad_w[index] += error * value
        grad_b /= n
        for index in range(len(weights)):
            grad_w[index] = (grad_w[index] / n) + (l2 * weights[index] / n)
        intercept -= learning_rate * grad_b
        for index in range(len(weights)):
            weights[index] -= learning_rate * grad_w[index]
    return {
        "model_type": MODEL_TYPE,
        "feature_names": feature_names,
        "intercept": intercept,
        "weights": {
            name: weights[index] for index, name in enumerate(feature_names)
        },
        "standardization": standardization,
        "fitted_row_count": len(rows),
        "positive_count": sum(targets),
        "negative_count": len(targets) - sum(targets),
    }


def _predict_probability(
    model: Mapping[str, Any],
    row: Mapping[str, Any],
) -> float:
    feature_names = list(model["feature_names"])
    x_vec = _vector(row, feature_names, model["standardization"])
    logit = float(model["intercept"])
    weights = model["weights"]
    for name, value in zip(feature_names, x_vec):
        logit += float(weights[name]) * value
    return _sigmoid(logit)


def _auc_roc(predictions: list[Mapping[str, Any]]) -> float | None:
    positives = [item for item in predictions if int(item["target"]) == 1]
    negatives = [item for item in predictions if int(item["target"]) == 0]
    if not positives or not negatives:
        return None
    wins = 0.0
    total = 0
    for positive in positives:
        for negative in negatives:
            total += 1
            p_score = float(positive["probability"])
            n_score = float(negative["probability"])
            if p_score > n_score:
                wins += 1.0
            elif p_score == n_score:
                wins += 0.5
    return wins / total


def _ece(predictions: list[Mapping[str, Any]], bins: int) -> float:
    total = len(predictions)
    if total == 0:
        return 0.0
    value = 0.0
    for index in range(bins):
        lower = index / bins
        upper = (index + 1) / bins
        bucket = [
            item for item in predictions
            if lower <= float(item["probability"]) <= upper
            and (index == bins - 1 or float(item["probability"]) < upper)
        ]
        if not bucket:
            continue
        confidence = sum(float(item["probability"]) for item in bucket) / len(bucket)
        accuracy = sum(int(item["target"]) for item in bucket) / len(bucket)
        value += (len(bucket) / total) * abs(confidence - accuracy)
    return value


def _metrics(predictions: list[Mapping[str, Any]], *, bins: int) -> dict[str, Any]:
    if not predictions:
        raise ValueError("metrics require predictions")
    brier = sum(
        (float(item["probability"]) - int(item["target"])) ** 2
        for item in predictions
    ) / len(predictions)
    log_loss = -sum(
        int(item["target"]) * math.log(_safe_probability(float(item["probability"])))
        + (1 - int(item["target"]))
        * math.log(_safe_probability(1.0 - float(item["probability"])))
        for item in predictions
    ) / len(predictions)
    accuracy = sum(
        int((float(item["probability"]) >= 0.5) == bool(int(item["target"])))
        for item in predictions
    ) / len(predictions)
    return {
        "row_count": len(predictions),
        "positive_count": sum(int(item["target"]) for item in predictions),
        "negative_count": sum(1 - int(item["target"]) for item in predictions),
        "brier": brier,
        "log_loss": log_loss,
        "accuracy_at_0_5": accuracy,
        "ece": _ece(predictions, bins),
        "auc_roc": _auc_roc(predictions),
    }


def _rows_for_orders(rows: Iterable[Mapping[str, Any]], orders: set[int]) -> list[dict[str, Any]]:
    return [
        _clone(row) for row in rows if int(row["order"]) in orders
    ]


def _seal_train_only_calibrator_fit(payload: Mapping[str, Any]) -> dict[str, Any]:
    normalized = _clone(payload)
    normalized.pop("train_only_calibrator_fit_sha256", None)
    normalized["train_only_calibrator_fit_sha256"] = canonical_json_sha256(normalized)
    return normalized


def fit_train_only_calibrator(
    design_audit: Mapping[str, Any],
    *,
    l2: float = DEFAULT_L2,
    learning_rate: float = DEFAULT_LEARNING_RATE,
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
    ece_bins: int = DEFAULT_ECE_BINS,
) -> dict[str, Any]:
    """Fit a train-only calibrator and evaluate leave-one-question-out folds."""

    design = validate_calibrator_design_audit(design_audit)
    if design.get("calibrator_design_gate") is not True:
        raise ValueError("calibrator design gate must pass before fit")
    rows = [_clone(row) for row in design.get("fit_rows") or []]
    if len(rows) != int(design.get("fit_row_count")):
        raise ValueError("design fit_row_count mismatch")
    feature_names = list(design["feature_names"])
    fold_predictions: list[dict[str, Any]] = []
    fold_metrics = []
    for fold in design["folds"]:
        validation_order = int(fold["validation_order"])
        train_rows = [
            row for row in rows if int(row["order"]) != validation_order
        ]
        validation_rows = [
            row for row in rows if int(row["order"]) == validation_order
        ]
        model = _fit_logistic(
            train_rows,
            feature_names,
            l2=l2,
            learning_rate=learning_rate,
            max_iterations=max_iterations,
        )
        predictions = []
        for row in validation_rows:
            prediction = {
                "fold": fold["fold"],
                "order": row["order"],
                "question_id": row["question_id"],
                "concept_id": row["concept_id"],
                "target": int(row["target"]),
                "probability": _predict_probability(model, row),
            }
            predictions.append(prediction)
            fold_predictions.append(prediction)
        fold_metrics.append({
            "fold": fold["fold"],
            "validation_order": validation_order,
            "metrics": _metrics(predictions, bins=ece_bins),
        })

    final_model = _fit_logistic(
        rows,
        feature_names,
        l2=l2,
        learning_rate=learning_rate,
        max_iterations=max_iterations,
    )
    artifact = _seal_train_only_calibrator_fit({
        "train_only_calibrator_fit_artifact_version": (
            CALIBRATOR_FIT_ARTIFACT_VERSION
        ),
        "phase": "J1.1B",
        "status": "train_only_calibrator_fit_completed_offline_not_promoted",
        "calibrator_design_audit_sha256": design[
            "calibrator_design_audit_sha256"
        ],
        "independent_score_capture_sha256": design[
            "independent_score_capture_sha256"
        ],
        "union_label_pack_sha256": design["union_label_pack_sha256"],
        "reviewed_reference_answer_pack_sha256": design[
            "reviewed_reference_answer_pack_sha256"
        ],
        "model_type": MODEL_TYPE,
        "hyperparameters": {
            "l2": l2,
            "learning_rate": learning_rate,
            "max_iterations": max_iterations,
            "ece_bins": ece_bins,
        },
        "feature_names": feature_names,
        "target_mapping": design["target_mapping"],
        "training_scope": "train_calibration_only",
        "evaluation_scope": "leave_one_question_out_on_train_calibration_only",
        "fit_row_count": len(rows),
        "excluded_uncertain_count": design["excluded_uncertain_count"],
        "fold_count": len(fold_metrics),
        "fold_metrics": fold_metrics,
        "cross_validation_predictions": fold_predictions,
        "cross_validation_metrics": _metrics(fold_predictions, bins=ece_bins),
        "final_train_only_model": final_model,
        "train_only_fit_execution_gate": True,
        "offline_probabilities_computed": True,
        "runtime_probabilities_computed": False,
        "calibrator_fit_gate": True,
        "database_writes": False,
        "learning_enabled": False,
        "heldout_gate": False,
        "performance_claim_gate": False,
        "production_promotion_gate": False,
        "block_reasons": [],
        "next_step": "audit_question_selection_probability_snapshot_before_runtime_use",
    })
    return validate_train_only_calibrator_fit(artifact, design)


def validate_train_only_calibrator_fit(
    payload: Mapping[str, Any],
    design_audit: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    normalized = _clone(payload)
    if normalized.get("train_only_calibrator_fit_artifact_version") != (
        CALIBRATOR_FIT_ARTIFACT_VERSION
    ):
        raise ValueError("unsupported train_only_calibrator_fit_artifact_version")
    if normalized.get("phase") != "J1.1B":
        raise ValueError("train-only calibrator fit must be J1.1B")
    if normalized.get("model_type") != MODEL_TYPE:
        raise ValueError("unsupported calibrator model_type")
    if normalized.get("training_scope") != "train_calibration_only":
        raise ValueError("calibrator training must remain train-only")
    if normalized.get("evaluation_scope") != (
        "leave_one_question_out_on_train_calibration_only"
    ):
        raise ValueError("calibrator evaluation scope mismatch")
    if design_audit is not None:
        design = validate_calibrator_design_audit(design_audit)
        for field in (
            "calibrator_design_audit_sha256",
            "independent_score_capture_sha256",
            "union_label_pack_sha256",
            "reviewed_reference_answer_pack_sha256",
            "fit_row_count",
            "excluded_uncertain_count",
            "fold_count",
        ):
            if normalized.get(field) != design.get(field):
                raise ValueError(f"calibrator fit {field} binding mismatch")
        if normalized.get("feature_names") != design.get("feature_names"):
            raise ValueError("calibrator fit feature schema mismatch")
    predictions = list(normalized.get("cross_validation_predictions") or [])
    if len(predictions) != int(normalized.get("fit_row_count")):
        raise ValueError("calibrator predictions must cover every fit row")
    for prediction in predictions:
        probability = float(prediction.get("probability"))
        if not math.isfinite(probability) or not 0.0 <= probability <= 1.0:
            raise ValueError("calibrator probability must be finite and in [0, 1]")
        if prediction.get("target") not in (0, 1):
            raise ValueError("calibrator prediction target must be binary")
    final_model = normalized.get("final_train_only_model") or {}
    if final_model.get("feature_names") != normalized.get("feature_names"):
        raise ValueError("final model feature schema mismatch")
    if set(final_model.get("weights") or {}) != set(normalized.get("feature_names") or []):
        raise ValueError("final model weights must cover every feature")
    required_false = (
        "runtime_probabilities_computed",
        "database_writes",
        "learning_enabled",
        "heldout_gate",
        "performance_claim_gate",
        "production_promotion_gate",
    )
    if any(normalized.get(field) is not False for field in required_false):
        raise ValueError("train-only calibrator fit cannot enable runtime gates")
    if normalized.get("train_only_fit_execution_gate") is not True:
        raise ValueError("train-only fit execution gate must be true")
    if normalized.get("offline_probabilities_computed") is not True:
        raise ValueError("offline calibrator probabilities must be recorded")
    supplied_hash = str(normalized.get("train_only_calibrator_fit_sha256") or "")
    unhashed = _clone(normalized)
    unhashed.pop("train_only_calibrator_fit_sha256", None)
    if supplied_hash != canonical_json_sha256(unhashed):
        raise ValueError("train_only_calibrator_fit_sha256 mismatch")
    return normalized
