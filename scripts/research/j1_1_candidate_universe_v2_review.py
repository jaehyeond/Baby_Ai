"""Export and seal J1.1B independent-union user review artifacts.

This script keeps the assistant draft, the user review decisions, and the
reviewed successor label pack as separate immutable artifacts.  It does not
write Neo4j, run learning, fit a calibrator, or promote production behavior.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from neural.baby.answer_source import (  # noqa: E402
    validate_answer_source_amendment,
    validate_reference_answer_pack,
)
from neural.baby.candidate_universe import (  # noqa: E402
    UNION_REVIEW_DECISION_PACK_VERSION,
    build_union_label_readiness_report,
    build_user_reviewed_union_label_pack,
    validate_candidate_vocabulary,
    validate_independent_score_capture,
    validate_union_label_pack,
)
from neural.baby.pending_question_semantics import canonical_json_sha256  # noqa: E402
from neural.baby.question_calibration import validate_preregistered_manifest  # noqa: E402


DEFAULT_MANIFEST = (
    PROJECT_ROOT / "scripts" / "research" / "manifests"
    / "j1_1_train_calibration_a_20260716.json"
)
DEFAULT_RAW_PACK = (
    PROJECT_ROOT / "scripts" / "research" / "inputs"
    / "j1_1_train_calibration_a_20260716_raw_scores_sealed.json"
)
DEFAULT_AMENDMENT = (
    PROJECT_ROOT / "scripts" / "research" / "inputs"
    / "j1_1_answer_source_amendment_20260716.json"
)
DEFAULT_ANSWERS = (
    PROJECT_ROOT / "scripts" / "research" / "inputs"
    / "j1_1_teacher_answers_reviewed_20260716.json"
)
DEFAULT_VOCABULARY = (
    PROJECT_ROOT / "scripts" / "research" / "inputs"
    / "j1_1_candidate_vocabulary_v2_20260716.json"
)
DEFAULT_CAPTURE = (
    PROJECT_ROOT / "scripts" / "research" / "inputs"
    / "j1_1_candidate_universe_v2_raw_scores_20260716.json"
)
DEFAULT_DRAFT_LABELS = (
    PROJECT_ROOT / "scripts" / "research" / "inputs"
    / "j1_1_candidate_universe_v2_labels_draft_20260716.json"
)
DEFAULT_REVIEW_DECISIONS = (
    PROJECT_ROOT / "scripts" / "research" / "inputs"
    / "j1_1_candidate_universe_v2_review_decisions_20260718.json"
)
DEFAULT_ACCEPTED_DECISIONS = (
    PROJECT_ROOT / "scripts" / "research" / "inputs"
    / "j1_1_candidate_universe_v2_review_decisions_accepted_20260718.json"
)
DEFAULT_REVIEWED_LABELS = (
    PROJECT_ROOT / "scripts" / "research" / "inputs"
    / "j1_1_candidate_universe_v2_labels_reviewed_20260718.json"
)
DEFAULT_REVIEWED_REPORT = (
    PROJECT_ROOT / "claudedocs" / "research"
    / "j1_1_candidate_universe_v2_labels_reviewed_20260718.json"
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def _validated_context(
    args: argparse.Namespace,
    labels_path: Path,
    *,
    require_user_review: bool = False,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    manifest = validate_preregistered_manifest(_load_json(args.manifest))
    raw_pack = _load_json(args.raw_pack)
    amendment = validate_answer_source_amendment(
        manifest, raw_pack, _load_json(args.amendment)
    )
    answers = validate_reference_answer_pack(
        manifest, raw_pack, amendment, _load_json(args.answers)
    )
    vocabulary = validate_candidate_vocabulary(_load_json(args.vocabulary))
    capture = validate_independent_score_capture(
        vocabulary, _load_json(args.capture)
    )
    labels = validate_union_label_pack(
        capture,
        answers,
        _load_json(labels_path),
        require_user_review=require_user_review,
    )
    return answers, vocabulary, capture, labels


def _review_decision_from_draft(decision: str) -> str:
    if not decision.startswith("proposed_"):
        raise ValueError("draft union label decision must be proposed_*")
    return decision.removeprefix("proposed_")


def export_template(args: argparse.Namespace) -> dict[str, Any]:
    answers, _, capture, draft = _validated_context(args, args.draft_labels)
    entries = []
    label_count = 0
    for entry in draft["entries"]:
        labels = []
        for label in entry["labels"]:
            label_count += 1
            labels.append({
                "concept_id": label["concept_id"],
                "concept_name": label["concept_name"],
                "draft_decision": label["decision"],
                "suggested_decision": _review_decision_from_draft(
                    str(label["decision"])
                ),
                "decision": None,
                "rationale": label["rationale"],
            })
        entries.append({
            "order": entry["order"],
            "question_id": entry["question_id"],
            "question_sha256": entry["question_sha256"],
            "answer_sha256": entry["answer_sha256"],
            "labels": labels,
        })

    template = {
        "review_decision_pack_version": UNION_REVIEW_DECISION_PACK_VERSION,
        "phase": "J1.1B",
        "status": "awaiting_user_batch_review",
        "decision_source": "user_batch_review",
        "source_union_label_pack_sha256": draft["union_label_pack_sha256"],
        "independent_score_capture_sha256": capture[
            "independent_score_capture_sha256"
        ],
        "reviewed_reference_answer_pack_sha256": answers[
            "reference_answer_pack_sha256"
        ],
        "reviewer_role": "user",
        "reviewed_at": None,
        "instructions": [
            "Fill reviewed_at with a timezone-aware ISO timestamp.",
            "Set every labels[].decision to approved, rejected, or uncertain.",
            "Keep rationale or replace it when changing a suggested decision.",
        ],
        "label_count": label_count,
        "entries": entries,
        "database_writes": False,
        "learning_enabled": False,
        "calibrator_fit_allowed": False,
        "heldout_gate": False,
        "performance_claim_gate": False,
        "production_promotion_gate": False,
    }
    _write_json_new(args.decisions, template)
    return {
        "phase": "J1.1B",
        "status": "review_template_exported",
        "created_at": _now_iso(),
        "review_decision_path": str(args.decisions),
        "source_union_label_pack_sha256": draft["union_label_pack_sha256"],
        "independent_score_capture_sha256": capture[
            "independent_score_capture_sha256"
        ],
        "label_count": label_count,
        "reviewed_label_pack_created": False,
        "next_step": "user_batch_review_fill_decisions_then_run_seal_reviewed",
    }


def accept_suggested(args: argparse.Namespace) -> dict[str, Any]:
    if args.accepted_decisions.exists():
        raise FileExistsError(
            f"refusing to overwrite existing artifact: {args.accepted_decisions}"
        )
    template = _load_json(args.decisions)
    if template.get("status") != "awaiting_user_batch_review":
        raise ValueError("review decision template is not awaiting user review")
    reviewed_at = args.reviewed_at or _now_iso()
    accepted = json.loads(json.dumps(template, ensure_ascii=False))
    accepted["status"] = "user_reviewed_bulk_accept_suggested_decisions"
    accepted["reviewed_at"] = reviewed_at
    accepted["review_mode"] = (
        "bulk_accept_suggested_decisions_from_current_user_instruction"
    )
    accepted["source_review_template_sha256"] = canonical_json_sha256(template)
    label_count = 0
    for entry in accepted.get("entries") or []:
        for label in entry.get("labels") or []:
            if label.get("decision") is not None:
                raise ValueError("bulk accept requires an unfilled decision template")
            suggested = str(label.get("suggested_decision") or "")
            if suggested not in {"approved", "rejected", "uncertain"}:
                raise ValueError("invalid suggested decision")
            label["decision"] = suggested
            label_count += 1
    if accepted.get("label_count") != label_count:
        raise ValueError("review decision label_count mismatch")
    _write_json_new(args.accepted_decisions, accepted)
    return {
        "phase": "J1.1B",
        "status": "suggested_decisions_bulk_accepted",
        "reviewed_at": reviewed_at,
        "source_review_template_sha256": accepted[
            "source_review_template_sha256"
        ],
        "review_decision_path": str(args.accepted_decisions),
        "label_count": label_count,
        "reviewed_label_pack_created": False,
        "next_step": "run_seal_reviewed_with_the_accepted_decision_artifact",
    }


def seal_reviewed(args: argparse.Namespace) -> dict[str, Any]:
    if args.reviewed_labels.exists() or args.reviewed_report.exists():
        raise FileExistsError("refusing to overwrite existing reviewed artifacts")
    answers, _, capture, draft = _validated_context(args, args.draft_labels)
    decisions = _load_json(args.decisions)
    reviewed = build_user_reviewed_union_label_pack(
        capture,
        answers,
        draft,
        decisions,
        reviewed_at=args.reviewed_at,
    )
    report = build_union_label_readiness_report(capture, answers, reviewed)
    report.update({
        "created_at": reviewed["reviewed_at"],
        "reviewed_at": reviewed["reviewed_at"],
        "reviewer_role": "user",
        "source_union_label_pack_sha256": draft["union_label_pack_sha256"],
        "review_decision_pack_sha256": canonical_json_sha256(decisions),
        "union_label_pack_sha256": reviewed["union_label_pack_sha256"],
        "conversation_handler_changed": False,
        "live_predictor_changed": False,
    })
    _write_json_new(args.reviewed_labels, reviewed)
    _write_json_new(args.reviewed_report, report)
    return report


def audit_reviewed(args: argparse.Namespace) -> dict[str, Any]:
    answers, _, capture, labels = _validated_context(
        args, args.reviewed_labels, require_user_review=True
    )
    return build_union_label_readiness_report(capture, answers, labels)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=(
            "export-template",
            "accept-suggested",
            "seal-reviewed",
            "audit-reviewed",
        ),
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--raw-pack", type=Path, default=DEFAULT_RAW_PACK)
    parser.add_argument("--amendment", type=Path, default=DEFAULT_AMENDMENT)
    parser.add_argument("--answers", type=Path, default=DEFAULT_ANSWERS)
    parser.add_argument("--vocabulary", type=Path, default=DEFAULT_VOCABULARY)
    parser.add_argument("--capture", type=Path, default=DEFAULT_CAPTURE)
    parser.add_argument("--draft-labels", type=Path, default=DEFAULT_DRAFT_LABELS)
    parser.add_argument("--decisions", type=Path, default=DEFAULT_REVIEW_DECISIONS)
    parser.add_argument(
        "--accepted-decisions", type=Path, default=DEFAULT_ACCEPTED_DECISIONS
    )
    parser.add_argument(
        "--reviewed-labels", type=Path, default=DEFAULT_REVIEWED_LABELS
    )
    parser.add_argument(
        "--reviewed-report", type=Path, default=DEFAULT_REVIEWED_REPORT
    )
    parser.add_argument("--reviewed-at")
    return parser.parse_args()


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args()
    if args.action == "export-template":
        report = export_template(args)
    elif args.action == "accept-suggested":
        report = accept_suggested(args)
    elif args.action == "seal-reviewed":
        report = seal_reviewed(args)
    else:
        report = audit_reviewed(args)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
