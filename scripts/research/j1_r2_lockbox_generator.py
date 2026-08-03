"""Seal, audit, review, and freeze the J1-R2 lockbox generator contract."""

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

from neural.baby.candidate_universe import (  # noqa: E402
    validate_candidate_vocabulary,
)
from neural.baby.pending_question_semantics import (  # noqa: E402
    canonical_json_sha256,
)
from neural.baby.relevance_cohort_lifecycle import (  # noqa: E402
    build_cohort_manifest_readiness,
    validate_cohort_manifest,
    validate_cohort_manifest_readiness,
)
from neural.baby.relevance_lockbox_generator import (  # noqa: E402
    REVIEW_ITEM_IDS,
    build_lockbox_generator_spec,
    build_lockbox_review_packet,
    build_lockbox_sample_size_plan,
    freeze_lockbox_generator_manifest,
    validate_lockbox_generator_spec,
    validate_lockbox_review_decisions,
    validate_lockbox_review_packet,
    validate_lockbox_sample_size_plan,
)


DEFAULT_LIFECYCLE = (
    PROJECT_ROOT / "claudedocs" / "research"
    / "j1_r2_relevance_cohort_lifecycle_20260722.json"
)
DEFAULT_VOCABULARY = (
    PROJECT_ROOT / "scripts" / "research" / "inputs"
    / "j1_1_candidate_vocabulary_v2_20260716.json"
)
DEFAULT_ANCHOR = (
    PROJECT_ROOT / "scripts" / "research" / "manifests"
    / "j1_r2_anchor_regression_manifest_20260722.json"
)
DEFAULT_DEVELOPMENT = (
    PROJECT_ROOT / "scripts" / "research" / "manifests"
    / "j1_r2_rolling_development_manifest_reviewed_20260723.json"
)
DEFAULT_LOCKBOX_DRAFT = (
    PROJECT_ROOT / "scripts" / "research" / "manifests"
    / "j1_r2_one_time_lockbox_manifest_draft_20260722.json"
)
DEFAULT_SAMPLE_PLAN = (
    PROJECT_ROOT / "scripts" / "research" / "specs"
    / "j1_r2_one_time_lockbox_sample_size_plan_draft_20260723.json"
)
DEFAULT_GENERATOR_SPEC = (
    PROJECT_ROOT / "scripts" / "research" / "specs"
    / "j1_r2_one_time_lockbox_generator_spec_draft_20260723.json"
)
DEFAULT_REVIEW_PACKET = (
    PROJECT_ROOT / "scripts" / "research" / "inputs"
    / "j1_r2_one_time_lockbox_review_packet_20260723.json"
)
DEFAULT_REVIEW_DECISIONS = (
    PROJECT_ROOT / "scripts" / "research" / "inputs"
    / "j1_r2_one_time_lockbox_review_decisions_20260723.json"
)
DEFAULT_FROZEN_MANIFEST = (
    PROJECT_ROOT / "scripts" / "research" / "manifests"
    / "j1_r2_one_time_lockbox_manifest_generator_frozen_20260723.json"
)
DEFAULT_READINESS = (
    PROJECT_ROOT / "claudedocs" / "research"
    / "j1_r2_relevance_cohort_readiness_after_lockbox_freeze_20260723.json"
)
GENERATOR_MODULE = (
    PROJECT_ROOT / "neural" / "baby" / "relevance_lockbox_generator.py"
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


def _context(args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, Any]]:
    lifecycle = _load_json(args.lifecycle)
    vocabulary = validate_candidate_vocabulary(_load_json(args.vocabulary))
    if vocabulary["candidate_vocabulary_sha256"] != lifecycle[
        "evaluation_epoch"
    ]["candidate_vocabulary_sha256"]:
        raise ValueError("candidate vocabulary does not match lifecycle")
    return lifecycle, vocabulary


