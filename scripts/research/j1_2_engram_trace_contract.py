"""Create and audit the J1.2 engram trace contract (definition only).

This script reads sealed J1 artifacts, recomputes their hashes, re-runs their
validators, and seals a definition-only taxonomy.  It performs no engram
measurement, opens no database, loads no model, and writes nothing outside the
two new artifact paths.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Mapping


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from neural.baby.engram_trace_contract import (  # noqa: E402
    ALL_REQUIRED_FALSE_GATES,
    ENGRAM_OWN_GATE,
    REQUIRED_UPSTREAM_KEYS,
    UPSTREAM_HASH_SPEC,
    build_engram_trace_contract,
    validate_engram_trace_contract,
)


INPUTS = PROJECT_ROOT / "scripts" / "research" / "inputs"
DOCS = PROJECT_ROOT / "claudedocs" / "research"

DEFAULT_UPSTREAM_PATHS: dict[str, Path] = {
    "fresh_shadow_question_selection": (
        INPUTS / "j1_1_fresh_shadow_question_selection_20260718.json"
    ),
    "fresh_pre_question_shadow_probability_snapshot": (
        INPUTS / "j1_1_fresh_pre_question_shadow_probability_snapshot_20260718.json"
    ),
    "fresh_pre_question_input_pack": (
        INPUTS / "j1_1_fresh_pre_question_shadow_input_pack_20260718.json"
    ),
    "fresh_pre_question_snapshot_input_contract": (
        INPUTS / "j1_1_fresh_pre_question_snapshot_input_contract_20260718.json"
    ),
    "train_only_calibrator_fit": (
        INPUTS / "j1_1_candidate_universe_v2_train_only_calibrator_fit_20260718.json"
    ),
    "calibrator_design_audit": (
        DOCS / "j1_1_candidate_universe_v2_calibrator_design_audit_20260718.json"
    ),
    "calibrator_probability_snapshot": (
        INPUTS / "j1_1_candidate_universe_v2_probability_snapshot_20260718.json"
    ),
    "question_selection_contract": (
        INPUTS / "j1_1_question_selection_contract_20260718.json"
    ),
    "independent_score_capture": (
        INPUTS / "j1_1_candidate_universe_v2_raw_scores_20260716.json"
    ),
    "candidate_vocabulary": (
        INPUTS / "j1_1_candidate_vocabulary_v2_20260716.json"
    ),
    "union_label_pack": (
        INPUTS / "j1_1_candidate_universe_v2_labels_reviewed_20260718.json"
    ),
    "answer_source_amendment": (
        INPUTS / "j1_1_answer_source_amendment_20260716.json"
    ),
}

DEFAULT_CONTRACT = INPUTS / "j1_2_engram_trace_contract_20260719.json"
DEFAULT_REPORT = DOCS / "j1_2_engram_trace_contract_20260719.json"

LOCAL_CORE_ADAPTER_DIR = PROJECT_ROOT / "models" / "local_core_adapter"


def sha256_directory(path: Path) -> str:
    """Reproduce j1_1_capture_raw_scores._sha256_directory exactly.

    Read-only: the directory is opened for reading and nothing is written.  The
    sealed adapter hash is a digest over the whole directory, never over a single
    file, so a single-file hash must never be compared against it.
    """

    if not path.is_dir():
        raise FileNotFoundError(f"local-core adapter directory not found: {path}")
    digest = hashlib.sha256()
    files = sorted(item for item in path.rglob("*") if item.is_file())
    if not files:
        raise ValueError("local-core adapter directory is empty")
    for item in files:
        relative = item.relative_to(path).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(item.stat().st_size.to_bytes(8, "big"))
        with item.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
    return digest.hexdigest()


def adapter_digest_recheck(sealed_digest: str) -> dict[str, Any]:
    """Advisory observation only: never asserted by the contract validator.

    A later distill run may legitimately change the adapter, which would make
    this observation false without invalidating the sealed historical record.
    """

    result: dict[str, Any] = {
        "checked_path": "models/local_core_adapter",
        "digest_scope": "directory_digest_not_single_file_hash",
        "sealed_digest": sealed_digest,
        "is_advisory_not_validator_assertion": True,
    }
    try:
        recomputed = sha256_directory(LOCAL_CORE_ADAPTER_DIR)
    except (FileNotFoundError, ValueError, OSError) as error:
        result["recomputed_digest"] = None
        result["matches_sealed"] = None
        result["recheck_error"] = f"{type(error).__name__}: {error}"
        return result
    result["recomputed_digest"] = recomputed
    result["matches_sealed"] = recomputed == sealed_digest
    return result


def report_statements(recheck: Mapping[str, Any]) -> list[str]:
    """Plain-language statements so the gates are not the only place facts appear."""

    matches = recheck.get("matches_sealed")
    if matches is True:
        adapter_sentence = (
            "the sealed local-core adapter digest is a DIRECTORY digest over "
            "models/local_core_adapter/ and was recomputed during this run and "
            "matches; it is not a single-file hash and must never be compared "
            "against one."
        )
    elif matches is False:
        adapter_sentence = (
            "the sealed local-core adapter digest is a DIRECTORY digest over "
            "models/local_core_adapter/ and DID NOT match when recomputed during "
            "this run, so the sealed capture is no longer reproducible on disk; "
            "it is still not comparable to any single-file hash."
        )
    else:
        adapter_sentence = (
            "the sealed local-core adapter digest is a DIRECTORY digest over "
            "models/local_core_adapter/ and could NOT be recomputed during this "
            "run; treat its on-disk reproducibility as unknown, and never compare "
            "it against a single-file hash."
        )
    return [
        "engram measurement was not executed.",
        "graph / probability / provenance layers are not the paper's weight-space "
        "engrams.",
        adapter_sentence,
    ]


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


def load_upstream(paths: Mapping[str, Path]) -> dict[str, dict[str, Any]]:
    """Step 0 integrity gate: load and self-verify every upstream artifact."""

    upstream: dict[str, dict[str, Any]] = {}
    for key in REQUIRED_UPSTREAM_KEYS:
        path = paths[key]
        if not path.exists():
            raise FileNotFoundError(f"missing upstream artifact for {key}: {path}")
        upstream[key] = _load_json(path)
    return upstream


def _summary(contract: Mapping[str, Any]) -> dict[str, Any]:
    gates = {gate: contract[gate] for gate in ALL_REQUIRED_FALSE_GATES}
    gates[ENGRAM_OWN_GATE] = contract[ENGRAM_OWN_GATE]
    mapping_kinds: dict[str, int] = {}
    for cell in contract["criteria_mappings"]:
        kind = str(cell["mapping_kind"])
        mapping_kinds[kind] = mapping_kinds.get(kind, 0) + 1
    recheck = adapter_digest_recheck(contract["local_core_identity"]["adapter_sha256"])
    return {
        "local_core_adapter_digest_recheck": recheck,
        "phase": contract["phase"],
        "status": contract["status"],
        "engram_trace_contract_sha256": contract["engram_trace_contract_sha256"],
        "engram_trace_contract_scope": contract["engram_trace_contract_scope"],
        "engram_criteria_policy": contract["engram_criteria_policy"],
        "own_gate_semantics": contract["own_gate_semantics"],
        "plain_language_statements": report_statements(recheck),
        "engram_object_locus": contract["engram_object_locus"],
        "estimator_verification_status": contract["estimator_verification_status"],
        "engram_criteria_attribution": contract["engram_criteria_attribution"],
        "engram_source_reference": contract["engram_source_reference"],
        "local_core_identity": contract["local_core_identity"],
        "sample_scale": contract["sample_scale"],
        "selected_question_id_at_chain_tip": contract[
            "selected_question_id_at_chain_tip"
        ],
        "selected_order_at_chain_tip": contract["selected_order_at_chain_tip"],
        "criteria_mapping_count": len(contract["criteria_mappings"]),
        "criteria_mapping_kind_counts": mapping_kinds,
        "executed_measurement_count": 0,
        "hash_binding_count": len(contract["hash_bindings"]),
        "hash_bindings": contract["hash_bindings"],
        "revalidated_upstream_artifacts": contract["revalidated_upstream_artifacts"],
        "forbidden_operations": contract["forbidden_operations"],
        "discipline": contract["discipline"],
        "gates": gates,
        "block_reasons": contract["block_reasons"],
        "block_reason_count": len(contract["block_reasons"]),
        "next_step": contract["next_step"],
        "engram_track_next_step": contract["engram_track_next_step"],
    }


def create_contract(args: argparse.Namespace) -> dict[str, Any]:
    if args.contract.exists() or args.report.exists():
        raise FileExistsError("refusing to overwrite existing engram contract artifact")
    upstream = load_upstream(DEFAULT_UPSTREAM_PATHS)
    contract = build_engram_trace_contract(upstream)
    _write_json_new(args.contract, contract)
    report = _summary(contract)
    _write_json_new(args.report, report)
    return report


def audit_existing(args: argparse.Namespace) -> dict[str, Any]:
    upstream = load_upstream(DEFAULT_UPSTREAM_PATHS)
    contract = validate_engram_trace_contract(_load_json(args.contract), upstream)
    return _summary(contract)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("create", "audit-existing"))
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    return parser.parse_args()


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args()
    report = create_contract(args) if args.action == "create" else audit_existing(args)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    print(f"upstream_hash_spec_count={len(UPSTREAM_HASH_SPEC)}")


if __name__ == "__main__":
    main()
