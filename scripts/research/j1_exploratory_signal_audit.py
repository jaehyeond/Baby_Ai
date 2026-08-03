"""Seal external-teacher answers, then audit the J1 exploratory capture."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from neural.baby.exploratory_signal_audit import (  # noqa: E402
    build_exploratory_signal_audit,
    seal_exploratory_answer_pack,
    validate_exploratory_answer_pack,
    validate_exploratory_signal_audit,
)
from neural.baby.exploratory_question_probe import (  # noqa: E402
    validate_exploratory_pre_answer_capture,
    validate_exploratory_question_manifest,
)
from scripts.research.j1_1_candidate_universe_v2 import (  # noqa: E402
    _read_all_concepts,
)


DEFAULT_MANIFEST = (
    PROJECT_ROOT
    / "scripts"
    / "research"
    / "manifests"
    / "j1_1_fresh_selection_b_20260720_draft.json"
)
DEFAULT_CAPTURE = (
    PROJECT_ROOT
    / "scripts"
    / "research"
    / "inputs"
    / "j1_exploratory_pre_answer_probe_b_20260721.json"
)
DEFAULT_ANSWER_SPEC = (
    PROJECT_ROOT
    / "scripts"
    / "research"
    / "manifests"
    / "j1_exploratory_external_teacher_answers_b_20260721.json"
)
DEFAULT_ANSWER_PACK = (
    PROJECT_ROOT
    / "scripts"
    / "research"
    / "inputs"
    / "j1_exploratory_external_teacher_answers_b_20260721.json"
)
DEFAULT_AUDIT = (
    PROJECT_ROOT
    / "claudedocs"
    / "research"
    / "j1_exploratory_signal_audit_b_20260721.json"
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json_new(path: Path, payload: dict[str, Any]) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite sealed exploratory artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _load_context(args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, Any]]:
    manifest = validate_exploratory_question_manifest(_load_json(args.manifest))
    capture = validate_exploratory_pre_answer_capture(
        _load_json(args.capture), manifest
    )
    return manifest, capture


def _answer_summary(answer_pack: dict[str, Any]) -> dict[str, Any]:
    return {
        "phase": answer_pack["phase"],
        "status": answer_pack["status"],
        "answer_source": answer_pack["answer_source"],
        "question_count": answer_pack["question_count"],
        "generated_before_prediction_reveal": answer_pack[
            "generated_before_prediction_reveal"
        ],
        "prediction_fields_consumed_for_answer_generation": answer_pack[
            "prediction_fields_consumed_for_answer_generation"
        ],
        "exploratory_answer_pack_sha256": answer_pack[
            "exploratory_answer_pack_sha256"
        ],
        "next_step": answer_pack["next_step"],
    }


def _audit_summary(audit: dict[str, Any]) -> dict[str, Any]:
    question_hits = []
    for question in audit["questions"]:
        question_hits.append({
            "question_id": question["question_id"],
            "available_targets": [
                item["target_concept"]
                for item in question["target_availability"]
                if item["available_in_captured_vocabulary"]
            ],
            "missing_targets": [
                item["target_concept"]
                for item in question["target_availability"]
                if not item["available_in_captured_vocabulary"]
            ],
            "graph_exact_target_hits": [
                item["target_concept"]
                for item in question["graph"]["exact_target_hits"]
            ],
            "local_core_exact_target_hits": [
                item["target_concept"]
                for item in question["local_core"]["exact_target_hits"]
            ],
        })
    return {
        "phase": audit["phase"],
        "status": audit["status"],
        "signal_status": audit["signal_status"],
        "question_count": audit["question_count"],
        "declared_target_count": audit["declared_target_count"],
        "available_target_count": audit["available_target_count"],
        "missing_target_count": audit["missing_target_count"],
        "graph_summary": audit["graph_summary"],
        "local_core_summary": audit["local_core_summary"],
        "question_hits": question_hits,
        "exploratory_signal_audit_sha256": audit[
            "exploratory_signal_audit_sha256"
        ],
        "performance_claim_gate": audit["performance_claim_gate"],
        "production_promotion_gate": audit["production_promotion_gate"],
        "next_step": audit["next_step"],
    }


def seal_answers(args: argparse.Namespace) -> dict[str, Any]:
    manifest, capture = _load_context(args)
    answer_pack = seal_exploratory_answer_pack(
        _load_json(args.answer_spec),
        manifest,
        capture,
        sealed_at=_now_iso(),
    )
    _write_json_new(args.answer_pack, answer_pack)
    return _answer_summary(answer_pack)


def run_audit(args: argparse.Namespace) -> dict[str, Any]:
    manifest, capture = _load_context(args)
    answer_pack = validate_exploratory_answer_pack(
        _load_json(args.answer_pack), manifest, capture
    )
    source_concepts = asyncio.run(_read_all_concepts())
    audit = build_exploratory_signal_audit(
        answer_pack,
        manifest,
        capture,
        source_concepts,
        audited_at=_now_iso(),
    )
    _write_json_new(args.audit, audit)
    return _audit_summary(audit)


def audit_existing(args: argparse.Namespace) -> dict[str, Any]:
    manifest, capture = _load_context(args)
    answer_pack = validate_exploratory_answer_pack(
        _load_json(args.answer_pack), manifest, capture
    )
    audit = validate_exploratory_signal_audit(
        _load_json(args.audit), answer_pack, manifest, capture
    )
    return _audit_summary(audit)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=("seal-answers", "audit", "audit-existing"),
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--capture", type=Path, default=DEFAULT_CAPTURE)
    parser.add_argument("--answer-spec", type=Path, default=DEFAULT_ANSWER_SPEC)
    parser.add_argument("--answer-pack", type=Path, default=DEFAULT_ANSWER_PACK)
    parser.add_argument("--audit", type=Path, default=DEFAULT_AUDIT)
    return parser.parse_args()


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args()
    if args.action == "seal-answers":
        result = seal_answers(args)
    elif args.action == "audit":
        result = run_audit(args)
    else:
        result = audit_existing(args)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
