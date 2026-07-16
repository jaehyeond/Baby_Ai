"""Build the B5.9 offline semantic-label and action-to-answer proposal report."""

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

from neural.baby.pending_question_semantics import (  # noqa: E402
    build_action_answer_relation_proposals,
    canonical_json_sha256,
    validate_semantic_label_pack,
)


DEFAULT_MANIFEST = PROJECT_ROOT / "scripts" / "research" / "manifests" / "b5_7_pending_question_train_a_20260716.json"
DEFAULT_ANSWERS = PROJECT_ROOT / "scripts" / "research" / "inputs" / "b5_7_pending_question_train_a_20260716_answers.json"
DEFAULT_B5_8_ARTIFACT = PROJECT_ROOT / "claudedocs" / "research" / "b5_8_measurement_validity_ranker_20260716.json"
DEFAULT_LABELS = PROJECT_ROOT / "scripts" / "research" / "inputs" / "b5_9_pending_question_train_a_20260716_semantic_labels_reviewed.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "claudedocs" / "research" / "b5_9_semantic_outcome_contract_20260716.json"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def run(args: argparse.Namespace) -> dict[str, Any]:
    manifest = load_json(args.manifest)
    answers = load_json(args.answers)
    b5_8_artifact = load_json(args.b5_8_artifact)
    label_pack = load_json(args.labels)
    validated = validate_semantic_label_pack(
        manifest,
        answers,
        b5_8_artifact,
        label_pack,
    )
    proposals = build_action_answer_relation_proposals(
        manifest,
        answers,
        b5_8_artifact,
        validated,
    )
    label_count = sum(len(entry["labels"]) for entry in validated["entries"])
    return {
        "status": "completed",
        "phase": "B5.9",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "contract_sha256": validated["contract_sha256"],
        "semantic_label_pack_sha256": canonical_json_sha256(validated),
        "review_status": validated["review_status"],
        "question_count": len(validated["entries"]),
        "semantic_label_count": label_count,
        "semantic_target_validity_gate": proposals["semantic_target_validity_gate"],
        "relation_proposal": proposals,
        "database_writes": False,
        "live_predictor_changed": False,
        "conversation_handler_changed": False,
        "heldout_gate": False,
        "production_promotion_gate": False,
        "block_reasons": [
            "semantic_labels_not_user_reviewed",
            "train_only_same_six_questions",
            "relation_schema_not_integrated",
        ] if validated["review_status"] == "draft_unreviewed" else [
            "train_only_same_six_questions",
            "relation_schema_not_integrated",
        ],
        "next_step": (
            "user_review_semantic_labels_before_any_db_write_or_heldout"
            if validated["review_status"] == "draft_unreviewed"
            else "review_relation_schema_and_keep_train_only_until_clean_signal"
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--answers", type=Path, default=DEFAULT_ANSWERS)
    parser.add_argument("--b5-8-artifact", type=Path, default=DEFAULT_B5_8_ARTIFACT)
    parser.add_argument("--labels", type=Path, default=DEFAULT_LABELS)
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
            "review_status": report["review_status"],
            "question_count": report["question_count"],
            "semantic_label_count": report["semantic_label_count"],
            "semantic_target_validity_gate": report["semantic_target_validity_gate"],
            "relation_proposal_count": report["relation_proposal"]["relation_proposal_count"],
            "database_writes": report["database_writes"],
            "heldout_gate": report["heldout_gate"],
            "production_promotion_gate": report["production_promotion_gate"],
            "block_reasons": report["block_reasons"],
            "next_step": report["next_step"],
            "output": str(args.output.resolve()),
        }
    print(json.dumps(rendered, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
