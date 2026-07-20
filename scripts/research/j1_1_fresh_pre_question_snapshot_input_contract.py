"""Create and audit the J1.1B fresh pre-question input contract."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from neural.baby.calibrator_design import (  # noqa: E402
    validate_calibrator_design_audit,
)
from neural.baby.fresh_snapshot_contract import (  # noqa: E402
    build_fresh_pre_question_snapshot_input_contract,
    validate_fresh_pre_question_snapshot_input_contract,
)
from neural.baby.question_selection_contract import (  # noqa: E402
    validate_question_selection_contract,
)


DEFAULT_SELECTION_CONTRACT = (
    PROJECT_ROOT / "scripts" / "research" / "inputs"
    / "j1_1_question_selection_contract_20260718.json"
)
DEFAULT_DESIGN_AUDIT = (
    PROJECT_ROOT / "claudedocs" / "research"
    / "j1_1_candidate_universe_v2_calibrator_design_audit_20260718.json"
)
DEFAULT_CONTRACT = (
    PROJECT_ROOT / "scripts" / "research" / "inputs"
    / "j1_1_fresh_pre_question_snapshot_input_contract_20260718.json"
)
DEFAULT_REPORT = (
    PROJECT_ROOT / "claudedocs" / "research"
    / "j1_1_fresh_pre_question_snapshot_input_contract_20260718.json"
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
    return {
        "phase": contract["phase"],
        "status": contract["status"],
        "fresh_pre_question_snapshot_input_contract_sha256": contract[
            "fresh_pre_question_snapshot_input_contract_sha256"
        ],
        "question_selection_contract_sha256": contract[
            "question_selection_contract_sha256"
        ],
        "calibrator_probability_snapshot_sha256": contract[
            "calibrator_probability_snapshot_sha256"
        ],
        "calibrator_design_audit_sha256": contract[
            "calibrator_design_audit_sha256"
        ],
        "train_only_calibrator_fit_sha256": contract[
            "train_only_calibrator_fit_sha256"
        ],
        "input_contract_scope": contract["input_contract_scope"],
        "input_pack_scope": contract["input_pack_scope"],
        "selection_policy": contract["selection_policy"],
        "feature_schema_sha256": contract["feature_schema_sha256"],
        "feature_names": contract["feature_names"],
        "required_candidate_question_count_min": contract[
            "required_candidate_question_count_min"
        ],
        "required_question_fields": contract["required_question_fields"],
        "required_candidate_row_fields": contract["required_candidate_row_fields"],
        "forbidden_input_fields": contract["forbidden_input_fields"],
        "fresh_pre_question_snapshot_input_contract_gate": contract[
            "fresh_pre_question_snapshot_input_contract_gate"
        ],
        "fresh_snapshot_runtime_gate": contract["fresh_snapshot_runtime_gate"],
        "question_selection_runtime_gate": contract[
            "question_selection_runtime_gate"
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
        raise FileExistsError("refusing to overwrite existing fresh input contract")
    selection = validate_question_selection_contract(_load_json(args.selection))
    design = validate_calibrator_design_audit(_load_json(args.design))
    contract = build_fresh_pre_question_snapshot_input_contract(selection, design)
    _write_json_new(args.contract, contract)
    report = _summary(contract)
    _write_json_new(args.report, report)
    return report


def audit_existing(args: argparse.Namespace) -> dict[str, Any]:
    selection = validate_question_selection_contract(_load_json(args.selection))
    design = validate_calibrator_design_audit(_load_json(args.design))
    contract = validate_fresh_pre_question_snapshot_input_contract(
        _load_json(args.contract),
        selection,
        design,
    )
    return _summary(contract)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("create", "audit-existing"))
    parser.add_argument("--selection", type=Path, default=DEFAULT_SELECTION_CONTRACT)
    parser.add_argument("--design", type=Path, default=DEFAULT_DESIGN_AUDIT)
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
