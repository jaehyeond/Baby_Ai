"""Create and audit J1.1B offline calibrator probability snapshots."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from neural.baby.calibrator_design import validate_calibrator_design_audit  # noqa: E402
from neural.baby.calibrator_fit import validate_train_only_calibrator_fit  # noqa: E402
from neural.baby.calibrator_snapshot import (  # noqa: E402
    build_calibrator_probability_snapshot,
    validate_calibrator_probability_snapshot,
)


DEFAULT_DESIGN_AUDIT = (
    PROJECT_ROOT / "claudedocs" / "research"
    / "j1_1_candidate_universe_v2_calibrator_design_audit_20260718.json"
)
DEFAULT_FIT_ARTIFACT = (
    PROJECT_ROOT / "scripts" / "research" / "inputs"
    / "j1_1_candidate_universe_v2_train_only_calibrator_fit_20260718.json"
)
DEFAULT_SNAPSHOT = (
    PROJECT_ROOT / "scripts" / "research" / "inputs"
    / "j1_1_candidate_universe_v2_probability_snapshot_20260718.json"
)
DEFAULT_REPORT = (
    PROJECT_ROOT / "claudedocs" / "research"
    / "j1_1_candidate_universe_v2_probability_snapshot_20260718.json"
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


def _summary(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    question_summary = []
    for question in snapshot["question_snapshots"]:
        question_summary.append({
            "order": question["order"],
            "candidate_count": question["candidate_count"],
            "top_concept_id": question["top_concept_id"],
            "top_probability": question["top_probability"],
            "mean_probability": question["mean_probability"],
            "mean_binary_entropy": question["mean_binary_entropy"],
            "uncertainty_band_count_0_4_to_0_6": question[
                "uncertainty_band_count_0_4_to_0_6"
            ],
        })
    return {
        "phase": snapshot["phase"],
        "status": snapshot["status"],
        "calibrator_probability_snapshot_sha256": snapshot[
            "calibrator_probability_snapshot_sha256"
        ],
        "calibrator_design_audit_sha256": snapshot[
            "calibrator_design_audit_sha256"
        ],
        "train_only_calibrator_fit_sha256": snapshot[
            "train_only_calibrator_fit_sha256"
        ],
        "snapshot_scope": snapshot["snapshot_scope"],
        "snapshot_policy": snapshot["snapshot_policy"],
        "question_selection_policy_preview": snapshot[
            "question_selection_policy_preview"
        ],
        "question_count": snapshot["question_count"],
        "candidate_label_count": snapshot["candidate_label_count"],
        "probability_count": snapshot["probability_count"],
        "selected_order_preview": snapshot["selected_order_preview"],
        "selected_order_preview_reason": snapshot[
            "selected_order_preview_reason"
        ],
        "question_summary": question_summary,
        "offline_probability_snapshot_gate": snapshot[
            "offline_probability_snapshot_gate"
        ],
        "runtime_probability_snapshot_gate": snapshot[
            "runtime_probability_snapshot_gate"
        ],
        "question_selection_runtime_gate": snapshot[
            "question_selection_runtime_gate"
        ],
        "database_writes": snapshot["database_writes"],
        "learning_enabled": snapshot["learning_enabled"],
        "heldout_gate": snapshot["heldout_gate"],
        "performance_claim_gate": snapshot["performance_claim_gate"],
        "production_promotion_gate": snapshot["production_promotion_gate"],
        "block_reasons": snapshot["block_reasons"],
        "next_step": snapshot["next_step"],
    }


def create_snapshot(args: argparse.Namespace) -> dict[str, Any]:
    if args.snapshot.exists() or args.report.exists():
        raise FileExistsError("refusing to overwrite existing probability snapshot")
    design = validate_calibrator_design_audit(_load_json(args.design_audit))
    fit = validate_train_only_calibrator_fit(_load_json(args.fit_artifact), design)
    snapshot = build_calibrator_probability_snapshot(design, fit)
    _write_json_new(args.snapshot, snapshot)
    report = _summary(snapshot)
    _write_json_new(args.report, report)
    return report


def audit_existing(args: argparse.Namespace) -> dict[str, Any]:
    design = validate_calibrator_design_audit(_load_json(args.design_audit))
    fit = validate_train_only_calibrator_fit(_load_json(args.fit_artifact), design)
    snapshot = validate_calibrator_probability_snapshot(
        _load_json(args.snapshot),
        design,
        fit,
    )
    return _summary(snapshot)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("create", "audit-existing"))
    parser.add_argument("--design-audit", type=Path, default=DEFAULT_DESIGN_AUDIT)
    parser.add_argument("--fit-artifact", type=Path, default=DEFAULT_FIT_ARTIFACT)
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    return parser.parse_args()


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args()
    report = create_snapshot(args) if args.action == "create" else audit_existing(args)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
