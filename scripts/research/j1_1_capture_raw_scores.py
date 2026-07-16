"""Preregister J1.1 questions and seal graph/local-core raw scores before reveal.

The capture path is intentionally read-only: Neo4j is queried but never
mutated, and the local core runs under torch.inference_mode() with every
parameter frozen.  It emits raw scores only; probability calibration waits for
new user answers and reviewed semantic labels.
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


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from neural.baby.pending_question_semantics import canonical_json_sha256  # noqa: E402
from neural.baby.question_calibration import (  # noqa: E402
    RAW_SCORE_MODE,
    RAW_SCORE_PACK_VERSION,
    seal_question_manifest,
    seal_raw_score_pack,
    rank_raw_scores,
    validate_preregistered_manifest,
    validate_raw_score_pack,
)


DEFAULT_DRAFT = (
    PROJECT_ROOT / "scripts" / "research" / "manifests"
    / "j1_1_train_calibration_a_20260716_draft.json"
)
DEFAULT_MANIFEST = (
    PROJECT_ROOT / "scripts" / "research" / "manifests"
    / "j1_1_train_calibration_a_20260716.json"
)
DEFAULT_RAW_PACK = (
    PROJECT_ROOT / "scripts" / "research" / "inputs"
    / "j1_1_train_calibration_a_20260716_raw_scores_sealed.json"
)
DEFAULT_REPORT = (
    PROJECT_ROOT / "claudedocs" / "research"
    / "j1_1_train_calibration_capture_20260716.json"
)
ADAPTER_PATH = PROJECT_ROOT / "models" / "local_core_adapter"
BASE_MODEL_ID = "Qwen/Qwen2.5-0.5B-Instruct"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json_new(path: Path, payload: dict[str, Any]) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite sealed artifact: {path}")
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


def _sha256_directory(path: Path) -> str:
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


def prepare_manifest(draft_path: Path, manifest_path: Path) -> dict[str, Any]:
    draft = _load_json(draft_path)
    created_at = _now_iso()
    draft["created_at"] = created_at
    draft["approval_recorded_at"] = created_at
    manifest = seal_question_manifest(draft)
    validate_preregistered_manifest(manifest)
    _write_json_new(manifest_path, manifest)
    return manifest


async def _capture_graph(manifest: dict[str, Any]) -> dict[str, Any]:
    from neural.baby.neo4j_db import (  # imported only for the capture action
        BrainDatabase,
        close_driver,
        init_driver,
    )

    implementation_hash = _sha256_file(PROJECT_ROOT / "neural" / "baby" / "neo4j_db.py")
    await init_driver()
    database = BrainDatabase()
    captures: list[dict[str, Any]] = []
    try:
        for question in manifest["questions"]:
            snapshot = await database.prepare_curiosity_prediction(
                question["question"],
                cue_terms=question["cue_terms"],
                cue_limit=4,
                prediction_limit=8,
            )
            if not snapshot:
                raise RuntimeError(f"no graph snapshot for question order {question['order']}")
            predictions = list(snapshot.get("predicted_concepts") or [])
            if len(predictions) < 4:
                raise RuntimeError(
                    f"question order {question['order']} has fewer than four graph candidates"
                )
            captures.append({
                "order": question["order"],
                "question_sha256": question["question_sha256"],
                "captured_at": snapshot["captured_at"],
                "cue_concepts": snapshot.get("cue_concepts") or [],
                "predicted_concepts": predictions,
            })
    finally:
        await close_driver()

    state_fingerprint = {
        "predictor": "graph",
        "implementation_sha256": implementation_hash,
        "snapshot_scope": "query_scoped_not_full_database",
        "captures": captures,
    }
    return {
        "implementation_sha256": implementation_hash,
        "model_snapshot_sha256": canonical_json_sha256(state_fingerprint),
        "snapshot_scope": "query_scoped_not_full_database",
        "captures": captures,
    }


def _load_local_core():
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is required for the explicitly approved J1.1 GPU inference")
    device = torch.device("cuda:0")
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL_ID, local_files_only=True)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    base = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL_ID,
        dtype=torch.float16,
        local_files_only=True,
    ).to(device)
    model = PeftModel.from_pretrained(
        base,
        str(ADAPTER_PATH),
        is_trainable=False,
    ).to(device)
    for parameter in model.parameters():
        parameter.requires_grad_(False)
    model.eval()
    trainable = sum(parameter.numel() for parameter in model.parameters() if parameter.requires_grad)
    if trainable != 0:
        raise RuntimeError("read-only local-core load unexpectedly exposed trainable parameters")
    revision = str(getattr(model.config, "_commit_hash", None) or "local_cache_revision_unavailable")
    return torch, tokenizer, model, device, revision, trainable


def _score_local_candidates(
    torch_module,
    tokenizer,
    model,
    device,
    question: str,
    concepts: list[dict[str, str]],
) -> list[dict[str, Any]]:
    messages = [
        {
            "role": "system",
            "content": "질문과 관련된 개념 이름 하나를 답하는 의미 연관성 평가기다.",
        },
        {
            "role": "user",
            "content": f"질문: {question}\n관련 개념:",
        },
    ]
    prompt = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )
    prompt_ids = tokenizer(prompt, add_special_tokens=False)["input_ids"]
    sequences: list[list[int]] = []
    for concept in concepts:
        full_ids = tokenizer(
            prompt + concept["concept_name"],
            add_special_tokens=False,
        )["input_ids"]
        if full_ids[: len(prompt_ids)] != prompt_ids or len(full_ids) <= len(prompt_ids):
            raise RuntimeError("tokenizer did not preserve the sealed prompt prefix")
        sequences.append(full_ids)

    max_length = max(len(sequence) for sequence in sequences)
    input_ids = torch_module.full(
        (len(sequences), max_length),
        tokenizer.pad_token_id,
        dtype=torch_module.long,
        device=device,
    )
    attention_mask = torch_module.zeros_like(input_ids)
    for index, sequence in enumerate(sequences):
        input_ids[index, : len(sequence)] = torch_module.tensor(sequence, device=device)
        attention_mask[index, : len(sequence)] = 1

    scores: list[dict[str, Any]] = []
    with torch_module.inference_mode():
        logits = model(
            input_ids=input_ids,
            attention_mask=attention_mask,
            use_cache=False,
        ).logits
        for index, (concept, sequence) in enumerate(zip(concepts, sequences)):
            start = len(prompt_ids)
            end = len(sequence)
            token_logits = logits[index, start - 1 : end - 1].float()
            target_ids = input_ids[index, start:end]
            token_log_probabilities = torch_module.log_softmax(
                token_logits,
                dim=-1,
            ).gather(1, target_ids.unsqueeze(1)).squeeze(1)
            scores.append({
                "concept_id": concept["concept_id"],
                "concept_name": concept["concept_name"],
                "raw_score": float(token_log_probabilities.mean().item()),
            })
    return rank_raw_scores(scores)


def _capture_local_core(
    manifest: dict[str, Any],
    graph_capture: dict[str, Any],
) -> dict[str, Any]:
    adapter_hash = _sha256_directory(ADAPTER_PATH)
    torch_module, tokenizer, model, device, revision, trainable = _load_local_core()
    torch_module.cuda.reset_peak_memory_stats(device)
    model_hash = canonical_json_sha256({
        "predictor": "local_core",
        "base_model_id": BASE_MODEL_ID,
        "base_model_revision": revision,
        "adapter_sha256": adapter_hash,
        "scoring_contract": "mean_conditional_token_log_probability_v1",
    })
    captured: list[dict[str, Any]] = []
    graph_by_order = {item["order"]: item for item in graph_capture["captures"]}
    for question in manifest["questions"]:
        graph_item = graph_by_order[question["order"]]
        concepts = [
            {
                "concept_id": str(item["id"]),
                "concept_name": str(item["name"]),
            }
            for item in graph_item["predicted_concepts"]
        ]
        scores = _score_local_candidates(
            torch_module,
            tokenizer,
            model,
            device,
            question["question"],
            concepts,
        )
        captured.append({
            "order": question["order"],
            "captured_at": _now_iso(),
            "raw_scores": scores,
        })
    peak_memory = int(torch_module.cuda.max_memory_allocated(device))
    del model
    torch_module.cuda.empty_cache()
    return {
        "adapter_sha256": adapter_hash,
        "model_snapshot_sha256": model_hash,
        "base_model_id": BASE_MODEL_ID,
        "base_model_revision": revision,
        "device": str(device),
        "trainable_parameter_count": trainable,
        "peak_cuda_memory_bytes": peak_memory,
        "captures": captured,
    }


def capture_raw_scores(manifest_path: Path) -> dict[str, Any]:
    manifest = validate_preregistered_manifest(_load_json(manifest_path))
    graph = asyncio.run(_capture_graph(manifest))
    local = _capture_local_core(manifest, graph)
    graph_by_order = {item["order"]: item for item in graph["captures"]}
    local_by_order = {item["order"]: item for item in local["captures"]}
    questions: list[dict[str, Any]] = []
    score_count = 0
    for question in manifest["questions"]:
        graph_item = graph_by_order[question["order"]]
        local_item = local_by_order[question["order"]]
        concepts = [
            {
                "concept_id": str(item["id"]),
                "concept_name": str(item["name"]),
            }
            for item in graph_item["predicted_concepts"]
        ]
        graph_scores = rank_raw_scores([
            {
                "concept_id": str(item["id"]),
                "concept_name": str(item["name"]),
                "raw_score": float(item["score"]),
            }
            for item in graph_item["predicted_concepts"]
        ])
        entry = {
            "order": question["order"],
            "question_id": question["question_id"],
            "question": question["question"],
            "question_sha256": question["question_sha256"],
            "cue_terms": question["cue_terms"],
            "cue_concepts": graph_item["cue_concepts"],
            "concept_universe": concepts,
            "predictors": {
                "graph": {
                    "predictor": "graph",
                    "model_snapshot_sha256": graph["model_snapshot_sha256"],
                    "captured_at": graph_item["captured_at"],
                    "raw_score_type": "graph_max_relationship_strength",
                    "raw_scores": graph_scores,
                },
                "local_core": {
                    "predictor": "local_core",
                    "model_snapshot_sha256": local["model_snapshot_sha256"],
                    "captured_at": local_item["captured_at"],
                    "raw_score_type": "mean_conditional_token_log_probability",
                    "raw_scores": local_item["raw_scores"],
                },
            },
        }
        score_count += len(concepts)
        questions.append(entry)

    pack = seal_raw_score_pack({
        "raw_score_pack_version": RAW_SCORE_PACK_VERSION,
        "phase": "J1.1",
        "mode": RAW_SCORE_MODE,
        "manifest_id": manifest["manifest_id"],
        "contract_sha256": manifest["contract_sha256"],
        "split": "train_calibration",
        "created_at": min(
            item["captured_at"] for item in graph["captures"]
        ),
        "sealed_at": _now_iso(),
        "question_count": len(questions),
        "raw_score_count_per_predictor": score_count,
        "learning_enabled": False,
        "database_writes": False,
        "gradients_enabled": False,
        "optimizer_created": False,
        "gpu_inference_read_only": True,
        "questions_revealed_before_capture": False,
        "probabilities_created": False,
        "calibrator_fitted": False,
        "heldout_gate": False,
        "performance_claim_gate": False,
        "production_promotion_gate": False,
        "graph_implementation_sha256": graph["implementation_sha256"],
        "graph_model_snapshot_sha256": graph["model_snapshot_sha256"],
        "graph_snapshot_scope": graph["snapshot_scope"],
        "local_core_base_model_id": local["base_model_id"],
        "local_core_base_model_revision": local["base_model_revision"],
        "local_core_adapter_sha256": local["adapter_sha256"],
        "local_core_model_snapshot_sha256": local["model_snapshot_sha256"],
        "local_core_device": local["device"],
        "local_core_trainable_parameter_count": local["trainable_parameter_count"],
        "local_core_peak_cuda_memory_bytes": local["peak_cuda_memory_bytes"],
        "questions": questions,
    })
    return validate_raw_score_pack(manifest, pack)


def build_report(
    manifest: dict[str, Any],
    raw_pack: dict[str, Any],
    manifest_path: Path,
    raw_pack_path: Path,
) -> dict[str, Any]:
    return {
        "status": "awaiting_user_answers",
        "phase": "J1.1",
        "mode": RAW_SCORE_MODE,
        "created_at": _now_iso(),
        "manifest_id": manifest["manifest_id"],
        "contract_sha256": manifest["contract_sha256"],
        "raw_score_pack_sha256": raw_pack["raw_score_pack_sha256"],
        "question_count": raw_pack["question_count"],
        "raw_score_count_per_predictor": raw_pack["raw_score_count_per_predictor"],
        "graph_snapshot_scope": raw_pack["graph_snapshot_scope"],
        "local_core_device": raw_pack["local_core_device"],
        "local_core_gpu_peak_memory_bytes": raw_pack["local_core_peak_cuda_memory_bytes"],
        "manifest_path": str(manifest_path.resolve()),
        "raw_score_pack_path": str(raw_pack_path.resolve()),
        "preregistered_before_capture": True,
        "questions_revealed_before_capture": False,
        "same_concept_universe_per_predictor": True,
        "learning_enabled": False,
        "database_writes": False,
        "probabilities_created": False,
        "calibrator_fitted": False,
        "heldout_gate": False,
        "performance_claim_gate": False,
        "production_promotion_gate": False,
        "next_step": "collect_new_user_answers_then_review_candidate_labels_and_fit_train_only_calibrators",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "capture", "audit"))
    parser.add_argument("--draft", type=Path, default=DEFAULT_DRAFT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--raw-pack", type=Path, default=DEFAULT_RAW_PACK)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    return parser.parse_args()


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args()
    if args.action == "prepare":
        manifest = prepare_manifest(args.draft, args.manifest)
        output = {
            "status": "preregistered",
            "manifest_id": manifest["manifest_id"],
            "question_count": manifest["question_count"],
            "contract_sha256": manifest["contract_sha256"],
            "questions_revealed": False,
            "manifest_path": str(args.manifest.resolve()),
        }
    elif args.action == "capture":
        manifest = validate_preregistered_manifest(_load_json(args.manifest))
        raw_pack = capture_raw_scores(args.manifest)
        _write_json_new(args.raw_pack, raw_pack)
        report = build_report(manifest, raw_pack, args.manifest, args.raw_pack)
        _write_json_new(args.report, report)
        output = {
            "status": report["status"],
            "question_count": report["question_count"],
            "raw_score_count_per_predictor": report["raw_score_count_per_predictor"],
            "local_core_device": report["local_core_device"],
            "contract_sha256": report["contract_sha256"],
            "raw_score_pack_sha256": report["raw_score_pack_sha256"],
            "database_writes": False,
            "learning_enabled": False,
            "probabilities_created": False,
            "questions_revealed_before_capture": False,
            "report_path": str(args.report.resolve()),
        }
    else:
        manifest = validate_preregistered_manifest(_load_json(args.manifest))
        raw_pack = validate_raw_score_pack(manifest, _load_json(args.raw_pack))
        output = {
            "status": "valid",
            "question_count": raw_pack["question_count"],
            "raw_score_count_per_predictor": raw_pack["raw_score_count_per_predictor"],
            "contract_sha256": manifest["contract_sha256"],
            "raw_score_pack_sha256": raw_pack["raw_score_pack_sha256"],
        }
    print(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
