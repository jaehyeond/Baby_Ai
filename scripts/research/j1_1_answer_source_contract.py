"""Prepare or audit J1.1A answer-source, reference-answer, and label drafts."""

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

from neural.baby.answer_source import (  # noqa: E402
    build_user_reviewed_packs,
    build_answer_source_readiness_report,
    seal_answer_source_amendment,
    seal_candidate_label_pack,
    seal_reference_answer_pack,
    validate_answer_source_amendment,
    validate_candidate_label_pack,
    validate_reference_answer_pack,
)


DEFAULT_MANIFEST = (
    PROJECT_ROOT / "scripts" / "research" / "manifests"
    / "j1_1_train_calibration_a_20260716.json"
)
DEFAULT_RAW_PACK = (
    PROJECT_ROOT / "scripts" / "research" / "inputs"
    / "j1_1_train_calibration_a_20260716_raw_scores_sealed.json"
)
DEFAULT_DRAFT = (
    PROJECT_ROOT / "scripts" / "research" / "inputs"
    / "j1_1_answer_source_draft_20260716.json"
)
DEFAULT_AMENDMENT = (
    PROJECT_ROOT / "scripts" / "research" / "inputs"
    / "j1_1_answer_source_amendment_20260716.json"
)
DEFAULT_ANSWERS = (
    PROJECT_ROOT / "scripts" / "research" / "inputs"
    / "j1_1_teacher_answers_20260716.json"
)
DEFAULT_LABELS = (
    PROJECT_ROOT / "scripts" / "research" / "inputs"
    / "j1_1_candidate_labels_draft_20260716.json"
)
DEFAULT_REPORT = (
    PROJECT_ROOT / "claudedocs" / "research"
    / "j1_1_answer_source_contract_20260716.json"
)
DEFAULT_REVIEWED_ANSWERS = (
    PROJECT_ROOT / "scripts" / "research" / "inputs"
    / "j1_1_teacher_answers_reviewed_20260716.json"
)
DEFAULT_REVIEWED_LABELS = (
    PROJECT_ROOT / "scripts" / "research" / "inputs"
    / "j1_1_candidate_labels_reviewed_20260716.json"
)
DEFAULT_REVIEWED_REPORT = (
    PROJECT_ROOT / "claudedocs" / "research"
    / "j1_1_answer_source_contract_reviewed_20260716.json"
)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json_new(path: Path, payload: MappingLike) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite J1.1A artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _require_new_paths(*paths: Path) -> None:
    existing = [str(path) for path in paths if path.exists()]
    if existing:
        raise FileExistsError(
            "refusing to overwrite J1.1A artifact(s): " + ", ".join(existing)
        )


