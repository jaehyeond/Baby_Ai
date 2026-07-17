"""Create and audit the J1.1B offline question-selection contract."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from neural.baby.calibrator_snapshot import (  # noqa: E402
    validate_calibrator_probability_snapshot,
)
from neural.baby.question_selection_contract import (  # noqa: E402
    build_question_selection_contract,
    validate_question_selection_contract,
)


DEFAULT_SNAPSHOT = (
    PROJECT_ROOT / "scripts" / "research" / "inputs"
    / "j1_1_candidate_universe_v2_probability_snapshot_20260718.json"
)
DEFAULT_CONTRACT = (
    PROJECT_ROOT / "scripts" / "research" / "inputs"
    / "j1_1_question_selection_contract_20260718.json"
)
DEFAULT_REPORT = (
    PROJECT_ROOT / "claudedocs" / "research"
    / "j1_1_question_selection_contract_20260718.json"
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


def _summary(contract: Mapping[str, Any]) -> dict[str, Any]:
    preview = contract["offline_selection_preview"]
    return {
        "phase": contract["phase"],
        "status": contract["status"],
        "question_selection_contract_sha256": contract[
            "question_selection_contract_sha256"
        ],
        "calibrator_probability_snapshot_sha256": contract[
            "calibrator_probability_snapshot_sha256"
        ],
        "selection_scope": contract["selection_scope"],
        "selection_policy": contract["selection_policy"],
        "question_count": contract["question_count"],
        "candidate_label_count": contract["candidate_label_count"],
        "probability_count": contract["probability_count"],
        "selected_order": preview["selected_order"],
        "runner_up_order": preview["runner_up_order"],
        "selected_score": preview["selected_score"],
        "runner_up_score": preview["runner_up_score"],
        "ranked_orders": preview["ranked_orders"],
        "offline_question_selection_contract_gate": contract[
            "offline_question_selection_contract_gate"
        ],
        "runtime_question_selection_gate": contract[
            "runtime_question_selection_gate"
        ],
        "runtime_probability_snapshot_gate": contract[
            "runtime_probability_snapshot_gate"
        ],
        "database_writes": contract["database_writes"],
        "learning_enabled": contract["learning_enabled"],
        "heldout_gate": contract["heldout_gate"],
        "performance_claim_gate": contract["performance_claim_gate"],
        "production_promotion_gate": contract["production_promotion_gate"],
        "block_reasons": contract["block_reasons"],
        "next_step": contract["next_step"],
    }


def create_contract(args: argparse.Namespace) -> dict[str, Any]:
    if args.contract.exists() or args.report.exists():
        raise FileExistsError("refusing to overwrite existing selection contract")
    snapshot = validate_calibrator_probability_snapshot(_load_json(args.snapshot))
    contract = build_question_selection_contract(snapshot)
    _write_json_new(args.contract, contract)
    report = _summary(contract)
    _write_json_new(args.report, report)
    return report


def audit_existing(args: argparse.Namespace) -> dict[str, Any]:
    snapshot = validate_calibrator_probability_snapshot(_load_json(args.snapshot))
    contract = validate_question_selection_contract(
        _load_json(args.contract),
        snapshot,
    )
    return _summary(contract)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("create", "audit-existing"))
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    return parser.parse_args()


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args()
    report = create_contract(args) if args.action == "create" else audit_existing(args)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
