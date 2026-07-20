"""Create and audit a J1.1B fresh pre-question shadow input pack."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from neural.baby.candidate_universe import (  # noqa: E402
    validate_candidate_vocabulary,
    validate_independent_score_capture,
)
from neural.baby.fresh_snapshot_contract import (  # noqa: E402
    build_shadow_fresh_pre_question_snapshot_input_pack,
    validate_fresh_pre_question_snapshot_input_contract,
    validate_fresh_pre_question_snapshot_input_pack,
)


DEFAULT_CONTRACT = (
    PROJECT_ROOT / "scripts" / "research" / "inputs"
    / "j1_1_fresh_pre_question_snapshot_input_contract_20260718.json"
)
DEFAULT_VOCABULARY = (
    PROJECT_ROOT / "scripts" / "research" / "inputs"
    / "j1_1_candidate_vocabulary_v2_20260716.json"
)
DEFAULT_CAPTURE = (
    PROJECT_ROOT / "scripts" / "research" / "inputs"
    / "j1_1_candidate_universe_v2_raw_scores_20260716.json"
)
DEFAULT_PACK = (
    PROJECT_ROOT / "scripts" / "research" / "inputs"
    / "j1_1_fresh_pre_question_shadow_input_pack_20260718.json"
)
DEFAULT_REPORT = (
    PROJECT_ROOT / "claudedocs" / "research"
    / "j1_1_fresh_pre_question_shadow_input_pack_20260718.json"
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


def _summary(pack: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "phase": pack["phase"],
        "status": pack["status"],
        "fresh_pre_question_input_pack_sha256": pack[
            "fresh_pre_question_input_pack_sha256"
        ],
        "fresh_pre_question_snapshot_input_contract_sha256": pack[
            "fresh_pre_question_snapshot_input_contract_sha256"
        ],
        "source_independent_score_capture_sha256": pack[
            "source_independent_score_capture_sha256"
        ],
        "source_scope": pack["source_scope"],
        "input_pack_scope": pack["input_pack_scope"],
        "selection_policy": pack["selection_policy"],
        "feature_schema_sha256": pack["feature_schema_sha256"],
        "pre_question_captured_at": pack["pre_question_captured_at"],
        "question_count": pack["question_count"],
        "candidate_row_count": pack["candidate_row_count"],
        "fresh_pre_question_input_pack_gate": pack[
            "fresh_pre_question_input_pack_gate"
        ],
        "fresh_snapshot_runtime_gate": pack["fresh_snapshot_runtime_gate"],
        "question_selection_runtime_gate": pack[
            "question_selection_runtime_gate"
        ],
        "runtime_probability_snapshot_gate": pack[
            "runtime_probability_snapshot_gate"
        ],
        "database_writes": pack["database_writes"],
        "learning_enabled": pack["learning_enabled"],
        "heldout_gate": pack["heldout_gate"],
        "performance_claim_gate": pack["performance_claim_gate"],
        "production_promotion_gate": pack["production_promotion_gate"],
        "block_reasons": pack["block_reasons"],
        "next_step": pack["next_step"],
    }


def create_shadow(args: argparse.Namespace) -> dict[str, Any]:
    if args.pack.exists() or args.report.exists():
        raise FileExistsError("refusing to overwrite existing fresh shadow pack")
    contract = validate_fresh_pre_question_snapshot_input_contract(
        _load_json(args.contract)
    )
    vocabulary = validate_candidate_vocabulary(_load_json(args.vocabulary))
    capture = validate_independent_score_capture(
        vocabulary,
        _load_json(args.capture),
    )
    pack = build_shadow_fresh_pre_question_snapshot_input_pack(contract, capture)
    _write_json_new(args.pack, pack)
    report = _summary(pack)
    _write_json_new(args.report, report)
    return report


def audit_existing(args: argparse.Namespace) -> dict[str, Any]:
    contract = validate_fresh_pre_question_snapshot_input_contract(
        _load_json(args.contract)
    )
    pack = validate_fresh_pre_question_snapshot_input_pack(
        _load_json(args.pack),
        contract,
    )
    return _summary(pack)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("create-shadow", "audit-existing"))
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--vocabulary", type=Path, default=DEFAULT_VOCABULARY)
    parser.add_argument("--capture", type=Path, default=DEFAULT_CAPTURE)
    parser.add_argument("--pack", type=Path, default=DEFAULT_PACK)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    return parser.parse_args()


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args()
    report = create_shadow(args) if args.action == "create-shadow" else audit_existing(args)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
