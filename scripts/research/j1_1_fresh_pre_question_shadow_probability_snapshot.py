"""Create and audit J1.1B fresh pre-question shadow probabilities."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from neural.baby.calibrator_fit import (  # noqa: E402
    validate_train_only_calibrator_fit,
)
from neural.baby.fresh_shadow_probability import (  # noqa: E402
    build_fresh_pre_question_shadow_probability_snapshot,
    validate_fresh_pre_question_shadow_probability_snapshot,
)
from neural.baby.fresh_snapshot_contract import (  # noqa: E402
    validate_fresh_pre_question_snapshot_input_contract,
    validate_fresh_pre_question_snapshot_input_pack,
)


DEFAULT_CONTRACT = (
    PROJECT_ROOT / "scripts" / "research" / "inputs"
    / "j1_1_fresh_pre_question_snapshot_input_contract_20260718.json"
)
DEFAULT_INPUT_PACK = (
    PROJECT_ROOT / "scripts" / "research" / "inputs"
    / "j1_1_fresh_pre_question_shadow_input_pack_20260718.json"
)
DEFAULT_FIT = (
    PROJECT_ROOT / "scripts" / "research" / "inputs"
    / "j1_1_candidate_universe_v2_train_only_calibrator_fit_20260718.json"
)
DEFAULT_SNAPSHOT = (
    PROJECT_ROOT / "scripts" / "research" / "inputs"
    / "j1_1_fresh_pre_question_shadow_probability_snapshot_20260718.json"
)
DEFAULT_REPORT = (
    PROJECT_ROOT / "claudedocs" / "research"
    / "j1_1_fresh_pre_question_shadow_probability_snapshot_20260718.json"
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
    ranked_preview = sorted(
        snapshot["question_probability_snapshots"],
        key=lambda item: (
            -float(item["mean_binary_entropy"]),
            -int(item["uncertainty_band_count_0_4_to_0_6"]),
            int(item["order"]),
        ),
    )
    return {
        "phase": snapshot["phase"],
        "status": snapshot["status"],
        "fresh_pre_question_shadow_probability_snapshot_sha256": snapshot[
            "fresh_pre_question_shadow_probability_snapshot_sha256"
        ],
        "fresh_pre_question_input_pack_sha256": snapshot[
            "fresh_pre_question_input_pack_sha256"
        ],
        "fresh_pre_question_snapshot_input_contract_sha256": snapshot[
            "fresh_pre_question_snapshot_input_contract_sha256"
        ],
        "train_only_calibrator_fit_sha256": snapshot[
            "train_only_calibrator_fit_sha256"
        ],
        "probability_scope": snapshot["probability_scope"],
        "probability_policy": snapshot["probability_policy"],
        "selection_policy": snapshot["selection_policy"],
        "question_count": snapshot["question_count"],
        "candidate_row_count": snapshot["candidate_row_count"],
        "probability_count": snapshot["probability_count"],
        "ranked_question_preview": [
            {
                "rank": index + 1,
                "order": item["order"],
                "question_id": item["question_id"],
                "mean_binary_entropy": item["mean_binary_entropy"],
                "uncertainty_band_count_0_4_to_0_6": item[
                    "uncertainty_band_count_0_4_to_0_6"
                ],
                "top_concept_id": item["top_concept_id"],
                "top_probability": item["top_probability"],
            }
            for index, item in enumerate(ranked_preview)
        ],
        "fresh_shadow_probability_snapshot_gate": snapshot[
            "fresh_shadow_probability_snapshot_gate"
        ],
        "fresh_snapshot_runtime_gate": snapshot["fresh_snapshot_runtime_gate"],
        "question_selection_runtime_gate": snapshot[
            "question_selection_runtime_gate"
        ],
        "runtime_probability_snapshot_gate": snapshot[
            "runtime_probability_snapshot_gate"
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
    contract = validate_fresh_pre_question_snapshot_input_contract(
        _load_json(args.contract)
    )
    pack = validate_fresh_pre_question_snapshot_input_pack(
        _load_json(args.input_pack),
        contract,
    )
    fit = validate_train_only_calibrator_fit(_load_json(args.fit))
    snapshot = build_fresh_pre_question_shadow_probability_snapshot(
        contract,
        pack,
        fit,
    )
    _write_json_new(args.snapshot, snapshot)
    report = _summary(snapshot)
    _write_json_new(args.report, report)
    return report


def audit_existing(args: argparse.Namespace) -> dict[str, Any]:
    contract = validate_fresh_pre_question_snapshot_input_contract(
        _load_json(args.contract)
    )
    pack = validate_fresh_pre_question_snapshot_input_pack(
        _load_json(args.input_pack),
        contract,
    )
    fit = validate_train_only_calibrator_fit(_load_json(args.fit))
    snapshot = validate_fresh_pre_question_shadow_probability_snapshot(
        _load_json(args.snapshot),
        contract,
        pack,
        fit,
    )
    return _summary(snapshot)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("create", "audit-existing"))
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--input-pack", type=Path, default=DEFAULT_INPUT_PACK)
    parser.add_argument("--fit", type=Path, default=DEFAULT_FIT)
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
