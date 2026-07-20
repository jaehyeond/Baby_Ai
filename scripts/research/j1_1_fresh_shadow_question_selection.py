"""Create and audit J1.1B fresh shadow question selection."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from neural.baby.fresh_shadow_probability import (  # noqa: E402
    validate_fresh_pre_question_shadow_probability_snapshot,
)
from neural.baby.fresh_shadow_selection import (  # noqa: E402
    build_fresh_shadow_question_selection,
    validate_fresh_shadow_question_selection,
)


DEFAULT_PROBABILITY_SNAPSHOT = (
    PROJECT_ROOT / "scripts" / "research" / "inputs"
    / "j1_1_fresh_pre_question_shadow_probability_snapshot_20260718.json"
)
DEFAULT_SELECTION = (
    PROJECT_ROOT / "scripts" / "research" / "inputs"
    / "j1_1_fresh_shadow_question_selection_20260718.json"
)
DEFAULT_REPORT = (
    PROJECT_ROOT / "claudedocs" / "research"
    / "j1_1_fresh_shadow_question_selection_20260718.json"
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


def _summary(selection: Mapping[str, Any]) -> dict[str, Any]:
    preview = selection["offline_selection_preview"]
    return {
        "phase": selection["phase"],
        "status": selection["status"],
        "fresh_shadow_question_selection_sha256": selection[
            "fresh_shadow_question_selection_sha256"
        ],
        "fresh_pre_question_shadow_probability_snapshot_sha256": selection[
            "fresh_pre_question_shadow_probability_snapshot_sha256"
        ],
        "fresh_pre_question_input_pack_sha256": selection[
            "fresh_pre_question_input_pack_sha256"
        ],
        "fresh_pre_question_snapshot_input_contract_sha256": selection[
            "fresh_pre_question_snapshot_input_contract_sha256"
        ],
        "train_only_calibrator_fit_sha256": selection[
            "train_only_calibrator_fit_sha256"
        ],
        "selection_scope": selection["selection_scope"],
        "selection_policy": selection["selection_policy"],
        "question_count": selection["question_count"],
        "candidate_row_count": selection["candidate_row_count"],
        "probability_count": selection["probability_count"],
        "selected_order": preview["selected_order"],
        "selected_question_id": preview["selected_question_id"],
        "runner_up_order": preview["runner_up_order"],
        "runner_up_question_id": preview["runner_up_question_id"],
        "selected_score": preview["selected_score"],
        "runner_up_score": preview["runner_up_score"],
        "ranked_orders": preview["ranked_orders"],
        "fresh_shadow_question_selection_gate": selection[
            "fresh_shadow_question_selection_gate"
        ],
        "fresh_snapshot_runtime_gate": selection["fresh_snapshot_runtime_gate"],
        "question_selection_runtime_gate": selection[
            "question_selection_runtime_gate"
        ],
        "runtime_probability_snapshot_gate": selection[
            "runtime_probability_snapshot_gate"
        ],
        "database_writes": selection["database_writes"],
        "learning_enabled": selection["learning_enabled"],
        "heldout_gate": selection["heldout_gate"],
        "performance_claim_gate": selection["performance_claim_gate"],
        "production_promotion_gate": selection["production_promotion_gate"],
        "block_reasons": selection["block_reasons"],
        "next_step": selection["next_step"],
    }


def create_selection(args: argparse.Namespace) -> dict[str, Any]:
    if args.selection.exists() or args.report.exists():
        raise FileExistsError("refusing to overwrite existing selection artifact")
    snapshot = validate_fresh_pre_question_shadow_probability_snapshot(
        _load_json(args.probability_snapshot)
    )
    selection = build_fresh_shadow_question_selection(snapshot)
    _write_json_new(args.selection, selection)
    report = _summary(selection)
    _write_json_new(args.report, report)
    return report


def audit_existing(args: argparse.Namespace) -> dict[str, Any]:
    snapshot = validate_fresh_pre_question_shadow_probability_snapshot(
        _load_json(args.probability_snapshot)
    )
    selection = validate_fresh_shadow_question_selection(
        _load_json(args.selection),
        snapshot,
    )
    return _summary(selection)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("create", "audit-existing"))
    parser.add_argument(
        "--probability-snapshot",
        type=Path,
        default=DEFAULT_PROBABILITY_SNAPSHOT,
    )
    parser.add_argument("--selection", type=Path, default=DEFAULT_SELECTION)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    return parser.parse_args()


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args()
    report = create_selection(args) if args.action == "create" else audit_existing(args)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
