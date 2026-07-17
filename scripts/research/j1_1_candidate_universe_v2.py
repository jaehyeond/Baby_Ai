"""Build or audit the read-only J1.1B candidate-vocabulary preflight.

This step snapshots all Neo4j concepts, applies predictor-neutral validity
rules, and preregisters independent full-vocabulary Graph/Local-Core scoring.
It does not run the GPU, compute probabilities, fit a calibrator, or write DB.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from neural.baby.answer_source import (  # noqa: E402
    validate_answer_source_amendment,
    validate_candidate_label_pack,
    validate_reference_answer_pack,
)
from neural.baby.candidate_universe import (  # noqa: E402
    CANDIDATE_VOCABULARY_VERSION,
    DEFAULT_TOP_K,
    classify_candidate_vocabulary,
    exclude_question_cue_surfaces,
    seal_candidate_vocabulary,
    validate_candidate_vocabulary,
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
DEFAULT_REVIEWED_ANSWERS = (
    PROJECT_ROOT / "scripts" / "research" / "inputs"
    / "j1_1_teacher_answers_reviewed_20260716.json"
)
DEFAULT_REVIEWED_LABELS = (
    PROJECT_ROOT / "scripts" / "research" / "inputs"
    / "j1_1_candidate_labels_reviewed_20260716.json"
)
DEFAULT_VOCABULARY = (
    PROJECT_ROOT / "scripts" / "research" / "inputs"
    / "j1_1_candidate_vocabulary_v2_20260716.json"
)
DEFAULT_REPORT = (
    PROJECT_ROOT / "claudedocs" / "research"
    / "j1_1_candidate_universe_v2_preflight_20260716.json"
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json_new(path: Path, payload: dict[str, Any]) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite J1.1B artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


async def _read_all_concepts() -> list[dict[str, Any]]:
    """Read concept identity fields through the existing read-only DB method."""

    load_dotenv(PROJECT_ROOT / ".env", override=False)
    from neural.baby.neo4j_db import (  # imported only after .env is loaded
        BrainDatabase,
        close_driver,
        init_driver,
    )

    await init_driver()
    try:
        concepts = await BrainDatabase().get_all_concepts()
    finally:
        await close_driver()
    return [{
        "id": str(item.get("id") or ""),
        "name": str(item.get("name") or ""),
    } for item in concepts]


def _validated_inputs(args: argparse.Namespace) -> tuple[dict[str, Any], ...]:
    manifest = validate_preregistered_manifest(_load_json(args.manifest))
    raw_pack = _load_json(args.raw_pack)
    amendment = validate_answer_source_amendment(
        manifest, raw_pack, _load_json(args.amendment)
    )
    answers = validate_reference_answer_pack(
        manifest, raw_pack, amendment, _load_json(args.reviewed_answers)
    )
    labels = validate_candidate_label_pack(
        manifest,
        raw_pack,
        answers,
        _load_json(args.reviewed_labels),
        require_user_review=True,
    )
    return manifest, raw_pack, amendment, answers, labels


def _report(vocabulary: dict[str, Any]) -> dict[str, Any]:
    return {
        "phase": "J1.1B",
        "status": "ready_for_read_only_independent_raw_score_capture",
        "created_at": vocabulary["created_at"],
        "candidate_vocabulary_sha256": vocabulary["candidate_vocabulary_sha256"],
        "source_concept_count": vocabulary["source_concept_count"],
        "eligible_concept_count": vocabulary["eligible_concept_count"],
        "rejected_concept_count": vocabulary["rejected_concept_count"],
        "rejection_counts": vocabulary["rejection_counts"],
        "question_scope_count": len(vocabulary["question_scopes"]),
        "minimum_question_eligible_count": min(
            item["eligible_concept_count"] for item in vocabulary["question_scopes"]
        ),
        "vocabulary_contract_gate": True,
        "independent_full_vocabulary_raw_score_gate": False,
        "fair_candidate_universe_gate": False,
        "calibrator_fit_gate": False,
        "database_writes": False,
        "learning_enabled": False,
        "gpu_inference_executed": False,
        "probabilities_computed": False,
        "heldout_gate": False,
        "performance_claim_gate": False,
        "production_promotion_gate": False,
        "block_reasons": [
            "graph_and_local_core_full_vocabulary_raw_scores_not_captured"
        ],
        "next_step": (
            "capture_graph_and_local_core_full_vocabulary_raw_scores_read_only_"
            "then_build_independent_top_k_union"
        ),
    }


def preflight(args: argparse.Namespace) -> dict[str, Any]:
    if args.vocabulary.exists() or args.report.exists():
        raise FileExistsError("refusing to overwrite existing J1.1B preflight artifacts")
    manifest, raw_pack, amendment, answers, labels = _validated_inputs(args)
    source_concepts = sorted(
        asyncio.run(_read_all_concepts()),
        key=lambda item: (item["id"], item["name"]),
    )
    eligible, rejected = classify_candidate_vocabulary(source_concepts)
    question_scopes: list[dict[str, Any]] = []
    for question in manifest["questions"]:
        scoped, cue_exclusions = exclude_question_cue_surfaces(
            eligible, question["cue_terms"]
        )
        question_scopes.append({
            "order": question["order"],
            "question_id": question["question_id"],
            "question_sha256": question["question_sha256"],
            "cue_terms": question["cue_terms"],
            "cue_exclusions": cue_exclusions,
            "eligible_concept_count": len(scoped),
        })

    created_at = _now_iso()
    vocabulary = seal_candidate_vocabulary({
        "candidate_vocabulary_version": CANDIDATE_VOCABULARY_VERSION,
        "phase": "J1.1B",
        "status": "preflight_only",
        "created_at": created_at,
        "manifest_id": manifest["manifest_id"],
        "manifest_contract_sha256": manifest["contract_sha256"],
        "raw_score_pack_sha256": raw_pack["raw_score_pack_sha256"],
        "answer_source_amendment_sha256": amendment["amendment_sha256"],
        "reviewed_reference_answer_pack_sha256": answers[
            "reference_answer_pack_sha256"
        ],
        "reviewed_candidate_label_pack_sha256": labels[
            "candidate_label_pack_sha256"
        ],
        "graph_snapshot_sha256": canonical_json_sha256({
            "concepts": source_concepts
        }),
        "selection_contract": {
            "source_vocabulary": "neo4j_full_concept_snapshot",
            "validity_filter_precedes_predictor_scoring": True,
            "semantic_labels_used_for_filtering": False,
            "graph_scores_required_for_full_question_vocabulary": True,
            "local_core_scores_required_for_full_question_vocabulary": True,
            "top_k": DEFAULT_TOP_K,
            "union_rule": "graph_top_k_union_local_core_top_k",
            "both_predictors_rescore_union": True,
        },
        "source_concept_count": len(source_concepts),
        "eligible_concept_count": len(eligible),
        "rejected_concept_count": len(rejected),
        "rejection_counts": dict(Counter(item["reason"] for item in rejected)),
        "eligible_concepts": eligible,
        "rejected_concepts": rejected,
        "question_scopes": question_scopes,
        "database_writes": False,
        "learning_enabled": False,
        "gpu_inference_executed": False,
        "probabilities_computed": False,
        "calibrator_fit_allowed": False,
        "heldout_gate": False,
        "performance_claim_gate": False,
        "production_promotion_gate": False,
    })
    vocabulary = validate_candidate_vocabulary(vocabulary)
    report = _report(vocabulary)
    _write_json_new(args.vocabulary, vocabulary)
    _write_json_new(args.report, report)
    return report


def audit(args: argparse.Namespace) -> dict[str, Any]:
    _validated_inputs(args)
    return _report(validate_candidate_vocabulary(_load_json(args.vocabulary)))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("preflight", "audit"))
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--raw-pack", type=Path, default=DEFAULT_RAW_PACK)
    parser.add_argument("--amendment", type=Path, default=DEFAULT_AMENDMENT)
    parser.add_argument(
        "--reviewed-answers", type=Path, default=DEFAULT_REVIEWED_ANSWERS
    )
    parser.add_argument(
        "--reviewed-labels", type=Path, default=DEFAULT_REVIEWED_LABELS
    )
    parser.add_argument("--vocabulary", type=Path, default=DEFAULT_VOCABULARY)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    return parser.parse_args()


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args()
    report = preflight(args) if args.action == "preflight" else audit(args)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
