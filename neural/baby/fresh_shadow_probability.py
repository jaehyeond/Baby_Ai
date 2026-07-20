"""Offline probabilities for fresh pre-question shadow input packs.

This module replays the sealed train-only calibrator over a validated fresh
pre-question shadow input pack.  It does not run runtime selection, write the
database, enable learning, evaluate held-out data, or promote behavior.
"""

from __future__ import annotations

import json
import math
from typing import Any, Mapping

from neural.baby.calibrator_fit import (
    _predict_probability,
    validate_train_only_calibrator_fit,
)
from neural.baby.fresh_snapshot_contract import (
    validate_fresh_pre_question_snapshot_input_contract,
    validate_fresh_pre_question_snapshot_input_pack,
)
from neural.baby.pending_question_semantics import canonical_json_sha256
from neural.baby.question_selection_contract import SELECTION_POLICY


FRESH_SHADOW_PROBABILITY_SNAPSHOT_VERSION = 1
FRESH_SHADOW_PROBABILITY_SCOPE = (
    "fresh_pre_question_shadow_pack_offline_replay"
)
FRESH_SHADOW_PROBABILITY_POLICY = (
    "train_only_calibrator_final_model_probability_replay"
)


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
    normalized.pop("fresh_pre_question_shadow_probability_snapshot_sha256", None)
    normalized["fresh_pre_question_shadow_probability_snapshot_sha256"] = (
        canonical_json_sha256(normalized)
    )
    return normalized


