"""Seal and audit rotating J1-R2 relevance evaluation cohorts."""

from __future__ import annotations

import argparse
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
from neural.baby.question_calibration import (  # noqa: E402
    validate_preregistered_manifest,
)
from neural.baby.relevance_cohort_lifecycle import (  # noqa: E402
    build_anchor_manifest,
    build_cohort_manifest_readiness,
    build_planned_generator_manifest,
    build_relevance_cohort_lifecycle_contract,
    validate_cohort_manifest,
    validate_cohort_manifest_readiness,
    validate_relevance_cohort_lifecycle_contract,
)
from neural.baby.relevance_scorer_contract import (  # noqa: E402
    validate_relevance_scorer_contract,
)


DEFAULT_MANIFEST = (
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
DEFAULT_DEVELOPMENT = (
    PROJECT_ROOT / "scripts" / "research" / "manifests"
    / "j1_r2_rolling_development_manifest_draft_20260722.json"
)
DEFAULT_LOCKBOX = (
    PROJECT_ROOT / "scripts" / "research" / "manifests"
    / "j1_r2_one_time_lockbox_manifest_draft_20260722.json"
)
DEFAULT_READINESS = (
    PROJECT_ROOT / "claudedocs" / "research"
    / "j1_r2_relevance_cohort_readiness_20260722.json"
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


def _validated_context(
    args: argparse.Namespace,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    manifest = validate_preregistered_manifest(_load_json(args.manifest))
    raw_pack = _load_json(args.raw_pack)
    amendment = validate_answer_source_amendment(
        manifest, raw_pack, _load_json(args.amendment)
    )
    answers = validate_reference_answer_pack(
        manifest, raw_pack, amendment, _load_json(args.answers)
    )
    vocabulary = validate_candidate_vocabulary(_load_json(args.vocabulary))
    capture = validate_independent_score_capture(vocabulary, _load_json(args.capture))
    labels = validate_union_label_pack(
        capture, answers, _load_json(args.labels), require_user_review=True
    )
    r1 = validate_relevance_scorer_contract(
        _load_json(args.r1), vocabulary, capture, answers, labels
    )
    if vocabulary["manifest_contract_sha256"] != manifest["contract_sha256"]:
        raise ValueError("vocabulary and manifest are not bound")
    return manifest, vocabulary, r1


def _lifecycle_inputs(
    manifest: Mapping[str, Any], vocabulary: Mapping[str, Any]
) -> dict[str, Any]:
    return {
        "graph_snapshot_sha256": vocabulary["graph_snapshot_sha256"],
        "legacy_question_hashes": [
            item["question_sha256"] for item in manifest["questions"]
        ],
    }


def seal_lifecycle(args: argparse.Namespace) -> dict[str, Any]:
    manifest, vocabulary, r1 = _validated_context(args)
    inputs = _lifecycle_inputs(manifest, vocabulary)
    artifact = build_relevance_cohort_lifecycle_contract(
        r1,
        **inputs,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    _write_json_new(args.lifecycle, artifact)
    return artifact


def _validated_lifecycle(args: argparse.Namespace) -> dict[str, Any]:
    manifest, vocabulary, r1 = _validated_context(args)
    return validate_relevance_cohort_lifecycle_contract(
        _load_json(args.lifecycle),
        r1,
        **_lifecycle_inputs(manifest, vocabulary),
    )


def seal_manifests(args: argparse.Namespace) -> dict[str, Any]:
    lifecycle = _validated_lifecycle(args)
    created_at = datetime.now(timezone.utc).isoformat()
    anchor = build_anchor_manifest(lifecycle, created_at=created_at)
    development = build_planned_generator_manifest(
        lifecycle,
        role="rolling_development",
        cohort_id="j1-r2-rolling-development-0001",
        cohort_generation_id="development-generation-0001",
        created_at=created_at,
    )
    lockbox = build_planned_generator_manifest(
        lifecycle,
        role="one_time_lockbox",
        cohort_id="j1-r2-one-time-lockbox-0001",
        cohort_generation_id="lockbox-generation-0001",
        created_at=created_at,
    )
    for path in (args.anchor, args.development, args.lockbox, args.readiness):
        if path.exists():
            raise FileExistsError(f"refusing to overwrite existing artifact: {path}")
    _write_json_new(args.anchor, anchor)
    _write_json_new(args.development, development)
    _write_json_new(args.lockbox, lockbox)
    readiness = build_cohort_manifest_readiness(
        lifecycle, [anchor, development, lockbox]
    )
    _write_json_new(args.readiness, readiness)
    return readiness


def audit_existing(args: argparse.Namespace) -> dict[str, Any]:
    lifecycle = _validated_lifecycle(args)
    manifests = [
        validate_cohort_manifest(_load_json(path), lifecycle)
        for path in (args.anchor, args.development, args.lockbox)
    ]
    stored = validate_cohort_manifest_readiness(
        _load_json(args.readiness), lifecycle, manifests
    )
    return {
        "lifecycle": lifecycle,
        "readiness": stored,
    }


def _summary(payload: Mapping[str, Any]) -> dict[str, Any]:
    if payload.get("phase") == "J1-R2" and "cohort_roles" in payload:
        lifecycle = payload
        readiness = None
    elif "lifecycle" in payload and "readiness" in payload:
        lifecycle = payload["lifecycle"]
        readiness = payload["readiness"]
    else:
        lifecycle = None
        readiness = payload
    return {
        "cohort_lifecycle_contract_sha256": (
            lifecycle.get("cohort_lifecycle_contract_sha256")
            if lifecycle
            else readiness.get("cohort_lifecycle_contract_sha256")
            if readiness
            else None
        ),
        "evaluation_epoch": lifecycle.get("evaluation_epoch") if lifecycle else None,
        "learning_evaluation_boundary": (
            lifecycle.get("learning_evaluation_boundary") if lifecycle else None
        ),
        "readiness": readiness,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action", choices=("seal-lifecycle", "seal-manifests", "audit-existing")
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--raw-pack", type=Path, default=DEFAULT_RAW_PACK)
    parser.add_argument("--amendment", type=Path, default=DEFAULT_AMENDMENT)
    parser.add_argument("--answers", type=Path, default=DEFAULT_ANSWERS)
    parser.add_argument("--vocabulary", type=Path, default=DEFAULT_VOCABULARY)
    parser.add_argument("--capture", type=Path, default=DEFAULT_CAPTURE)
    parser.add_argument("--labels", type=Path, default=DEFAULT_LABELS)
    parser.add_argument("--r1", type=Path, default=DEFAULT_R1)
    parser.add_argument("--lifecycle", type=Path, default=DEFAULT_LIFECYCLE)
    parser.add_argument("--anchor", type=Path, default=DEFAULT_ANCHOR)
    parser.add_argument("--development", type=Path, default=DEFAULT_DEVELOPMENT)
    parser.add_argument("--lockbox", type=Path, default=DEFAULT_LOCKBOX)
    parser.add_argument("--readiness", type=Path, default=DEFAULT_READINESS)
    return parser.parse_args()


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args()
    if args.action == "seal-lifecycle":
        result = seal_lifecycle(args)
    elif args.action == "seal-manifests":
        result = seal_manifests(args)
    else:
        result = audit_existing(args)
    print(json.dumps(_summary(result), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
