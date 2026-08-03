"""Run or audit the deterministic J1-R2 lexical relevance baseline."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from neural.baby.candidate_universe import validate_candidate_vocabulary  # noqa: E402
from neural.baby.pending_question_semantics import canonical_json_sha256  # noqa: E402
from neural.baby.relevance_cohort_generator import (  # noqa: E402
    build_reviewed_development_label_pack,
    materialize_reviewed_development_manifest,
    validate_development_generator_spec,
    validate_development_review_decisions,
    validate_development_review_packet,
    validate_development_sample_size_plan,
)
from neural.baby.relevance_cohort_lifecycle import (  # noqa: E402
    validate_cohort_manifest,
    validate_cohort_manifest_readiness,
    validate_relevance_cohort_lifecycle_contract,
)
from neural.baby.relevance_lexical_baseline import (  # noqa: E402
    build_lexical_baseline_artifact,
    validate_lexical_baseline_artifact,
)


DEFAULT_VOCABULARY = (
    PROJECT_ROOT
    / "scripts"
    / "research"
    / "inputs"
    / "j1_1_candidate_vocabulary_v2_20260716.json"
)
DEFAULT_R1 = (
    PROJECT_ROOT
    / "claudedocs"
    / "research"
    / "j1_r1_relevance_scorer_contract_20260722.json"
)
DEFAULT_LIFECYCLE = (
    PROJECT_ROOT
    / "claudedocs"
    / "research"
    / "j1_r2_relevance_cohort_lifecycle_20260722.json"
)
DEFAULT_ANCHOR = (
    PROJECT_ROOT
    / "scripts"
    / "research"
    / "manifests"
    / "j1_r2_anchor_regression_manifest_20260722.json"
)
DEFAULT_DEVELOPMENT_DRAFT = (
    PROJECT_ROOT
    / "scripts"
    / "research"
    / "manifests"
    / "j1_r2_rolling_development_manifest_draft_20260722.json"
)
DEFAULT_SAMPLE_PLAN = (
    PROJECT_ROOT
    / "scripts"
    / "research"
    / "specs"
    / "j1_r2_rolling_development_sample_size_plan_draft_20260723.json"
)
DEFAULT_GENERATOR_SPEC = (
    PROJECT_ROOT
    / "scripts"
    / "research"
    / "specs"
    / "j1_r2_rolling_development_generator_spec_draft_20260723.json"
)
DEFAULT_REVIEW_PACKET = (
    PROJECT_ROOT
    / "scripts"
    / "research"
    / "inputs"
    / "j1_r2_rolling_development_review_packet_20260723.json"
)
DEFAULT_REVIEW_DECISIONS = (
    PROJECT_ROOT
    / "scripts"
    / "research"
    / "inputs"
    / "j1_r2_rolling_development_review_decisions_20260723.json"
)
DEFAULT_LABELS = (
    PROJECT_ROOT
    / "scripts"
    / "research"
    / "inputs"
    / "j1_r2_rolling_development_labels_reviewed_20260723.json"
)
DEFAULT_DEVELOPMENT = (
    PROJECT_ROOT
    / "scripts"
    / "research"
    / "manifests"
    / "j1_r2_rolling_development_manifest_reviewed_20260723.json"
)
DEFAULT_LOCKBOX = (
    PROJECT_ROOT
    / "scripts"
    / "research"
    / "manifests"
    / "j1_r2_one_time_lockbox_manifest_generator_frozen_20260723.json"
)
DEFAULT_READINESS = (
    PROJECT_ROOT
    / "claudedocs"
    / "research"
    / "j1_r2_relevance_cohort_readiness_after_lockbox_freeze_20260723.json"
)
DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "claudedocs"
    / "research"
    / "j1_r2_lexical_baseline_development_20260728.json"
)
BASELINE_MODULE = (
    PROJECT_ROOT / "neural" / "baby" / "relevance_lexical_baseline.py"
)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json_new(path: Path, payload: dict[str, Any]) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite existing artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _validated_inputs(args: argparse.Namespace) -> dict[str, Any]:
    vocabulary = validate_candidate_vocabulary(_load_json(args.vocabulary))
    r1 = _load_json(args.r1)
    lifecycle_raw = _load_json(args.lifecycle)
    lifecycle = validate_relevance_cohort_lifecycle_contract(
        lifecycle_raw,
        r1,
        graph_snapshot_sha256=lifecycle_raw["evaluation_epoch"][
            "graph_snapshot_sha256"
        ],
        legacy_question_hashes=lifecycle_raw["cohort_roles"][
            "anchor_regression"
        ]["question_hashes"],
    )
    anchor = validate_cohort_manifest(_load_json(args.anchor), lifecycle)
    sample_plan = validate_development_sample_size_plan(
        _load_json(args.sample_plan),
        lifecycle,
    )
    generator_spec = validate_development_generator_spec(
        _load_json(args.generator_spec),
        lifecycle,
        vocabulary,
        sample_plan,
        legacy_question_hashes=lifecycle["cohort_roles"]["anchor_regression"][
            "question_hashes"
        ],
    )
    review_packet = validate_development_review_packet(
        _load_json(args.review_packet),
        generator_spec,
        sample_plan,
    )
    review_decisions = validate_development_review_decisions(
        _load_json(args.review_decisions),
        review_packet,
    )
    labels = _load_json(args.labels)
    expected_labels = build_reviewed_development_label_pack(
        generator_spec,
        review_packet,
        review_decisions,
        created_at=str(labels.get("created_at") or ""),
    )
    if labels != expected_labels:
        raise ValueError("reviewed labels do not match approved generator mapping")

    development = _load_json(args.development)
    expected_development = materialize_reviewed_development_manifest(
        lifecycle,
        _load_json(args.development_draft),
        generator_spec,
        sample_plan,
        review_packet,
        review_decisions,
        labels,
        created_at=str(development.get("created_at") or ""),
    )
    if development != expected_development:
        raise ValueError("development manifest does not match reviewed inputs")
    lockbox = validate_cohort_manifest(_load_json(args.lockbox), lifecycle)
    readiness = validate_cohort_manifest_readiness(
        _load_json(args.readiness),
        lifecycle,
        [anchor, development, lockbox],
    )
    if readiness.get("lexical_baseline_execution_gate") is not True:
        raise ValueError("lexical baseline execution gate is not open")
    if readiness.get("block_reasons"):
        raise ValueError("lexical baseline readiness has block reasons")
    return {
        "vocabulary": vocabulary,
        "r1": r1,
        "lifecycle": lifecycle,
        "anchor": anchor,
        "sample_plan": sample_plan,
        "generator_spec": generator_spec,
        "review_packet": review_packet,
        "review_decisions": review_decisions,
        "labels": labels,
        "development": development,
        "lockbox": lockbox,
        "readiness": readiness,
    }


def _bindings(args: argparse.Namespace, inputs: dict[str, Any]) -> dict[str, Any]:
    input_paths = {
        "candidate_vocabulary": args.vocabulary,
        "r1_contract": args.r1,
        "lifecycle_contract": args.lifecycle,
        "anchor_manifest": args.anchor,
        "development_draft_manifest": args.development_draft,
        "development_sample_plan": args.sample_plan,
        "development_generator_spec": args.generator_spec,
        "development_review_packet": args.review_packet,
        "development_review_decisions": args.review_decisions,
        "development_labels": args.labels,
        "development_manifest": args.development,
        "lockbox_generator_manifest": args.lockbox,
        "cohort_readiness": args.readiness,
        "baseline_module": BASELINE_MODULE,
        "baseline_cli": Path(__file__).resolve(),
    }
    implementation_files = {
        "baseline_module": _file_sha256(BASELINE_MODULE),
        "baseline_cli": _file_sha256(Path(__file__).resolve()),
    }
    return {
        "candidate_vocabulary_sha256": inputs["vocabulary"][
            "candidate_vocabulary_sha256"
        ],
        "r1_contract_sha256": inputs["r1"][
            "relevance_scorer_contract_sha256"
        ],
        "cohort_lifecycle_contract_sha256": inputs["lifecycle"][
            "cohort_lifecycle_contract_sha256"
        ],
        "development_label_pack_sha256": inputs["labels"][
            "development_label_pack_sha256"
        ],
        "development_manifest_sha256": inputs["development"][
            "cohort_manifest_sha256"
        ],
        "lockbox_generator_manifest_sha256": inputs["lockbox"][
            "cohort_manifest_sha256"
        ],
        "cohort_readiness_sha256": inputs["readiness"][
            "cohort_readiness_sha256"
        ],
        "implementation_bundle_sha256": canonical_json_sha256(
            implementation_files
        ),
        "input_file_sha256s": {
            name: _file_sha256(path) for name, path in sorted(input_paths.items())
        },
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    inputs = _validated_inputs(args)
    artifact = build_lexical_baseline_artifact(
        inputs["vocabulary"],
        inputs["generator_spec"],
        inputs["labels"],
        bindings=_bindings(args, inputs),
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    validate_lexical_baseline_artifact(
        artifact,
        inputs["vocabulary"],
        inputs["generator_spec"],
        inputs["labels"],
    )
    _write_json_new(args.output, artifact)
    return artifact


def audit_existing(args: argparse.Namespace) -> dict[str, Any]:
    inputs = _validated_inputs(args)
    artifact = validate_lexical_baseline_artifact(
        _load_json(args.output),
        inputs["vocabulary"],
        inputs["generator_spec"],
        inputs["labels"],
    )
    if artifact["bindings"] != _bindings(args, inputs):
        raise ValueError("artifact file or implementation binding drift")
    return artifact


def _summary(artifact: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": artifact["status"],
        "baseline_id": artifact["baseline_id"],
        "candidate_count": artifact["candidate_count"],
        "question_count": artifact["question_count"],
        "aggregate_metrics": artifact["aggregate_metrics"],
        "partition_metrics": artifact["partition_metrics"],
        "surface_overlap_diagnostic": artifact["surface_overlap_diagnostic"],
        "heldout_gate": artifact["heldout_gate"],
        "performance_claim_gate": artifact["performance_claim_gate"],
        "production_promotion_gate": artifact["production_promotion_gate"],
        "next_step": artifact["next_step"],
        "lexical_baseline_artifact_sha256": artifact[
            "lexical_baseline_artifact_sha256"
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("run", "audit-existing"))
    parser.add_argument("--vocabulary", type=Path, default=DEFAULT_VOCABULARY)
    parser.add_argument("--r1", type=Path, default=DEFAULT_R1)
    parser.add_argument("--lifecycle", type=Path, default=DEFAULT_LIFECYCLE)
    parser.add_argument("--anchor", type=Path, default=DEFAULT_ANCHOR)
    parser.add_argument(
        "--development-draft",
        type=Path,
        default=DEFAULT_DEVELOPMENT_DRAFT,
    )
    parser.add_argument("--sample-plan", type=Path, default=DEFAULT_SAMPLE_PLAN)
    parser.add_argument(
        "--generator-spec",
        type=Path,
        default=DEFAULT_GENERATOR_SPEC,
    )
    parser.add_argument(
        "--review-packet",
        type=Path,
        default=DEFAULT_REVIEW_PACKET,
    )
    parser.add_argument(
        "--review-decisions",
        type=Path,
        default=DEFAULT_REVIEW_DECISIONS,
    )
    parser.add_argument("--labels", type=Path, default=DEFAULT_LABELS)
    parser.add_argument("--development", type=Path, default=DEFAULT_DEVELOPMENT)
    parser.add_argument("--lockbox", type=Path, default=DEFAULT_LOCKBOX)
    parser.add_argument("--readiness", type=Path, default=DEFAULT_READINESS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args()
    artifact = run(args) if args.action == "run" else audit_existing(args)
    print(json.dumps(_summary(artifact), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

