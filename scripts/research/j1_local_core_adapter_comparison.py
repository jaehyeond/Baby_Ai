"""Run or audit the frozen J1 Local-Core base-versus-adapter comparison."""

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
from neural.baby.local_core_adapter_comparison import (  # noqa: E402
    build_local_core_adapter_comparison,
    validate_local_core_adapter_comparison,
)
from neural.baby.local_core_conditioning_ablation import (  # noqa: E402
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
DEFAULT_CONDITIONING = (
    PROJECT_ROOT
    / "claudedocs/research/j1_local_core_conditioning_ablation_b_20260722.json"
)
DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "claudedocs/research/j1_local_core_adapter_comparison_b_20260722.json"
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json_new(path: Path, payload: dict[str, Any]) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite adapter comparison: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _load_context(
    args: argparse.Namespace,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    manifest = validate_exploratory_question_manifest(_load_json(args.manifest))
    capture = validate_exploratory_pre_answer_capture(
        _load_json(args.capture), manifest
    )
    answer_pack = validate_exploratory_answer_pack(
        _load_json(args.answer_pack), manifest, capture
    )
    conditioning = validate_local_core_conditioning_ablation(
        _load_json(args.conditioning), manifest, capture, answer_pack
    )
    return manifest, capture, answer_pack, conditioning


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
    target_rank_comparison = []
    for question in payload["questions"]:
        target_rank_comparison.append({
            "question_id": question["question_id"],
            "adapter_actual_top_k": [
                item["concept_name"]
                for item in question["rankings"]["adapter_actual"]
            ],
            "base_actual_top_k": [
                item["concept_name"]
                for item in question["rankings"]["base_actual"]
            ],
            "available_target_ranks": [
                {
                    "target": item["target_concept"],
                    "adapter_actual": item["ranks"]["adapter_actual"],
                    "base_actual": item["ranks"]["base_actual"],
                    "base_content_free_delta": item["ranks"][
                        "base_content_free_delta"
                    ],
                    "base_shuffle_delta": item["ranks"][
                        "base_shuffle_delta"
                    ],
                }
                for item in question["target_diagnostics"]
                if item["available_in_candidate_scope"]
            ],
        })
    return {
        "phase": payload["phase"],
        "status": payload["status"],
        "local_core_adapter_comparison_sha256": payload[
            "local_core_adapter_comparison_sha256"
        ],
        "adapter_actual_digest_match_count": payload[
            "adapter_actual_digest_match_count"
        ],
        "direct_adapter_vs_base": payload["direct_adapter_vs_base"],
        "adapter_reference": payload["adapter_reference"],
        "base_ranking_summaries": payload["base_ranking_summaries"],
        "base_aggregate_comparisons": payload["base_aggregate_comparisons"],
        "target_rank_comparison": target_rank_comparison,
        "database_writes": payload["database_writes"],
        "learning_enabled": payload["learning_enabled"],
        "root_cause_claim_gate": payload["root_cause_claim_gate"],
        "performance_claim_gate": payload["performance_claim_gate"],
        "next_step": payload["next_step"],
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    if args.output.exists():
        raise FileExistsError("refusing to overwrite adapter comparison artifact")
    if not 1 <= args.batch_size <= 64:
        raise ValueError("batch-size must be between 1 and 64")
    manifest, capture, answer_pack, conditioning = _load_context(args)
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
    adapter_actual_scores: dict[int, list[dict[str, Any]]] = {}
    base_actual_scores: dict[int, list[dict[str, Any]]] = {}
    base_content_free_scores: dict[int, list[dict[str, Any]]] = {}
    base_shuffled_scores: dict[int, list[dict[str, Any]]] = {}
    try:
        for question in manifest["questions"]:
            order = int(question["order"])
            adapter_actual_scores[order] = _score_candidates(
                torch_module,
                tokenizer,
                model,
                device,
                question["question"],
                scopes[order],
                batch_size=args.batch_size,
            )
            print(
                f"adapter order={order} actual={len(adapter_actual_scores[order])}",
                flush=True,
            )

        enabled_before = model.get_model_status().enabled
        with model.disable_adapter():
            enabled_during = model.get_model_status().enabled
            if enabled_during is not False:
                raise RuntimeError("PEFT adapter was not fully disabled")
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
            print(f"base content_free={len(global_content_free)}", flush=True)

            question_count = len(manifest["questions"])
            for question in manifest["questions"]:
                order = int(question["order"])
                concepts = scopes[order]
                base_actual_scores[order] = _score_candidates(
                    torch_module,
                    tokenizer,
                    model,
                    device,
                    question["question"],
                    concepts,
                    batch_size=args.batch_size,
                )
                shuffled_question = manifest["questions"][(order + 1) % question_count]
                base_shuffled_scores[order] = _score_candidates(
                    torch_module,
                    tokenizer,
                    model,
                    device,
                    shuffled_question["question"],
                    concepts,
                    batch_size=args.batch_size,
                )
                base_content_free_scores[order] = [
                    global_content_free_by_id[item["concept_id"]]
                    for item in concepts
                ]
                print(
                    f"base order={order} actual={len(base_actual_scores[order])} "
                    f"shuffled={len(base_shuffled_scores[order])}",
                    flush=True,
                )
        enabled_after = model.get_model_status().enabled
        if enabled_before is not True or enabled_after is not True:
            raise RuntimeError("PEFT adapter enable state was not restored")
        peak_memory = int(torch_module.cuda.max_memory_allocated(device))
    finally:
        del model
        torch_module.cuda.empty_cache()

    adapter_model_snapshot_sha256 = canonical_json_sha256({
        "predictor": "local_core",
        "base_model_id": BASE_MODEL_ID,
        "base_model_revision": revision,
        "adapter_sha256": adapter_sha256,
        "scoring_contract": "mean_conditional_token_log_probability_v1",
    })
    base_model_snapshot_sha256 = canonical_json_sha256({
        "predictor": "local_core_base_adapter_disabled",
        "base_model_id": BASE_MODEL_ID,
        "base_model_revision": revision,
        "adapter_disable_method": "peft_disable_adapter_context",
        "scoring_contract": "mean_conditional_token_log_probability_v1",
    })
    comparison_implementation_sha256 = canonical_json_sha256({
        "module_sha256": _sha256_file(
            PROJECT_ROOT / "neural/baby/local_core_adapter_comparison.py"
        ),
        "script_sha256": _sha256_file(Path(__file__).resolve()),
    })
    result = build_local_core_adapter_comparison(
        manifest,
        capture,
        answer_pack,
        conditioning,
        source_concepts,
        adapter_actual_scores,
        base_actual_scores,
        base_content_free_scores,
        base_shuffled_scores,
        predictor_metadata={
            "base_model_id": BASE_MODEL_ID,
            "base_model_revision": revision,
            "adapter_sha256": adapter_sha256,
            "adapter_model_snapshot_sha256": adapter_model_snapshot_sha256,
            "base_model_snapshot_sha256": base_model_snapshot_sha256,
            "adapter_disable_method": "peft_disable_adapter_context",
            "score_implementation_sha256": _sha256_file(
                PROJECT_ROOT / "scripts/research/j1_1_capture_raw_scores.py"
            ),
            "comparison_implementation_sha256": comparison_implementation_sha256,
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
    manifest, capture, answer_pack, conditioning = _load_context(args)
    result = validate_local_core_adapter_comparison(
        _load_json(args.output),
        manifest,
        capture,
        answer_pack,
        conditioning,
    )
    return _summary(result)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("run", "audit-existing"))
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--capture", type=Path, default=DEFAULT_CAPTURE)
    parser.add_argument("--answer-pack", type=Path, default=DEFAULT_ANSWER_PACK)
    parser.add_argument("--conditioning", type=Path, default=DEFAULT_CONDITIONING)
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
