"""Seal, audit, and materialize the J1-R2 development generator."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from neural.baby.answer_source import (  # noqa: E402
    validate_answer_source_amendment,
    validate_reference_answer_pack,
)
from neural.baby.candidate_universe import (  # noqa: E402
    validate_candidate_vocabulary,
    validate_independent_score_capture,
    validate_union_label_pack,
)
from neural.baby.pending_question_semantics import (  # noqa: E402
    canonical_json_sha256,
)
from neural.baby.question_calibration import (  # noqa: E402
    validate_preregistered_manifest,
)
from neural.baby.relevance_cohort_generator import (  # noqa: E402
    build_development_generator_spec,
    build_development_review_packet,
    build_development_sample_size_plan,
    build_reviewed_development_label_pack,
    materialize_reviewed_development_manifest,
    validate_development_generator_spec,
    validate_development_review_decisions,
    validate_development_review_packet,
    validate_development_sample_size_plan,
)
from neural.baby.relevance_cohort_lifecycle import (  # noqa: E402
    build_cohort_manifest_readiness,
    validate_cohort_manifest,
    validate_cohort_manifest_readiness,
    validate_relevance_cohort_lifecycle_contract,
)
from neural.baby.relevance_scorer_contract import (  # noqa: E402
    validate_relevance_scorer_contract,
)


DEFAULT_TRAIN_MANIFEST = (
    PROJECT_ROOT / "scripts" / "research" / "manifests"
    / "j1_1_train_calibration_a_20260716.json"
)
DEFAULT_RAW_PACK = (
    PROJECT_ROOT / "scripts" / "research" / "inputs"
    / "j1_1_train_calibration_a_20260716_raw_scores_sealed.json"
)
DEFAULT_AMENDMENT = (
    PROJECT_ROOT / "scripts" / "research" / "inputs"
    / "j1_1_answer_source_amendment_20260716.json"
)
DEFAULT_ANSWERS = (
    PROJECT_ROOT / "scripts" / "research" / "inputs"
    / "j1_1_teacher_answers_reviewed_20260716.json"
)
DEFAULT_VOCABULARY = (
    PROJECT_ROOT / "scripts" / "research" / "inputs"
    / "j1_1_candidate_vocabulary_v2_20260716.json"
)
DEFAULT_CAPTURE = (
    PROJECT_ROOT / "scripts" / "research" / "inputs"
    / "j1_1_candidate_universe_v2_raw_scores_20260716.json"
)
DEFAULT_LABELS = (
    PROJECT_ROOT / "scripts" / "research" / "inputs"
    / "j1_1_candidate_universe_v2_labels_reviewed_20260718.json"
)
DEFAULT_R1 = (
    PROJECT_ROOT / "claudedocs" / "research"
    / "j1_r1_relevance_scorer_contract_20260722.json"
)
DEFAULT_LIFECYCLE = (
    PROJECT_ROOT / "claudedocs" / "research"
    / "j1_r2_relevance_cohort_lifecycle_20260722.json"
)
DEFAULT_ANCHOR = (
    PROJECT_ROOT / "scripts" / "research" / "manifests"
    / "j1_r2_anchor_regression_manifest_20260722.json"
)
DEFAULT_DEVELOPMENT_DRAFT = (
    PROJECT_ROOT / "scripts" / "research" / "manifests"
    / "j1_r2_rolling_development_manifest_draft_20260722.json"
)
DEFAULT_LOCKBOX_DRAFT = (
    PROJECT_ROOT / "scripts" / "research" / "manifests"
    / "j1_r2_one_time_lockbox_manifest_draft_20260722.json"
)
DEFAULT_SAMPLE_PLAN = (
    PROJECT_ROOT / "scripts" / "research" / "specs"
    / "j1_r2_rolling_development_sample_size_plan_draft_20260723.json"
)
DEFAULT_GENERATOR_SPEC = (
    PROJECT_ROOT / "scripts" / "research" / "specs"
    / "j1_r2_rolling_development_generator_spec_draft_20260723.json"
)
DEFAULT_REVIEW_PACKET = (
    PROJECT_ROOT / "scripts" / "research" / "inputs"
    / "j1_r2_rolling_development_review_packet_20260723.json"
)
DEFAULT_REVIEW_DECISIONS = (
    PROJECT_ROOT / "scripts" / "research" / "inputs"
    / "j1_r2_rolling_development_review_decisions_20260723.json"
)
DEFAULT_REVIEWED_LABELS = (
    PROJECT_ROOT / "scripts" / "research" / "inputs"
    / "j1_r2_rolling_development_labels_reviewed_20260723.json"
)
DEFAULT_MATERIALIZED_DEVELOPMENT = (
    PROJECT_ROOT / "scripts" / "research" / "manifests"
    / "j1_r2_rolling_development_manifest_reviewed_20260723.json"
)
DEFAULT_SUCCESSOR_READINESS = (
    PROJECT_ROOT / "claudedocs" / "research"
    / "j1_r2_relevance_cohort_readiness_after_development_20260723.json"
)
GENERATOR_MODULE = (
    PROJECT_ROOT / "neural" / "baby" / "relevance_cohort_generator.py"
)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json_new(path: Path, payload: Mapping[str, Any]) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite existing artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _validated_context(
    args: argparse.Namespace,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    train_manifest = validate_preregistered_manifest(
        _load_json(args.train_manifest)
    )
    raw_pack = _load_json(args.raw_pack)
    amendment = validate_answer_source_amendment(
        train_manifest, raw_pack, _load_json(args.amendment)
    )
    answers = validate_reference_answer_pack(
        train_manifest, raw_pack, amendment, _load_json(args.answers)
    )
    vocabulary = validate_candidate_vocabulary(_load_json(args.vocabulary))
    capture = validate_independent_score_capture(
        vocabulary, _load_json(args.capture)
    )
    labels = validate_union_label_pack(
        capture, answers, _load_json(args.labels), require_user_review=True
    )
    r1 = validate_relevance_scorer_contract(
        _load_json(args.r1), vocabulary, capture, answers, labels
    )
    lifecycle = validate_relevance_cohort_lifecycle_contract(
        _load_json(args.lifecycle),
        r1,
        graph_snapshot_sha256=vocabulary["graph_snapshot_sha256"],
        legacy_question_hashes=[
            item["question_sha256"] for item in train_manifest["questions"]
        ],
    )
    return train_manifest, vocabulary, r1, lifecycle


def _legacy_question_hashes(train_manifest: Mapping[str, Any]) -> list[str]:
    return [str(item["question_sha256"]) for item in train_manifest["questions"]]


def seal_review_bundle(args: argparse.Namespace) -> dict[str, Any]:
    train_manifest, vocabulary, _, lifecycle = _validated_context(args)
    created_at = datetime.now(timezone.utc).isoformat()
    sample_plan = build_development_sample_size_plan(
        lifecycle, created_at=created_at
    )
    spec = build_development_generator_spec(
        lifecycle,
        vocabulary,
        sample_plan,
        implementation_sha256=_file_sha256(GENERATOR_MODULE),
        created_at=created_at,
    )
    validate_development_generator_spec(
        spec,
        lifecycle,
        vocabulary,
        sample_plan,
        legacy_question_hashes=_legacy_question_hashes(train_manifest),
    )
    packet = build_development_review_packet(
        spec, sample_plan, created_at=created_at
    )
    for path in (args.sample_plan, args.generator_spec, args.review_packet):
        if path.exists():
            raise FileExistsError(f"refusing to overwrite existing artifact: {path}")
    _write_json_new(args.sample_plan, sample_plan)
    _write_json_new(args.generator_spec, spec)
    _write_json_new(args.review_packet, packet)
    return {
        "sample_plan": sample_plan,
        "generator_spec": spec,
        "review_packet": packet,
    }


def audit_review_bundle(args: argparse.Namespace) -> dict[str, Any]:
    train_manifest, vocabulary, _, lifecycle = _validated_context(args)
    sample_plan = validate_development_sample_size_plan(
        _load_json(args.sample_plan), lifecycle
    )
    spec = validate_development_generator_spec(
        _load_json(args.generator_spec),
        lifecycle,
        vocabulary,
        sample_plan,
        legacy_question_hashes=_legacy_question_hashes(train_manifest),
    )
    if spec["implementation_sha256"] != _file_sha256(GENERATOR_MODULE):
        raise ValueError("generator implementation hash drift")
    packet = validate_development_review_packet(
        _load_json(args.review_packet), spec, sample_plan
    )
    return {
        "sample_plan": sample_plan,
        "generator_spec": spec,
        "review_packet": packet,
    }


def seal_approved_decisions(args: argparse.Namespace) -> dict[str, Any]:
    bundle = audit_review_bundle(args)
    packet = bundle["review_packet"]
    decisions = {
        "review_decisions_version": 1,
        "phase": "J1-R2",
        "review_packet_sha256": packet["review_packet_sha256"],
        "reviewer_role": "user",
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "overall_decision": "approved",
        "approval_basis": {
            "source": "explicit_user_message",
            "approved_as_sealed": True,
            "content_modifications": [],
            "positive_context_negative_mapping": "approved_as_sealed",
        },
        "decisions": [
            {
                "question_id": item["question_id"],
                "decision": "approved",
            }
            for item in packet["questions"]
        ],
    }
    decisions["review_decisions_sha256"] = canonical_json_sha256(decisions)
    validated = validate_development_review_decisions(decisions, packet)
    _write_json_new(args.review_decisions, validated)
    return {"review_decisions": validated}


def materialize_development(args: argparse.Namespace) -> dict[str, Any]:
    _, _, _, lifecycle = _validated_context(args)
    bundle = audit_review_bundle(args)
    sample_plan = bundle["sample_plan"]
    spec = bundle["generator_spec"]
    packet = bundle["review_packet"]
    decisions = validate_development_review_decisions(
        _load_json(args.review_decisions), packet
    )
    created_at = datetime.now(timezone.utc).isoformat()
    label_pack = build_reviewed_development_label_pack(
        spec, packet, decisions, created_at=created_at
    )
    development = materialize_reviewed_development_manifest(
        lifecycle,
        _load_json(args.development_draft),
        spec,
        sample_plan,
        packet,
        decisions,
        label_pack,
        created_at=created_at,
    )
    anchor = validate_cohort_manifest(_load_json(args.anchor), lifecycle)
    lockbox = validate_cohort_manifest(_load_json(args.lockbox_draft), lifecycle)
    readiness = build_cohort_manifest_readiness(
        lifecycle, [anchor, development, lockbox]
    )
    for path in (
        args.reviewed_labels,
        args.materialized_development,
        args.successor_readiness,
    ):
        if path.exists():
            raise FileExistsError(f"refusing to overwrite existing artifact: {path}")
    _write_json_new(args.reviewed_labels, label_pack)
    _write_json_new(args.materialized_development, development)
    _write_json_new(args.successor_readiness, readiness)
    return {
        "review_decisions": decisions,
        "reviewed_labels": label_pack,
        "development_manifest": development,
        "readiness": readiness,
    }


def audit_materialized_development(
    args: argparse.Namespace,
) -> dict[str, Any]:
    _, _, _, lifecycle = _validated_context(args)
    bundle = audit_review_bundle(args)
    sample_plan = bundle["sample_plan"]
    spec = bundle["generator_spec"]
    packet = bundle["review_packet"]
    decisions = validate_development_review_decisions(
        _load_json(args.review_decisions), packet
    )
    labels = _load_json(args.reviewed_labels)
    expected_labels = build_reviewed_development_label_pack(
        spec,
        packet,
        decisions,
        created_at=str(labels.get("created_at") or ""),
    )
    if labels != expected_labels:
        raise ValueError("reviewed label pack does not match approved mapping")

    development = _load_json(args.materialized_development)
    expected_development = materialize_reviewed_development_manifest(
        lifecycle,
        _load_json(args.development_draft),
        spec,
        sample_plan,
        packet,
        decisions,
        labels,
        created_at=str(development.get("created_at") or ""),
    )
    if development != expected_development:
        raise ValueError("development manifest does not match approved artifacts")

    anchor = validate_cohort_manifest(_load_json(args.anchor), lifecycle)
    lockbox = validate_cohort_manifest(_load_json(args.lockbox_draft), lifecycle)
    readiness = validate_cohort_manifest_readiness(
        _load_json(args.successor_readiness),
        lifecycle,
        [anchor, development, lockbox],
    )
    return {
        "review_decisions": decisions,
        "reviewed_labels": labels,
        "development_manifest": development,
        "readiness": readiness,
    }


def _summary(payload: Mapping[str, Any]) -> dict[str, Any]:
    if "review_packet" in payload:
        packet = payload["review_packet"]
        spec = payload["generator_spec"]
        plan = payload["sample_plan"]
        return {
            "sample_size_plan_sha256": plan["sample_size_plan_sha256"],
            "generator_spec_sha256": spec["generator_spec_sha256"],
            "implementation_sha256": spec["implementation_sha256"],
            "review_packet_sha256": packet["review_packet_sha256"],
            "question_count": packet["question_count"],
            "positive_label_count": packet["positive_label_count"],
            "explicit_negative_label_count": packet[
                "explicit_negative_label_count"
            ],
            "review_gate": packet["review_gate"],
            "materialization_gate": packet["materialization_gate"],
            "next_step": packet["next_step"],
        }
    if "development_manifest" not in payload:
        decisions = payload["review_decisions"]
        return {
            "review_decisions_sha256": decisions[
                "review_decisions_sha256"
            ],
            "overall_decision": decisions["overall_decision"],
            "approved_question_count": len(decisions["decisions"]),
            "content_modifications": decisions["approval_basis"][
                "content_modifications"
            ],
            "positive_context_negative_mapping": decisions["approval_basis"][
                "positive_context_negative_mapping"
            ],
        }
    return {
        "development_manifest_sha256": payload["development_manifest"][
            "cohort_manifest_sha256"
        ],
        "development_label_pack_sha256": payload["reviewed_labels"][
            "development_label_pack_sha256"
        ],
        "development_manifest_gate": payload["readiness"][
            "development_manifest_gate"
        ],
        "lockbox_generator_manifest_gate": payload["readiness"][
            "lockbox_generator_manifest_gate"
        ],
        "lexical_baseline_execution_gate": payload["readiness"][
            "lexical_baseline_execution_gate"
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=(
            "seal-review-bundle",
            "audit-review-bundle",
            "seal-approved-decisions",
            "materialize-development",
            "audit-materialized-development",
        ),
    )
    parser.add_argument(
        "--train-manifest", type=Path, default=DEFAULT_TRAIN_MANIFEST
    )
    parser.add_argument("--raw-pack", type=Path, default=DEFAULT_RAW_PACK)
    parser.add_argument("--amendment", type=Path, default=DEFAULT_AMENDMENT)
    parser.add_argument("--answers", type=Path, default=DEFAULT_ANSWERS)
    parser.add_argument("--vocabulary", type=Path, default=DEFAULT_VOCABULARY)
    parser.add_argument("--capture", type=Path, default=DEFAULT_CAPTURE)
    parser.add_argument("--labels", type=Path, default=DEFAULT_LABELS)
    parser.add_argument("--r1", type=Path, default=DEFAULT_R1)
    parser.add_argument("--lifecycle", type=Path, default=DEFAULT_LIFECYCLE)
    parser.add_argument("--anchor", type=Path, default=DEFAULT_ANCHOR)
    parser.add_argument(
        "--development-draft", type=Path, default=DEFAULT_DEVELOPMENT_DRAFT
    )
    parser.add_argument(
        "--lockbox-draft", type=Path, default=DEFAULT_LOCKBOX_DRAFT
    )
    parser.add_argument("--sample-plan", type=Path, default=DEFAULT_SAMPLE_PLAN)
    parser.add_argument(
        "--generator-spec", type=Path, default=DEFAULT_GENERATOR_SPEC
    )
    parser.add_argument(
        "--review-packet", type=Path, default=DEFAULT_REVIEW_PACKET
    )
    parser.add_argument(
        "--review-decisions", type=Path, default=DEFAULT_REVIEW_DECISIONS
    )
    parser.add_argument(
        "--reviewed-labels", type=Path, default=DEFAULT_REVIEWED_LABELS
    )
    parser.add_argument(
        "--materialized-development",
        type=Path,
        default=DEFAULT_MATERIALIZED_DEVELOPMENT,
    )
    parser.add_argument(
        "--successor-readiness", type=Path, default=DEFAULT_SUCCESSOR_READINESS
    )
    return parser.parse_args()


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args()
    if args.action == "seal-review-bundle":
        result = seal_review_bundle(args)
    elif args.action == "audit-review-bundle":
        result = audit_review_bundle(args)
    elif args.action == "seal-approved-decisions":
        result = seal_approved_decisions(args)
    elif args.action == "materialize-development":
        result = materialize_development(args)
    else:
        result = audit_materialized_development(args)
    print(json.dumps(_summary(result), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