def seal_review_bundle(args: argparse.Namespace) -> dict[str, Any]:
    lifecycle, vocabulary = _context(args)
    created_at = datetime.now(timezone.utc).isoformat()
    plan = build_lockbox_sample_size_plan(lifecycle, created_at=created_at)
    spec = build_lockbox_generator_spec(
        lifecycle,
        plan,
        candidate_vocabulary_sha256=vocabulary[
            "candidate_vocabulary_sha256"
        ],
        implementation_sha256=_file_sha256(GENERATOR_MODULE),
        created_at=created_at,
    )
    packet = build_lockbox_review_packet(
        spec, plan, created_at=created_at
    )
    for path in (args.sample_plan, args.generator_spec, args.review_packet):
        if path.exists():
            raise FileExistsError(f"refusing to overwrite existing artifact: {path}")
    _write_json_new(args.sample_plan, plan)
    _write_json_new(args.generator_spec, spec)
    _write_json_new(args.review_packet, packet)
    return {
        "sample_plan": plan,
        "generator_spec": spec,
        "review_packet": packet,
    }


def audit_review_bundle(args: argparse.Namespace) -> dict[str, Any]:
    lifecycle, _ = _context(args)
    plan = validate_lockbox_sample_size_plan(
        _load_json(args.sample_plan), lifecycle
    )
    implementation_hash = _file_sha256(GENERATOR_MODULE)
    spec = validate_lockbox_generator_spec(
        _load_json(args.generator_spec),
        lifecycle,
        plan,
        implementation_sha256=implementation_hash,
    )
    packet = validate_lockbox_review_packet(
        _load_json(args.review_packet), spec, plan
    )
    return {
        "sample_plan": plan,
        "generator_spec": spec,
        "review_packet": packet,
    }


def seal_approved_decisions(args: argparse.Namespace) -> dict[str, Any]:
    packet = audit_review_bundle(args)["review_packet"]
    decisions = {
        "lockbox_review_decisions_version": 1,
        "phase": "J1-R2",
        "lockbox_review_packet_sha256": packet[
            "lockbox_review_packet_sha256"
        ],
        "reviewer_role": "user",
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "overall_decision": "approved",
        "approval_basis": {
            "source": "explicit_user_message",
            "approved_as_sealed": True,
            "content_modifications": [
                (
                    "clarified_24_question_distribution_not_exact_question_"
                    "approval"
                ),
                (
                    "required_source_bank_review_provenance_and_zero_overlap_"
                    "audit"
                ),
            ],
        },
        "decisions": [
            {"review_item_id": item_id, "decision": "approved"}
            for item_id in REVIEW_ITEM_IDS
        ],
    }
    decisions["lockbox_review_decisions_sha256"] = canonical_json_sha256(
        decisions
    )
    validated = validate_lockbox_review_decisions(decisions, packet)
    _write_json_new(args.review_decisions, validated)
    return {"review_decisions": validated}