def build_fresh_pre_question_shadow_probability_snapshot(
    input_contract: Mapping[str, Any],
    input_pack: Mapping[str, Any],
    train_only_fit: Mapping[str, Any],
) -> dict[str, Any]:
    """Compute offline probabilities for every fresh shadow candidate row."""

    contract = validate_fresh_pre_question_snapshot_input_contract(input_contract)
    pack = validate_fresh_pre_question_snapshot_input_pack(input_pack, contract)
    fit = validate_train_only_calibrator_fit(train_only_fit)
    if fit["train_only_calibrator_fit_sha256"] != contract[
        "train_only_calibrator_fit_sha256"
    ]:
        raise ValueError("fresh shadow probability fit binding mismatch")
    if fit["feature_names"] != contract["feature_names"]:
        raise ValueError("fresh shadow probability feature schema mismatch")

    final_model = fit["final_train_only_model"]
    question_snapshots = []
    probability_count = 0
    for question in pack["candidate_questions"]:
        probabilities = []
        for row in question["candidate_rows"]:
            probability = _predict_probability(final_model, row)
            probabilities.append({
                "concept_id": row["concept_id"],
                "probability": probability,
                "feature_values_sha256": canonical_json_sha256(
                    row["feature_values"]
                ),
            })
        probabilities.sort(
            key=lambda item: (-float(item["probability"]), item["concept_id"])
        )
        probability_count += len(probabilities)
        entropy_values = [
            _entropy_binary(float(item["probability"])) for item in probabilities
        ]
        question_snapshots.append({
            "order": question["order"],
            "question_id": question["question_id"],
            "question_sha256": question["question_sha256"],
            "pre_question_captured_at": question["pre_question_captured_at"],
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

    snapshot = _seal_snapshot({
        "fresh_pre_question_shadow_probability_snapshot_version": (
            FRESH_SHADOW_PROBABILITY_SNAPSHOT_VERSION
        ),
        "phase": "J1.1B",
        "status": (
            "fresh_pre_question_shadow_probabilities_ready_not_runtime"
        ),
        "probability_scope": FRESH_SHADOW_PROBABILITY_SCOPE,
        "probability_policy": FRESH_SHADOW_PROBABILITY_POLICY,
        "selection_policy": SELECTION_POLICY,
        "fresh_pre_question_snapshot_input_contract_sha256": contract[
            "fresh_pre_question_snapshot_input_contract_sha256"
        ],
        "fresh_pre_question_input_pack_sha256": pack[
            "fresh_pre_question_input_pack_sha256"
        ],
        "source_independent_score_capture_sha256": pack[
            "source_independent_score_capture_sha256"
        ],
        "train_only_calibrator_fit_sha256": fit[
            "train_only_calibrator_fit_sha256"
        ],
        "calibrator_design_audit_sha256": fit["calibrator_design_audit_sha256"],
        "feature_schema_sha256": contract["feature_schema_sha256"],
        "feature_names": contract["feature_names"],
        "question_count": len(question_snapshots),
        "candidate_row_count": pack["candidate_row_count"],
        "probability_count": probability_count,
        "question_probability_snapshots": question_snapshots,
        "fresh_shadow_probability_snapshot_gate": True,
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
            "select_fresh_shadow_question_offline_before_runtime_selection"
        ),
    })
    return validate_fresh_pre_question_shadow_probability_snapshot(
        snapshot,
        input_contract,
        input_pack,
        train_only_fit,
    )


def validate_fresh_pre_question_shadow_probability_snapshot(
    payload: Mapping[str, Any],
    input_contract: Mapping[str, Any] | None = None,
    input_pack: Mapping[str, Any] | None = None,
    train_only_fit: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    normalized = _clone(payload)
    if normalized.get("fresh_pre_question_shadow_probability_snapshot_version") != (
        FRESH_SHADOW_PROBABILITY_SNAPSHOT_VERSION
    ):
        raise ValueError("unsupported fresh shadow probability snapshot version")
    if normalized.get("phase") != "J1.1B":
        raise ValueError("fresh shadow probability snapshot must be J1.1B")
    if normalized.get("status") != (
        "fresh_pre_question_shadow_probabilities_ready_not_runtime"
    ):
        raise ValueError("fresh shadow probability status mismatch")
    if normalized.get("probability_scope") != FRESH_SHADOW_PROBABILITY_SCOPE:
        raise ValueError("fresh shadow probability scope mismatch")
    if normalized.get("probability_policy") != FRESH_SHADOW_PROBABILITY_POLICY:
        raise ValueError("fresh shadow probability policy mismatch")
    if normalized.get("selection_policy") != SELECTION_POLICY:
        raise ValueError("fresh shadow probability selection policy mismatch")

    if input_contract is not None:
        contract = validate_fresh_pre_question_snapshot_input_contract(
            input_contract
        )
        for field in (
            "fresh_pre_question_snapshot_input_contract_sha256",
            "feature_schema_sha256",
            "feature_names",
        ):
            if normalized.get(field) != contract.get(field):
                raise ValueError(f"fresh shadow probability {field} mismatch")
    if input_pack is not None:
        if input_contract is None:
            raise ValueError("input_contract is required when input_pack is supplied")
        pack = validate_fresh_pre_question_snapshot_input_pack(
            input_pack,
            contract,
        )
        if normalized.get("fresh_pre_question_input_pack_sha256") != pack.get(
            "fresh_pre_question_input_pack_sha256"
        ):
            raise ValueError("fresh shadow probability input pack binding mismatch")
        if normalized.get("source_independent_score_capture_sha256") != pack.get(
            "source_independent_score_capture_sha256"
        ):
            raise ValueError("fresh shadow probability source capture mismatch")
        if normalized.get("candidate_row_count") != pack.get("candidate_row_count"):
            raise ValueError("fresh shadow probability candidate count mismatch")
    if train_only_fit is not None:
        fit = validate_train_only_calibrator_fit(train_only_fit)
        if normalized.get("train_only_calibrator_fit_sha256") != fit.get(
            "train_only_calibrator_fit_sha256"
        ):
            raise ValueError("fresh shadow probability fit binding mismatch")
        if normalized.get("calibrator_design_audit_sha256") != fit.get(
            "calibrator_design_audit_sha256"
        ):
            raise ValueError("fresh shadow probability design binding mismatch")
        if normalized.get("feature_names") != fit.get("feature_names"):
            raise ValueError("fresh shadow probability fit feature mismatch")

    question_snapshots = list(
        normalized.get("question_probability_snapshots") or []
    )
    if normalized.get("question_count") != len(question_snapshots):
        raise ValueError("fresh shadow probability question_count mismatch")
    probability_count = 0
    seen_orders: set[int] = set()
    for question in question_snapshots:
        order = int(question["order"])
        if order in seen_orders:
            raise ValueError("fresh shadow probability duplicate question order")
        seen_orders.add(order)
        probabilities = list(question.get("concept_probabilities") or [])
        if question.get("candidate_count") != len(probabilities):
            raise ValueError("fresh shadow probability candidate_count mismatch")
        probability_count += len(probabilities)
        seen_concept_ids: set[str] = set()
        for item in probabilities:
            concept_id = str(item.get("concept_id") or "")
            probability = float(item.get("probability"))
            if not concept_id or concept_id in seen_concept_ids:
                raise ValueError("fresh shadow probability concept IDs must be unique")
            if not math.isfinite(probability) or not 0.0 <= probability <= 1.0:
                raise ValueError("fresh shadow probabilities must be finite in [0, 1]")
            seen_concept_ids.add(concept_id)
    if normalized.get("probability_count") != probability_count:
        raise ValueError("fresh shadow probability probability_count mismatch")

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
        raise ValueError("fresh shadow probability cannot enable runtime gates")
    if normalized.get("fresh_shadow_probability_snapshot_gate") is not True:
        raise ValueError("fresh shadow probability gate must be true")

    supplied_hash = str(
        normalized.get("fresh_pre_question_shadow_probability_snapshot_sha256")
        or ""
    )
    unhashed = _clone(normalized)
    unhashed.pop("fresh_pre_question_shadow_probability_snapshot_sha256", None)
    if supplied_hash != canonical_json_sha256(unhashed):
        raise ValueError("fresh shadow probability snapshot sha256 mismatch")
    return normalized
