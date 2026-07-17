"""Fit and audit the J1.1B train-only probability calibrator offline."""

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
from neural.baby.calibrator_fit import (  # noqa: E402
    fit_train_only_calibrator,
    validate_train_only_calibrator_fit,
)


DEFAULT_DESIGN_AUDIT = (
    PROJECT_ROOT / "claudedocs" / "research"
    / "j1_1_candidate_universe_v2_calibrator_design_audit_20260718.json"
)
DEFAULT_FIT_ARTIFACT = (
    PROJECT_ROOT / "scripts" / "research" / "inputs"
    / "j1_1_candidate_universe_v2_train_only_calibrator_fit_20260718.json"
)
DEFAULT_REPORT = (
    PROJECT_ROOT / "claudedocs" / "research"
    / "j1_1_candidate_universe_v2_train_only_calibrator_fit_20260718.json"
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


def _summary(artifact: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "phase": artifact["phase"],
        "status": artifact["status"],
        "train_only_calibrator_fit_sha256": artifact[
            "train_only_calibrator_fit_sha256"
        ],
        "calibrator_design_audit_sha256": artifact[
            "calibrator_design_audit_sha256"
        ],
        "model_type": artifact["model_type"],
        "training_scope": artifact["training_scope"],
        "evaluation_scope": artifact["evaluation_scope"],
        "fit_row_count": artifact["fit_row_count"],
        "excluded_uncertain_count": artifact["excluded_uncertain_count"],
        "fold_count": artifact["fold_count"],
        "cross_validation_metrics": artifact["cross_validation_metrics"],
        "train_only_fit_execution_gate": artifact[
            "train_only_fit_execution_gate"
        ],
        "offline_probabilities_computed": artifact[
            "offline_probabilities_computed"
        ],
        "runtime_probabilities_computed": artifact[
            "runtime_probabilities_computed"
        ],
        "calibrator_fit_gate": artifact["calibrator_fit_gate"],
        "database_writes": artifact["database_writes"],
        "learning_enabled": artifact["learning_enabled"],
        "heldout_gate": artifact["heldout_gate"],
        "performance_claim_gate": artifact["performance_claim_gate"],
        "production_promotion_gate": artifact["production_promotion_gate"],
        "block_reasons": artifact["block_reasons"],
        "next_step": artifact["next_step"],
    }


def fit(args: argparse.Namespace) -> dict[str, Any]:
    if args.fit_artifact.exists() or args.report.exists():
        raise FileExistsError("refusing to overwrite existing calibrator fit artifacts")
    design = validate_calibrator_design_audit(_load_json(args.design_audit))
    artifact = fit_train_only_calibrator(
        design,
        l2=args.l2,
        learning_rate=args.learning_rate,
        max_iterations=args.max_iterations,
        ece_bins=args.ece_bins,
    )
    _write_json_new(args.fit_artifact, artifact)
    report = _summary(artifact)
    _write_json_new(args.report, report)
    return report


def audit_existing(args: argparse.Namespace) -> dict[str, Any]:
    design = validate_calibrator_design_audit(_load_json(args.design_audit))
    artifact = validate_train_only_calibrator_fit(
        _load_json(args.fit_artifact),
        design,
    )
    return _summary(artifact)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("fit", "audit-existing"))
    parser.add_argument("--design-audit", type=Path, default=DEFAULT_DESIGN_AUDIT)
    parser.add_argument("--fit-artifact", type=Path, default=DEFAULT_FIT_ARTIFACT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--l2", type=float, default=0.1)
    parser.add_argument("--learning-rate", type=float, default=0.1)
    parser.add_argument("--max-iterations", type=int, default=1200)
    parser.add_argument("--ece-bins", type=int, default=5)
    return parser.parse_args()


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args()
    report = fit(args) if args.action == "fit" else audit_existing(args)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
