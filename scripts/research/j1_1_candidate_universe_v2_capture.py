"""Capture J1.1B Graph/Local-Core raw scores on one sealed vocabulary.

The action is read-only: Neo4j relationships are queried, the local core is
frozen under inference mode, and only raw scores plus independent top-k union
are sealed.  No probability, calibrator, learning, or production gate runs.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from neural.baby.candidate_universe import (  # noqa: E402
    DEFAULT_TOP_K,
    INDEPENDENT_SCORE_CAPTURE_VERSION,
    build_independent_union,
    seal_independent_score_capture,
    validate_candidate_vocabulary,
    validate_independent_score_capture,
)
from neural.baby.pending_question_semantics import canonical_json_sha256  # noqa: E402
from neural.baby.question_calibration import (  # noqa: E402
    rank_raw_scores,
    validate_preregistered_manifest,
)
from scripts.research.j1_1_capture_raw_scores import (  # noqa: E402
    ADAPTER_PATH,
    BASE_MODEL_ID,
    _load_local_core,
    _score_local_candidates,
    _sha256_directory,
)


DEFAULT_MANIFEST = (
    PROJECT_ROOT / "scripts" / "research" / "manifests"
    / "j1_1_train_calibration_a_20260716.json"
)
DEFAULT_VOCABULARY = (
    PROJECT_ROOT / "scripts" / "research" / "inputs"
    / "j1_1_candidate_vocabulary_v2_20260716.json"
)
DEFAULT_CAPTURE = (
    PROJECT_ROOT / "scripts" / "research" / "inputs"
    / "j1_1_candidate_universe_v2_raw_scores_20260716.json"
)
DEFAULT_REPORT = (
    PROJECT_ROOT / "claudedocs" / "research"
    / "j1_1_candidate_universe_v2_capture_20260716.json"
)

GRAPH_SCORE_QUERY = """
UNWIND $candidate_ids AS candidate_id
MATCH (candidate:Concept {id: candidate_id})
OPTIONAL MATCH (cue:Concept)-[rel:RELATES_TO]-(candidate)
WHERE toLower(trim(toString(cue.name))) IN $cue_terms
WITH candidate,
     max(CASE WHEN rel IS NULL THEN 0.0
              ELSE coalesce(rel.hebb_strength, rel.strength, 0.0) END) AS raw_score
RETURN candidate.id AS concept_id,
       candidate.name AS concept_name,
       coalesce(raw_score, 0.0) AS raw_score