MappingLike = dict[str, Any]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _materialize_outputs(
    manifest: dict[str, Any],
    raw_pack: dict[str, Any],
    draft: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    created_at = _now_iso()
    amendment_payload = dict(draft["amendment"])
    amendment_payload.update({
        "created_at": created_at,
        "manifest_id": manifest["manifest_id"],
        "contract_sha256": manifest["contract_sha256"],
        "raw_score_pack_sha256": raw_pack["raw_score_pack_sha256"],
    })
    amendment = seal_answer_source_amendment(amendment_payload)
    validate_answer_source_amendment(manifest, raw_pack, amendment)

    manifest_by_order = {
        int(item["order"]): dict(item)
        for item in manifest["questions"]
    }
    answer_payload = dict(draft["reference_answer_pack"])
    answers: list[dict[str, Any]] = []
    for raw_answer in answer_payload.pop("answers"):
        order = int(raw_answer["order"])
        question = manifest_by_order[order]
        answers.append({
            **raw_answer,
            "question_id": question["question_id"],
            "question": question["question"],
            "question_sha256": question["question_sha256"],
        })
    answer_payload.update({
        "created_at": created_at,
        "manifest_id": manifest["manifest_id"],
        "contract_sha256": manifest["contract_sha256"],
        "raw_score_pack_sha256": raw_pack["raw_score_pack_sha256"],
        "answer_source_amendment_sha256": amendment["amendment_sha256"],
        "answer_count": len(answers),
        "answers": answers,
    })
    answer_pack = seal_reference_answer_pack(answer_payload)
    validate_reference_answer_pack(manifest, raw_pack, amendment, answer_pack)

    answer_by_order = {int(item["order"]): item for item in answer_pack["answers"]}
    label_payload = dict(draft["candidate_label_pack"])
    entries: list[dict[str, Any]] = []
    for raw_entry in label_payload.pop("entries"):
        order = int(raw_entry["order"])
        question = manifest_by_order[order]
        entries.append({
            **raw_entry,
            "question_id": question["question_id"],
            "question_sha256": question["question_sha256"],
            "answer_sha256": answer_by_order[order]["answer_sha256"],
        })
    label_payload.update({
        "created_at": created_at,
        "manifest_id": manifest["manifest_id"],
        "contract_sha256": manifest["contract_sha256"],
        "raw_score_pack_sha256": raw_pack["raw_score_pack_sha256"],
        "reference_answer_pack_sha256": answer_pack["reference_answer_pack_sha256"],
        "entries": entries,
    })
    label_pack = seal_candidate_label_pack(label_payload)
    validate_candidate_label_pack(manifest, raw_pack, answer_pack, label_pack)

    report = build_answer_source_readiness_report(
        manifest,
        raw_pack,
        amendment,
        answer_pack,
        label_pack,
    )
    report.update({
        "created_at": created_at,
        "answer_source_amendment_sha256": amendment["amendment_sha256"],
        "reference_answer_pack_sha256": answer_pack["reference_answer_pack_sha256"],
        "candidate_label_pack_sha256": label_pack["candidate_label_pack_sha256"],
        "conversation_handler_changed": False,
        "live_predictor_changed": False,
    })
    return amendment, answer_pack, label_pack, report


def prepare(args: argparse.Namespace) -> dict[str, Any]:
    manifest = _load_json(args.manifest)
    raw_pack = _load_json(args.raw_pack)
    amendment, answers, labels, report = _materialize_outputs(
        manifest,
        raw_pack,
        _load_json(args.draft),
    )
    _write_json_new(args.amendment, amendment)
    _write_json_new(args.answers, answers)
    _write_json_new(args.labels, labels)
    _write_json_new(args.report, report)
    return report


def approve(args: argparse.Namespace) -> dict[str, Any]:
    """Record the explicit batch approval in new, hash-bound artifacts."""

    _require_new_paths(
        args.reviewed_answers,
        args.reviewed_labels,
        args.reviewed_report,
    )
    manifest = _load_json(args.manifest)
    raw_pack = _load_json(args.raw_pack)
    amendment = validate_answer_source_amendment(
        manifest,
        raw_pack,
        _load_json(args.amendment),
    )
    draft_answers = validate_reference_answer_pack(
        manifest,
        raw_pack,
        amendment,
        _load_json(args.answers),
    )
    draft_labels = validate_candidate_label_pack(
        manifest,
        raw_pack,
        draft_answers,
        _load_json(args.labels),
    )
    reviewed_at = _now_iso()
    reviewed_answers, reviewed_labels = build_user_reviewed_packs(
        draft_answers,
        draft_labels,
        reviewed_at=reviewed_at,
    )
    reviewed_answers = validate_reference_answer_pack(
        manifest,
        raw_pack,
        amendment,
        reviewed_answers,
    )
    reviewed_labels = validate_candidate_label_pack(
        manifest,
        raw_pack,
        reviewed_answers,
        reviewed_labels,
        require_user_review=True,
    )
    report = build_answer_source_readiness_report(
        manifest,
        raw_pack,
        amendment,
        reviewed_answers,
        reviewed_labels,
    )
    report.update({
        "created_at": reviewed_at,
        "reviewed_at": reviewed_at,
        "reviewer_role": "user",
        "answer_source_amendment_sha256": amendment["amendment_sha256"],
        "draft_reference_answer_pack_sha256": draft_answers[
            "reference_answer_pack_sha256"
        ],
        "draft_candidate_label_pack_sha256": draft_labels[
            "candidate_label_pack_sha256"
        ],
        "reference_answer_pack_sha256": reviewed_answers[
            "reference_answer_pack_sha256"
        ],
        "candidate_label_pack_sha256": reviewed_labels[
            "candidate_label_pack_sha256"
        ],
        "conversation_handler_changed": False,
        "live_predictor_changed": False,
    })
    _write_json_new(args.reviewed_answers, reviewed_answers)
    _write_json_new(args.reviewed_labels, reviewed_labels)
    _write_json_new(args.reviewed_report, report)
    return report


def audit(args: argparse.Namespace) -> dict[str, Any]:
    manifest = _load_json(args.manifest)
    raw_pack = _load_json(args.raw_pack)
    amendment = _load_json(args.amendment)
    answers = _load_json(args.answers)
    labels = _load_json(args.labels)
    report = build_answer_source_readiness_report(
        manifest,
        raw_pack,
        amendment,
        answers,
        labels,
    )
    return {
        **report,
        "answer_source_amendment_sha256": amendment["amendment_sha256"],
        "reference_answer_pack_sha256": answers["reference_answer_pack_sha256"],
        "candidate_label_pack_sha256": labels["candidate_label_pack_sha256"],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "approve", "audit"))
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--raw-pack", type=Path, default=DEFAULT_RAW_PACK)
    parser.add_argument("--draft", type=Path, default=DEFAULT_DRAFT)
    parser.add_argument("--amendment", type=Path, default=DEFAULT_AMENDMENT)
    parser.add_argument("--answers", type=Path, default=DEFAULT_ANSWERS)
    parser.add_argument("--labels", type=Path, default=DEFAULT_LABELS)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument(
        "--reviewed-answers", type=Path, default=DEFAULT_REVIEWED_ANSWERS
    )
    parser.add_argument(
        "--reviewed-labels", type=Path, default=DEFAULT_REVIEWED_LABELS
    )
    parser.add_argument(
        "--reviewed-report", type=Path, default=DEFAULT_REVIEWED_REPORT
    )
    return parser.parse_args()


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args()
    if args.action == "prepare":
        report = prepare(args)
    elif args.action == "approve":
        report = approve(args)
    else:
        report = audit(args)
    rendered = {
        "status": report["status"],
        "question_count": report["question_count"],
        "candidate_label_count": report["candidate_label_count"],
        "proposed_decision_counts": report["proposed_decision_counts"],
        "candidate_positive_coverage_count": report["candidate_positive_coverage_count"],
        "candidate_positive_coverage_gate": report["candidate_positive_coverage_gate"],
        "provisional_calibrator_fit_gate": report["provisional_calibrator_fit_gate"],
        "question_selection_calibrator_gate": report["question_selection_calibrator_gate"],
        "database_writes": report["database_writes"],
        "learning_enabled": report["learning_enabled"],
        "block_reasons": report["block_reasons"],
        "next_step": report["next_step"],
    }
    print(json.dumps(rendered, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