def freeze_generator(args: argparse.Namespace) -> dict[str, Any]:
    lifecycle, _ = _context(args)
    bundle = audit_review_bundle(args)
    decisions = validate_lockbox_review_decisions(
        _load_json(args.review_decisions), bundle["review_packet"]
    )
    frozen = freeze_lockbox_generator_manifest(
        lifecycle,
        _load_json(args.lockbox_draft),
        bundle["generator_spec"],
        bundle["sample_plan"],
        bundle["review_packet"],
        decisions,
        implementation_sha256=_file_sha256(GENERATOR_MODULE),
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    anchor = validate_cohort_manifest(_load_json(args.anchor), lifecycle)
    development = validate_cohort_manifest(
        _load_json(args.development), lifecycle
    )
    readiness = build_cohort_manifest_readiness(
        lifecycle, [anchor, development, frozen]
    )
    for path in (args.frozen_manifest, args.readiness):
        if path.exists():
            raise FileExistsError(f"refusing to overwrite existing artifact: {path}")
    _write_json_new(args.frozen_manifest, frozen)
    _write_json_new(args.readiness, readiness)
    return {"frozen_manifest": frozen, "readiness": readiness}


def audit_frozen_generator(args: argparse.Namespace) -> dict[str, Any]:
    lifecycle, _ = _context(args)
    bundle = audit_review_bundle(args)
    decisions = validate_lockbox_review_decisions(
        _load_json(args.review_decisions), bundle["review_packet"]
    )
    frozen = _load_json(args.frozen_manifest)
    expected = freeze_lockbox_generator_manifest(
        lifecycle,
        _load_json(args.lockbox_draft),
        bundle["generator_spec"],
        bundle["sample_plan"],
        bundle["review_packet"],
        decisions,
        implementation_sha256=_file_sha256(GENERATOR_MODULE),
        created_at=str(frozen.get("created_at") or ""),
    )
    if frozen != expected:
        raise ValueError("frozen lockbox manifest does not match approved contract")
    anchor = validate_cohort_manifest(_load_json(args.anchor), lifecycle)
    development = validate_cohort_manifest(
        _load_json(args.development), lifecycle
    )
    readiness = validate_cohort_manifest_readiness(
        _load_json(args.readiness),
        lifecycle,
        [anchor, development, frozen],
    )
    return {"frozen_manifest": frozen, "readiness": readiness}


def _summary(payload: Mapping[str, Any]) -> dict[str, Any]:
    if "review_packet" in payload:
        plan = payload["sample_plan"]
        spec = payload["generator_spec"]
        packet = payload["review_packet"]
        return {
            "lockbox_sample_size_plan_sha256": plan[
                "lockbox_sample_size_plan_sha256"
            ],
            "lockbox_generator_spec_sha256": spec[
                "lockbox_generator_spec_sha256"
            ],
            "implementation_sha256": spec["input_bindings"][
                "implementation_sha256"
            ],
            "lockbox_review_packet_sha256": packet[
                "lockbox_review_packet_sha256"
            ],
            "question_count": plan["question_count"],
            "target_partition_counts": plan["target_partition_counts"],
            "review_gate": packet["review_gate"],
            "generator_freeze_gate": packet["generator_freeze_gate"],
            "next_step": packet["next_step"],
        }
    if "frozen_manifest" not in payload:
        decisions = payload["review_decisions"]
        return {
            "lockbox_review_decisions_sha256": decisions[
                "lockbox_review_decisions_sha256"
            ],
            "overall_decision": decisions["overall_decision"],
            "approved_review_item_count": len(decisions["decisions"]),
        }
    return {
        "lockbox_manifest_sha256": payload["frozen_manifest"][
            "cohort_manifest_sha256"
        ],
        "lockbox_generator_manifest_gate": payload["readiness"][
            "lockbox_generator_manifest_gate"
        ],
        "lexical_baseline_execution_gate": payload["readiness"][
            "lexical_baseline_execution_gate"
        ],
        "lockbox_materialization_gate": payload["frozen_manifest"][
            "execution_gate"
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
            "freeze-generator",
            "audit-frozen-generator",
        ),
    )
    parser.add_argument("--lifecycle", type=Path, default=DEFAULT_LIFECYCLE)
    parser.add_argument("--vocabulary", type=Path, default=DEFAULT_VOCABULARY)
    parser.add_argument("--anchor", type=Path, default=DEFAULT_ANCHOR)
    parser.add_argument("--development", type=Path, default=DEFAULT_DEVELOPMENT)
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
        "--frozen-manifest", type=Path, default=DEFAULT_FROZEN_MANIFEST
    )
    parser.add_argument("--readiness", type=Path, default=DEFAULT_READINESS)
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
    elif args.action == "freeze-generator":
        result = freeze_generator(args)
    else:
        result = audit_frozen_generator(args)
    print(json.dumps(_summary(result), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