ORDER BY candidate.id
"""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json_new(path: Path, payload: dict[str, Any]) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite J1.1B capture artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _question_concepts(
    vocabulary: dict[str, Any],
    order: int,
) -> list[dict[str, str]]:
    scope = next(
        item for item in vocabulary["question_scopes"]
        if int(item["order"]) == order
    )
    excluded = {
        item["concept_id"] for item in scope.get("cue_exclusions") or []
    }
    return [
        dict(item) for item in vocabulary["eligible_concepts"]
        if item["concept_id"] not in excluded
    ]


async def _capture_graph_scores(
    manifest: dict[str, Any],
    vocabulary: dict[str, Any],
) -> dict[int, list[dict[str, Any]]]:
    load_dotenv(PROJECT_ROOT / ".env", override=False)
    from neural.baby.neo4j_db import (  # imported after .env is loaded
        BrainDatabase,
        close_driver,
        init_driver,
    )

    await init_driver()
    captures: dict[int, list[dict[str, Any]]] = {}
    try:
        database = BrainDatabase()
        async with database.driver.session(database=os.getenv("NEO4J_DATABASE")) as session:
            for question in manifest["questions"]:
                order = int(question["order"])
                concepts = _question_concepts(vocabulary, order)
                expected = {
                    item["concept_id"]: item["concept_name"] for item in concepts
                }
                result = await session.run(
                    GRAPH_SCORE_QUERY,
                    candidate_ids=list(expected),
                    cue_terms=[str(item).strip().casefold() for item in question["cue_terms"]],
                )
                records = await result.fetch(len(expected) + 1)
                scores = [{
                    "concept_id": str(record["concept_id"]),
                    "concept_name": str(record["concept_name"]),
                    "raw_score": float(record["raw_score"] or 0.0),
                } for record in records]
                actual = {item["concept_id"]: item["concept_name"] for item in scores}
                if actual != expected:
                    raise RuntimeError(
                        f"graph scope mismatch at question order {order}"
                    )
                captures[order] = rank_raw_scores(scores)
                print(
                    f"graph order={order} scored={len(scores)}",
                    flush=True,
                )
    finally:
        await close_driver()
    return captures


def _capture_local_scores(
    manifest: dict[str, Any],
    vocabulary: dict[str, Any],
    *,
    batch_size: int,
) -> tuple[dict[int, list[dict[str, Any]]], dict[str, Any]]:
    adapter_hash = _sha256_directory(ADAPTER_PATH)
    torch_module, tokenizer, model, device, revision, trainable = _load_local_core()
    torch_module.cuda.reset_peak_memory_stats(device)
    captures: dict[int, list[dict[str, Any]]] = {}
    try:
        for question in manifest["questions"]:
            order = int(question["order"])
            concepts = _question_concepts(vocabulary, order)
            combined: list[dict[str, Any]] = []
            for start in range(0, len(concepts), batch_size):
                batch = concepts[start : start + batch_size]
                combined.extend(_score_local_candidates(
                    torch_module,
                    tokenizer,
                    model,
                    device,
                    question["question"],
                    batch,
                ))
            captures[order] = rank_raw_scores(combined)
            print(
                f"local_core order={order} scored={len(combined)}",
                flush=True,
            )
        peak_memory = int(torch_module.cuda.max_memory_allocated(device))
    finally:
        del model
        torch_module.cuda.empty_cache()

    metadata = {
        "base_model_id": BASE_MODEL_ID,
        "base_model_revision": revision,
        "adapter_sha256": adapter_hash,
        "model_snapshot_sha256": canonical_json_sha256({
            "predictor": "local_core",
            "base_model_id": BASE_MODEL_ID,
            "base_model_revision": revision,
            "adapter_sha256": adapter_hash,
            "scoring_contract": "mean_conditional_token_log_probability_v1",
        }),
        "device": str(device),
        "trainable_parameter_count": trainable,
        "batch_size": batch_size,
        "peak_cuda_memory_bytes": peak_memory,
    }
    return captures, metadata


def _build_report(capture: dict[str, Any]) -> dict[str, Any]:
    per_question = []
    for question in capture["questions"]:
        union = question["independent_union"]
        graph_top = set(union["graph_top_k_ids"])
        local_top = set(union["local_core_top_k_ids"])
        names = {
            item["concept_id"]: item["concept_name"] for item in union["union"]
        }
        per_question.append({
            "order": question["order"],
            "question_id": question["question_id"],
            "eligible_concept_count": question["eligible_concept_count"],
            "graph_top_k_names": [names[item] for item in union["graph_top_k_ids"]],
            "local_core_top_k_names": [names[item] for item in union["local_core_top_k_ids"]],
            "top_k_overlap_count": len(graph_top & local_top),
            "union_count": union["union_count"],
        })
    return {
        "phase": "J1.1B",
        "status": "raw_scores_sealed_pending_union_semantic_review",
        "captured_at": capture["captured_at"],
        "independent_score_capture_sha256": capture[
            "independent_score_capture_sha256"
        ],
        "question_count": capture["question_count"],
        "per_question": per_question,
        "independent_full_vocabulary_raw_score_gate": True,
        "fair_candidate_universe_gate": True,
        "union_semantic_review_gate": False,
        "calibrator_fit_gate": False,
        "database_writes": False,
        "learning_enabled": False,
        "probabilities_computed": False,
        "heldout_gate": False,
        "performance_claim_gate": False,
        "production_promotion_gate": False,
        "block_reasons": ["independent_union_semantic_labels_not_reviewed"],
        "next_step": (
            "draft_semantic_labels_for_independent_union_against_reviewed_"
            "reference_answers_then_stop_before_calibrator_fit"
        ),
    }


def capture(args: argparse.Namespace) -> dict[str, Any]:
    if args.capture.exists() or args.report.exists():
        raise FileExistsError("refusing to overwrite existing J1.1B capture artifacts")
    if not 1 <= args.batch_size <= 64:
        raise ValueError("batch-size must be between 1 and 64")
    manifest = validate_preregistered_manifest(_load_json(args.manifest))
    vocabulary = validate_candidate_vocabulary(_load_json(args.vocabulary))
    if vocabulary["manifest_contract_sha256"] != manifest["contract_sha256"]:
        raise ValueError("vocabulary and manifest are not bound")

    graph = asyncio.run(_capture_graph_scores(manifest, vocabulary))
    local, local_metadata = _capture_local_scores(
        manifest,
        vocabulary,
        batch_size=args.batch_size,
    )
    questions: list[dict[str, Any]] = []
    for question in manifest["questions"]:
        order = int(question["order"])
        concepts = _question_concepts(vocabulary, order)
        independent_union = build_independent_union(
            concepts,
            graph[order],
            local[order],
            top_k=DEFAULT_TOP_K,
        )
        questions.append({
            "order": order,
            "question_id": question["question_id"],
            "question_sha256": question["question_sha256"],
            "eligible_concept_count": len(concepts),
            "graph_raw_scores": graph[order],
            "local_core_raw_scores": local[order],
            "independent_union": independent_union,
        })

    captured_at = _now_iso()
    result = seal_independent_score_capture({
        "independent_score_capture_version": INDEPENDENT_SCORE_CAPTURE_VERSION,
        "phase": "J1.1B",
        "status": "raw_scores_sealed",
        "captured_at": captured_at,
        "candidate_vocabulary_sha256": vocabulary["candidate_vocabulary_sha256"],
        "manifest_contract_sha256": manifest["contract_sha256"],
        "graph_predictor": {
            "implementation_sha256": _sha256_file(
                PROJECT_ROOT / "neural" / "baby" / "neo4j_db.py"
            ),
            "scoring_contract": "max_cue_edge_strength_full_vocabulary_v1",
            "unconnected_candidate_score": 0.0,
        },
        "local_core_predictor": local_metadata,
        "question_count": len(questions),
        "questions": questions,
        "database_writes": False,
        "learning_enabled": False,
        "gpu_inference_executed": True,
        "probabilities_computed": False,
        "calibrator_fit_allowed": False,
        "heldout_gate": False,
        "performance_claim_gate": False,
        "production_promotion_gate": False,
    })
    result = validate_independent_score_capture(vocabulary, result)
    report = _build_report(result)
    _write_json_new(args.capture, result)
    _write_json_new(args.report, report)
    return report


def audit(args: argparse.Namespace) -> dict[str, Any]:
    vocabulary = validate_candidate_vocabulary(_load_json(args.vocabulary))
    result = validate_independent_score_capture(
        vocabulary,
        _load_json(args.capture),
    )
    return _build_report(result)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("capture", "audit"))
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--vocabulary", type=Path, default=DEFAULT_VOCABULARY)
    parser.add_argument("--capture", type=Path, default=DEFAULT_CAPTURE)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--batch-size", type=int, default=16)
    return parser.parse_args()


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args()
    report = capture(args) if args.action == "capture" else audit(args)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
