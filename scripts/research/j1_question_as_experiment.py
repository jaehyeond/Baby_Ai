"""Run the J1 Question-as-Experiment readiness audit or sealed-pack evaluator."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from neural.baby.question_experiment import (  # noqa: E402
    audit_legacy_j1_readiness,
    evaluate_question_experiment_pack,
)


DEFAULT_MANIFEST = (
    PROJECT_ROOT / "scripts" / "research" / "manifests"
    / "b5_7_pending_question_train_a_20260716.json"
)
DEFAULT_B5_7_ARTIFACT = (
    PROJECT_ROOT / "claudedocs" / "research"
    / "b5_7_pending_question_train_a_20260716.json"
)
DEFAULT_B5_8_ARTIFACT = (
    PROJECT_ROOT / "claudedocs" / "research"
    / "b5_8_measurement_validity_ranker_20260716.json"
)
DEFAULT_LABELS = (
    PROJECT_ROOT / "scripts" / "research" / "inputs"
    / "b5_9_pending_question_train_a_20260716_semantic_labels_reviewed.json"
)
DEFAULT_OUTPUT = (
    PROJECT_ROOT / "claudedocs" / "research"
    / "j1_question_as_experiment_readiness_20260716.json"
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def run(args: argparse.Namespace) -> dict[str, Any]:
    manifest = load_json(args.manifest)
    labels = load_json(args.labels)
    if args.experiment_pack is None:
        report = audit_legacy_j1_readiness(
            manifest,
            load_json(args.b5_7_artifact),
            load_json(args.b5_8_artifact),
            labels,
        )
    else:
        report = evaluate_question_experiment_pack(
            manifest,
            labels,
            load_json(args.experiment_pack),
        )
        report["phase"] = "J1.0"
        report["experiment_pack"] = str(args.experiment_pack.resolve())
    return {
        **report,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "conversation_handler_changed": False,
        "live_predictor_changed": False,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--b5-7-artifact", type=Path, default=DEFAULT_B5_7_ARTIFACT)
    parser.add_argument("--b5-8-artifact", type=Path, default=DEFAULT_B5_8_ARTIFACT)
    parser.add_argument("--labels", type=Path, default=DEFAULT_LABELS)
    parser.add_argument("--experiment-pack", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--compact", action="store_true")
    return parser.parse_args()


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args()
    report = run(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    rendered = report
    if args.compact:
        rendered = {
            "status": report["status"],
            "phase": report["phase"],
            "mode": report["mode"],
            "contract_gate": report["contract_gate"],
            "database_writes": report["database_writes"],
            "learning_enabled": report["learning_enabled"],
            "heldout_gate": report["heldout_gate"],
            "production_promotion_gate": report["production_promotion_gate"],
            "block_reasons": report["block_reasons"],
            "next_step": report.get("next_step"),
            "output": str(args.output.resolve()),
        }
    print(json.dumps(rendered, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
