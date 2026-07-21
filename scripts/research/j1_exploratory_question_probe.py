"""Run or audit the read-only J1 exploratory pre-answer question probe."""

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

from neural.baby.candidate_universe import (  # noqa: E402
    classify_candidate_vocabulary,
    exclude_question_cue_surfaces,
)
from neural.baby.exploratory_question_probe import (  # noqa: E402
    build_exploratory_pre_answer_capture,
    validate_exploratory_pre_answer_capture,
    validate_exploratory_question_manifest,
)
from scripts.research.j1_1_candidate_universe_v2 import (  # noqa: E402
    _read_all_concepts,
)
from scripts.research.j1_1_candidate_universe_v2_capture import (  # noqa: E402
    _capture_graph_scores,
    _capture_local_scores,
    _sha256_file,
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


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json_new(path: Path, payload: dict[str, Any]) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite exploratory capture: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _scoring_vocabulary(
    manifest: dict[str, Any],
    source_concepts: list[dict[str, Any]],
) -> dict[str, Any]:
    eligible, _ = classify_candidate_vocabulary(source_concepts)
    scopes = []
    for question in manifest["questions"]:
        scoped, cue_exclusions = exclude_question_cue_surfaces(
            eligible, question["cue_terms"]
        )
        scopes.append({
            "order": question["order"],
            "question_id": question["question_id"],
            "question_sha256": question["question_sha256"],
            "cue_terms": question["cue_terms"],
            "cue_exclusions": cue_exclusions,
            "eligible_concept_count": len(scoped),
        })
    return {
        "eligible_concepts": eligible,
        "question_scopes": scopes,
    }


def _summary(capture: dict[str, Any]) -> dict[str, Any]:
    return {
        "phase": capture["phase"],
        "status": capture["status"],
        "captured_at": capture["captured_at"],
        "exploratory_pre_answer_capture_sha256": capture[
            "exploratory_pre_answer_capture_sha256"
        ],
        "question_count": capture["question_count"],
        "source_concept_count": capture["source_concept_count"],
        "eligible_concept_count": capture["eligible_concept_count"],
        "minimum_question_eligible_count": min(
            item["eligible_concept_count"] for item in capture["questions"]
        ),
        "maximum_question_eligible_count": max(
            item["eligible_concept_count"] for item in capture["questions"]
        ),
        "local_core_adapter_sha256": capture["local_core_predictor"][
            "adapter_sha256"
        ],
        "local_core_trainable_parameter_count": capture["local_core_predictor"][
            "trainable_parameter_count"
        ],
        "questions_public_before_raw_capture": True,
        "captured_before_answers": True,
        "exploratory_not_for_claim": True,
        "confirmatory_reuse_allowed": False,
        "database_writes": False,
        "learning_enabled": False,
        "performance_claim_gate": False,
        "next_step": capture["next_step"],
    }


def capture(args: argparse.Namespace) -> dict[str, Any]:
    if args.capture.exists():
        raise FileExistsError("refusing to overwrite exploratory pre-answer capture")
    if not 1 <= args.batch_size <= 64:
        raise ValueError("batch-size must be between 1 and 64")

    manifest = validate_exploratory_question_manifest(_load_json(args.manifest))
    source_concepts = sorted(
        asyncio.run(_read_all_concepts()),
        key=lambda item: (item["id"], item["name"]),
    )
    vocabulary = _scoring_vocabulary(manifest, source_concepts)
    graph_scores = asyncio.run(_capture_graph_scores(manifest, vocabulary))
    local_scores, local_metadata = _capture_local_scores(
        manifest,
        vocabulary,
        batch_size=args.batch_size,
    )
    result = build_exploratory_pre_answer_capture(
        manifest,
        source_concepts,
        graph_scores,
        local_scores,
        graph_predictor={
            "implementation_sha256": _sha256_file(
                PROJECT_ROOT / "neural" / "baby" / "neo4j_db.py"
            ),
            "scoring_contract": "max_cue_edge_strength_full_vocabulary_v1",
            "unconnected_candidate_score": 0.0,
        },
        local_core_predictor=local_metadata,
        captured_at=_now_iso(),
    )
    _write_json_new(args.capture, result)
    return _summary(result)


def audit_existing(args: argparse.Namespace) -> dict[str, Any]:
    manifest = validate_exploratory_question_manifest(_load_json(args.manifest))
    capture_payload = validate_exploratory_pre_answer_capture(
        _load_json(args.capture),
        manifest,
    )
    return _summary(capture_payload)


def show_questions(args: argparse.Namespace) -> dict[str, Any]:
    manifest = validate_exploratory_question_manifest(_load_json(args.manifest))
    return {
        "manifest_id": manifest["manifest_id"],
        "evidence_scope": manifest["evidence_scope"],
        "questions": [
            {
                "order": item["order"],
                "question_id": item["question_id"],
                "question": item["question"],
            }
            for item in manifest["questions"]
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=("capture", "audit-existing", "show-questions"),
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--capture", type=Path, default=DEFAULT_CAPTURE)
    parser.add_argument("--batch-size", type=int, default=16)
    return parser.parse_args()


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args()
    if args.action == "capture":
        result = capture(args)
    elif args.action == "audit-existing":
        result = audit_existing(args)
    else:
        result = show_questions(args)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

