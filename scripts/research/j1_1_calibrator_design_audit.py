"""Audit the J1.1B train-only calibrator design before any fit step."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from neural.baby.answer_source import (  # noqa: E402
    validate_answer_source_amendment,
    validate_reference_answer_pack,
)
from neural.baby.calibrator_design import (  # noqa: E402
    build_calibrator_design_audit,
    validate_calibrator_design_audit,
)
from neural.baby.candidate_universe import (  # noqa: E402
    validate_candidate_vocabulary,
    validate_independent_score_capture,
)
from neural.baby.question_calibration import validate_preregistered_manifest  # noqa: E402


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
DEFAULT_REVIEWED_LABELS = (
    PROJECT_ROOT / "scripts" / "research" / "inputs"
    / "j1_1_candidate_universe_v2_labels_reviewed_20260718.json"
)
DEFAULT_REPORT = (
    PROJECT_ROOT / "claudedocs" / "research"
    / "j1_1_candidate_universe_v2_calibrator_design_audit_20260718.json"
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


def _validated_inputs(args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    manifest = validate_preregistered_manifest(_load_json(args.manifest))
    raw_pack = _load_json(args.raw_pack)
    amendment = validate_answer_source_amendment(
        manifest, raw_pack, _load_json(args.amendment)
    )
    answers = validate_reference_answer_pack(
        manifest, raw_pack, amendment, _load_json(args.answers)
    )
    vocabulary = validate_candidate_vocabulary(_load_json(args.vocabulary))
    if vocabulary["manifest_contract_sha256"] != manifest["contract_sha256"]:
        raise ValueError("vocabulary and manifest are not bound")
    capture = validate_independent_score_capture(
        vocabulary, _load_json(args.capture)
    )
    labels = _load_json(args.reviewed_labels)
    return answers, capture, labels


def audit_design(args: argparse.Namespace) -> dict[str, Any]:
    if args.report.exists():
        raise FileExistsError("refusing to overwrite existing calibrator audit")
    answers, capture, labels = _validated_inputs(args)
    report = build_calibrator_design_audit(capture, answers, labels)
    _write_json_new(args.report, report)
    return report


def audit_existing(args: argparse.Namespace) -> dict[str, Any]:
    return validate_calibrator_design_audit(_load_json(args.report))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("audit-design", "audit-existing"))
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--raw-pack", type=Path, default=DEFAULT_RAW_PACK)
    parser.add_argument("--amendment", type=Path, default=DEFAULT_AMENDMENT)
    parser.add_argument("--answers", type=Path, default=DEFAULT_ANSWERS)
    parser.add_argument("--vocabulary", type=Path, default=DEFAULT_VOCABULARY)
    parser.add_argument("--capture", type=Path, default=DEFAULT_CAPTURE)
    parser.add_argument(
        "--reviewed-labels", type=Path, default=DEFAULT_REVIEWED_LABELS
    )
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    return parser.parse_args()


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args()
    report = audit_design(args) if args.action == "audit-design" else audit_existing(args)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
