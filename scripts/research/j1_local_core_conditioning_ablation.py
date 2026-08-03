"""Run or audit the frozen J1 Local-Core question-conditioning ablation."""

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
    validate_exploratory_pre_answer_capture,
    validate_exploratory_question_manifest,
)
from neural.baby.exploratory_signal_audit import (  # noqa: E402
    validate_exploratory_answer_pack,
)
from neural.baby.local_core_conditioning_ablation import (  # noqa: E402
    build_local_core_conditioning_ablation,
    validate_local_core_conditioning_ablation,
)
from neural.baby.pending_question_semantics import (  # noqa: E402
    canonical_json_sha256,
)
from neural.baby.question_calibration import rank_raw_scores  # noqa: E402
from scripts.research.j1_1_candidate_universe_v2 import (  # noqa: E402
    _read_all_concepts,
)
from scripts.research.j1_1_candidate_universe_v2_capture import (  # noqa: E402
    _sha256_file,
)
from scripts.research.j1_1_capture_raw_scores import (  # noqa: E402
    ADAPTER_PATH,
    BASE_MODEL_ID,
    _load_local_core,
    _score_local_candidates,
    _sha256_directory,
)


DEFAULT_MANIFEST = (
    PROJECT_ROOT
    / "scripts/research/manifests/j1_1_fresh_selection_b_20260720_draft.json"
)
DEFAULT_CAPTURE = (
    PROJECT_ROOT
    / "scripts/research/inputs/j1_exploratory_pre_answer_probe_b_20260721.json"
)
DEFAULT_ANSWER_PACK = (
    PROJECT_ROOT
    / "scripts/research/inputs/j1_exploratory_external_teacher_answers_b_20260721.json"
)
DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "claudedocs/research/j1_local_core_conditioning_ablation_b_20260722.json"
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json_new(path: Path, payload: dict[str, Any]) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite conditioning artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _load_context(
    args: argparse.Namespace,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    manifest = validate_exploratory_question_manifest(_load_json(args.manifest))
    capture = validate_exploratory_pre_answer_capture(
        _load_json(args.capture), manifest
    )
    answer_pack = validate_exploratory_answer_pack(
        _load_json(args.answer_pack), manifest, capture
    )
    return manifest, capture, answer_pack


def _score_candidates(
    torch_module,
    tokenizer,
    model,
    device,
    question: str,
    concepts: list[dict[str, str]],
    *,
    batch_size: int,
) -> list[dict[str, Any]]:
    combined: list[dict[str, Any]] = []
    for start in range(0, len(concepts), batch_size):
        combined.extend(_score_local_candidates(
            torch_module,
            tokenizer,
            model,
            device,
            question,
            concepts[start : start + batch_size],
        ))
    return rank_raw_scores(combined)


def _summary(payload: dict[str, Any]) -> dict[str, Any]:
    per_question = []
    for question in payload["questions"]:
        available = [
            item for item in question["target_diagnostics"]
            if item["available_in_candidate_scope"]
        ]
        per_question.append({
            "question_id": question["question_id"],
            "actual_vs_content_free": question["actual_vs_content_free"],
            "actual_vs_shuffled": question["actual_vs_shuffled"],
            "content_free_delta_top_k": [
                item["concept_name"]
                for item in question["rankings"]["content_free_delta"]
            ],
            "available_target_rank_changes": [
                {
                    "target": item["target_concept"],
                    "actual_rank": item["ranks"]["actual"],
                    "content_free_delta_rank": item["ranks"][
                        "content_free_delta"
                    ],
                    "shuffle_delta_rank": item["ranks"]["shuffle_delta"],
                }
                for item in available
            ],
        })
    return {
        "phase": payload["phase"],
        "status": payload["status"],
        "local_core_conditioning_ablation_sha256": payload[
            "local_core_conditioning_ablation_sha256"
        ],
        "actual_digest_match_count": payload["actual_digest_match_count"],
        "aggregate_comparisons": payload["aggregate_comparisons"],
        "diagnostic_warnings": payload["diagnostic_warnings"],
        "ranking_summaries": payload["ranking_summaries"],
        "per_question": per_question,
        "database_writes": payload["database_writes"],
        "learning_enabled": payload["learning_enabled"],
        "performance_claim_gate": payload["performance_claim_gate"],
        "production_promotion_gate": payload["production_promotion_gate"],
        "next_step": payload["next_step"],
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    if args.output.exists():
        raise FileExistsError("refusing to overwrite Local-Core conditioning artifact")
    if not 1 <= args.batch_size <= 64:
        raise ValueError("batch-size must be between 1 and 64")
    manifest, capture, answer_pack = _load_context(args)
    captured_batch_size = int(capture["local_core_predictor"].get("batch_size", 0))
    if args.batch_size != captured_batch_size:
        raise ValueError(
            f"batch-size must reproduce captured value {captured_batch_size}"
        )

    source_concepts = sorted(
        asyncio.run(_read_all_concepts()),
        key=lambda item: (item["id"], item["name"]),
    )
    eligible, _ = classify_candidate_vocabulary(source_concepts)
    scopes: dict[int, list[dict[str, str]]] = {}
    for question in manifest["questions"]:
        scoped, _ = exclude_question_cue_surfaces(
            eligible, question["cue_terms"]
        )
        scopes[int(question["order"])] = scoped

    adapter_sha256 = _sha256_directory(ADAPTER_PATH)
    if adapter_sha256 != capture["local_core_predictor"]["adapter_sha256"]:
        raise ValueError("on-disk adapter does not match exploratory capture")

    torch_module, tokenizer, model, device, revision, trainable = _load_local_core()
    torch_module.cuda.reset_peak_memory_stats(device)
    actual_scores: dict[int, list[dict[str, Any]]] = {}
    content_free_scores: dict[int, list[dict[str, Any]]] = {}
    shuffled_scores: dict[int, list[dict[str, Any]]] = {}
    try:
        global_content_free = _score_candidates(
            torch_module,
            tokenizer,
            model,
            device,
            "",
            eligible,
            batch_size=args.batch_size,
        )
        global_content_free_by_id = {
            item["concept_id"]: item for item in global_content_free
        }
        print(f"content_free scored={len(global_content_free)}", flush=True)

        question_count = len(manifest["questions"])
        for question in manifest["questions"]:
            order = int(question["order"])
            concepts = scopes[order]
            actual_scores[order] = _score_candidates(
                torch_module,
                tokenizer,
                model,
                device,
                question["question"],
                concepts,
                batch_size=args.batch_size,
            )
            shuffled_question = manifest["questions"][(order + 1) % question_count]
            shuffled_scores[order] = _score_candidates(
                torch_module,
                tokenizer,
                model,
                device,
                shuffled_question["question"],
                concepts,
                batch_size=args.batch_size,
            )
            content_free_scores[order] = [
                global_content_free_by_id[item["concept_id"]]
                for item in concepts
            ]
            print(
                f"order={order} actual={len(actual_scores[order])} "
                f"shuffled={len(shuffled_scores[order])}",
                flush=True,
            )
        peak_memory = int(torch_module.cuda.max_memory_allocated(device))
    finally:
        del model
        torch_module.cuda.empty_cache()

    model_snapshot_sha256 = canonical_json_sha256({
        "predictor": "local_core",
        "base_model_id": BASE_MODEL_ID,
        "base_model_revision": revision,
        "adapter_sha256": adapter_sha256,
        "scoring_contract": "mean_conditional_token_log_probability_v1",
    })
    implementation_sha256 = canonical_json_sha256({
        "module_sha256": _sha256_file(
            PROJECT_ROOT / "neural/baby/local_core_conditioning_ablation.py"
        ),
        "script_sha256": _sha256_file(Path(__file__).resolve()),
    })
    result = build_local_core_conditioning_ablation(
        manifest,
        capture,
        answer_pack,
        source_concepts,
        actual_scores,
        content_free_scores,
        shuffled_scores,
        predictor_metadata={
            "base_model_id": BASE_MODEL_ID,
            "base_model_revision": revision,
            "adapter_sha256": adapter_sha256,
            "model_snapshot_sha256": model_snapshot_sha256,
            "scoring_contract": "mean_conditional_token_log_probability_v1",
            "score_implementation_sha256": _sha256_file(
                PROJECT_ROOT / "scripts/research/j1_1_capture_raw_scores.py"
            ),
            "ablation_implementation_sha256": implementation_sha256,
            "device": str(device),
            "batch_size": args.batch_size,
            "trainable_parameter_count": trainable,
            "peak_cuda_memory_bytes": peak_memory,
        },
        audited_at=_now_iso(),
    )
    _write_json_new(args.output, result)
    return _summary(result)


def audit_existing(args: argparse.Namespace) -> dict[str, Any]:
    manifest, capture, answer_pack = _load_context(args)
    result = validate_local_core_conditioning_ablation(
        _load_json(args.output), manifest, capture, answer_pack
    )
    return _summary(result)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("run", "audit-existing"))
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--capture", type=Path, default=DEFAULT_CAPTURE)
    parser.add_argument("--answer-pack", type=Path, default=DEFAULT_ANSWER_PACK)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--batch-size", type=int, default=16)
    return parser.parse_args()


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args()
    result = run(args) if args.action == "run" else audit_existing(args)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
