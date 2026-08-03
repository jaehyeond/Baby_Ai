"""Acquire, run, or audit the frozen local J1-R2 embedding baseline."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from neural.baby.candidate_universe import (  # noqa: E402
    validate_candidate_vocabulary,
)
from neural.baby.relevance_embedding_baseline import (  # noqa: E402
    MODEL_ID,
    MODEL_REVISION,
    build_embedding_baseline_artifact,
    embedding_model_contract,
    inspect_local_model_snapshot,
    score_embedding_questions,
    validate_embedding_baseline_artifact,
    validate_embedding_model_decision,
    validate_embedding_snapshot_manifest,
    verify_snapshot_manifest_against_directory,
)
from neural.baby.relevance_lexical_baseline import (  # noqa: E402
    validate_lexical_baseline_artifact,
)


DEFAULT_VOCABULARY = (
    PROJECT_ROOT
    / "scripts"
    / "research"
    / "inputs"
    / "j1_1_candidate_vocabulary_v2_20260716.json"
)
DEFAULT_GENERATOR_SPEC = (
    PROJECT_ROOT
    / "scripts"
    / "research"
    / "specs"
    / "j1_r2_rolling_development_generator_spec_draft_20260723.json"
)
DEFAULT_LABELS = (
    PROJECT_ROOT
    / "scripts"
    / "research"
    / "inputs"
    / "j1_r2_rolling_development_labels_reviewed_20260723.json"
)
DEFAULT_LEXICAL_ARTIFACT = (
    PROJECT_ROOT
    / "claudedocs"
    / "research"
    / "j1_r2_lexical_baseline_development_20260728.json"
)
DEFAULT_DECISION = (
    PROJECT_ROOT
    / "scripts"
    / "research"
    / "inputs"
    / "j1_r2_embedding_model_review_decision_20260728.json"
)
DEFAULT_MODEL_DIR = (
    PROJECT_ROOT.parent
    / "model_cache"
    / "huggingface"
    / f"intfloat--multilingual-e5-small--{MODEL_REVISION}"
)
DEFAULT_SNAPSHOT_MANIFEST = (
    PROJECT_ROOT
    / "scripts"
    / "research"
    / "manifests"
    / "j1_r2_multilingual_e5_small_snapshot_20260728.json"
)
DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "claudedocs"
    / "research"
    / "j1_r2_embedding_baseline_development_20260728.json"
)
EMBEDDING_MODULE = (
    PROJECT_ROOT / "neural" / "baby" / "relevance_embedding_baseline.py"
)
LEXICAL_MODULE = (
    PROJECT_ROOT / "neural" / "baby" / "relevance_lexical_baseline.py"
)
LEXICAL_CLI = PROJECT_ROOT / "scripts" / "research" / "j1_r2_lexical_baseline.py"


LEXICAL_BOUND_PATHS = {
    "anchor_manifest": (
        PROJECT_ROOT
        / "scripts"
        / "research"
        / "manifests"
        / "j1_r2_anchor_regression_manifest_20260722.json"
    ),
    "baseline_cli": LEXICAL_CLI,
    "baseline_module": LEXICAL_MODULE,
    "candidate_vocabulary": DEFAULT_VOCABULARY,
    "cohort_readiness": (
        PROJECT_ROOT
        / "claudedocs"
        / "research"
        / "j1_r2_relevance_cohort_readiness_after_lockbox_freeze_20260723.json"
    ),
    "development_draft_manifest": (
        PROJECT_ROOT
        / "scripts"
        / "research"
        / "manifests"
        / "j1_r2_rolling_development_manifest_draft_20260722.json"
    ),
    "development_generator_spec": DEFAULT_GENERATOR_SPEC,
    "development_labels": DEFAULT_LABELS,
    "development_manifest": (
        PROJECT_ROOT
        / "scripts"
        / "research"
        / "manifests"
        / "j1_r2_rolling_development_manifest_reviewed_20260723.json"
    ),
    "development_review_decisions": (
        PROJECT_ROOT
        / "scripts"
        / "research"
        / "inputs"
        / "j1_r2_rolling_development_review_decisions_20260723.json"
    ),
    "development_review_packet": (
        PROJECT_ROOT
        / "scripts"
        / "research"
        / "inputs"
        / "j1_r2_rolling_development_review_packet_20260723.json"
    ),
    "development_sample_plan": (
        PROJECT_ROOT
        / "scripts"
        / "research"
        / "specs"
        / "j1_r2_rolling_development_sample_size_plan_draft_20260723.json"
    ),
    "lifecycle_contract": (
        PROJECT_ROOT
        / "claudedocs"
        / "research"
        / "j1_r2_relevance_cohort_lifecycle_20260722.json"
    ),
    "lockbox_generator_manifest": (
        PROJECT_ROOT
        / "scripts"
        / "research"
        / "manifests"
        / "j1_r2_one_time_lockbox_manifest_generator_frozen_20260723.json"
    ),
    "r1_contract": (
        PROJECT_ROOT
        / "claudedocs"
        / "research"
        / "j1_r1_relevance_scorer_contract_20260722.json"
    ),
}


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json_new(path: Path, payload: dict[str, Any]) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite existing artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _load_predecessor_inputs(args: argparse.Namespace) -> dict[str, Any]:
    vocabulary = validate_candidate_vocabulary(_load_json(args.vocabulary))
    generator_spec = _load_json(args.generator_spec)
    labels = _load_json(args.labels)
    lexical_artifact = validate_lexical_baseline_artifact(
        _load_json(args.lexical_artifact),
        vocabulary,
        generator_spec,
        labels,
    )
    expected_files = dict(
        lexical_artifact.get("bindings", {}).get("input_file_sha256s", {})
    )
    if set(expected_files) != set(LEXICAL_BOUND_PATHS):
        raise ValueError("lexical predecessor input-file binding set drifted")
    for name, path in LEXICAL_BOUND_PATHS.items():
        if _file_sha256(path) != expected_files[name]:
            raise ValueError(f"lexical predecessor file drifted: {name}")
    return {
        "vocabulary": vocabulary,
        "generator_spec": generator_spec,
        "labels": labels,
        "lexical_artifact": lexical_artifact,
    }


def _load_decision(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(
            "user-approved embedding model decision is missing; "
            "download and inference remain blocked"
        )
    return validate_embedding_model_decision(_load_json(path))


def _load_snapshot(
    path: Path,
    decision: dict[str, Any],
    model_dir: Path,
) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError("sealed local embedding snapshot manifest is missing")
    manifest = validate_embedding_snapshot_manifest(_load_json(path), decision)
    return verify_snapshot_manifest_against_directory(
        manifest,
        decision,
        model_dir,
    )


class _LocalE5Encoder:
    def __init__(self, model_dir: Path, batch_size: int) -> None:
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"

        import torch
        import torch.nn.functional as torch_functional
        import transformers
        from transformers import AutoModel, AutoTokenizer

        if batch_size < 1:
            raise ValueError("batch size must be positive")
        torch.manual_seed(0)
        torch.use_deterministic_algorithms(True)
        self._torch = torch
        self._functional = torch_functional
        self._batch_size = batch_size
        self._tokenizer = AutoTokenizer.from_pretrained(
            str(model_dir),
            local_files_only=True,
            trust_remote_code=False,
        )
        self._model = AutoModel.from_pretrained(
            str(model_dir),
            local_files_only=True,
            trust_remote_code=False,
            use_safetensors=True,
        )
        self._model.to("cpu")
        self._model.eval()
        self._model.requires_grad_(False)
        self._batch_count = 0
        self._max_non_padding_tokens = 0
        self._runtime = {
            "python_version": platform.python_version(),
            "torch_version": str(torch.__version__),
            "transformers_version": str(transformers.__version__),
            "device": "cpu",
            "dtype": "float32",
            "batch_size": batch_size,
            "deterministic_algorithms": True,
            "embedding_dimension": int(self._model.config.hidden_size),
            "model_parameter_count": sum(
                parameter.numel() for parameter in self._model.parameters()
            ),
            "trainable_parameter_count": sum(
                parameter.numel()
                for parameter in self._model.parameters()
                if parameter.requires_grad
            ),
        }
        if self._runtime["trainable_parameter_count"] != 0:
            raise RuntimeError("frozen embedding model has trainable parameters")
        if self._runtime["embedding_dimension"] != 384:
            raise RuntimeError("frozen embedding model dimension drifted")

    def __call__(self, texts: Sequence[str]) -> list[list[float]]:
        vectors = []
        torch = self._torch
        for start in range(0, len(texts), self._batch_size):
            batch = list(texts[start : start + self._batch_size])
            encoded = self._tokenizer(
                batch,
                max_length=512,
                padding=True,
                truncation=True,
                return_tensors="pt",
            )
            self._max_non_padding_tokens = max(
                self._max_non_padding_tokens,
                int(encoded["attention_mask"].sum(dim=1).max().item()),
            )
            self._batch_count += 1
            with torch.inference_mode():
                outputs = self._model(**encoded)
                mask = encoded["attention_mask"][..., None].bool()
                hidden = outputs.last_hidden_state.masked_fill(~mask, 0.0)
                pooled = hidden.sum(dim=1) / encoded["attention_mask"].sum(
                    dim=1
                )[..., None]
                normalized = self._functional.normalize(pooled, p=2, dim=1)
            vectors.extend(normalized.float().cpu().tolist())
        return vectors

    def runtime_metadata(self) -> dict[str, Any]:
        return {
            **self._runtime,
            "encoded_batch_count": self._batch_count,
            "max_non_padding_tokens": self._max_non_padding_tokens,
        }


def _bindings(
    args: argparse.Namespace,
    decision: dict[str, Any],
    snapshot: dict[str, Any],
    lexical_artifact: dict[str, Any],
) -> dict[str, Any]:
    return {
        "lexical_baseline_artifact_sha256": lexical_artifact[
            "lexical_baseline_artifact_sha256"
        ],
        "embedding_model_decision_sha256": decision[
            "embedding_model_decision_sha256"
        ],
        "embedding_snapshot_manifest_sha256": snapshot[
            "embedding_snapshot_manifest_sha256"
        ],
        "embedding_model_contract_sha256": embedding_model_contract()[
            "embedding_model_contract_sha256"
        ],
        "implementation_bundle_sha256": hashlib.sha256(
            (
                _file_sha256(EMBEDDING_MODULE)
                + _file_sha256(Path(__file__).resolve())
            ).encode("ascii")
        ).hexdigest(),
        "input_file_sha256s": {
            "candidate_vocabulary": _file_sha256(args.vocabulary),
            "development_generator_spec": _file_sha256(args.generator_spec),
            "development_labels": _file_sha256(args.labels),
            "lexical_baseline_artifact": _file_sha256(args.lexical_artifact),
            "embedding_model_decision": _file_sha256(args.decision),
            "embedding_snapshot_manifest": _file_sha256(args.snapshot_manifest),
            "embedding_module": _file_sha256(EMBEDDING_MODULE),
            "embedding_cli": _file_sha256(Path(__file__).resolve()),
        },
    }


def readiness(args: argparse.Namespace) -> dict[str, Any]:
    contract = embedding_model_contract()
    block_reasons = []
    predecessor_valid = False
    try:
        _load_predecessor_inputs(args)
        predecessor_valid = True
    except (OSError, ValueError, json.JSONDecodeError):
        block_reasons.append("lexical_predecessor_chain_invalid")

    decision_valid = False
    decision = None
    if not args.decision.is_file():
        block_reasons.append("user_model_download_and_inference_decision_missing")
    else:
        try:
            decision = _load_decision(args.decision)
            decision_valid = True
        except (OSError, ValueError, json.JSONDecodeError):
            block_reasons.append("user_model_download_and_inference_decision_invalid")

    snapshot_valid = False
    if not args.model_dir.is_dir():
        block_reasons.append("pinned_local_model_snapshot_missing")
    if not args.snapshot_manifest.is_file():
        block_reasons.append("sealed_model_snapshot_manifest_missing")
    if (
        decision_valid
        and decision is not None
        and args.model_dir.is_dir()
        and args.snapshot_manifest.is_file()
    ):
        try:
            _load_snapshot(args.snapshot_manifest, decision, args.model_dir)
            snapshot_valid = True
        except (OSError, ValueError, json.JSONDecodeError):
            block_reasons.append("local_model_snapshot_validation_failed")
    if args.output.exists():
        block_reasons.append("embedding_output_already_exists_refuse_overwrite")
    return {
        "phase": contract["phase"],
        "baseline_id": contract["baseline_id"],
        "model_id": contract["model_id"],
        "immutable_revision": contract["immutable_revision"],
        "embedding_model_contract_sha256": contract[
            "embedding_model_contract_sha256"
        ],
        "model_dir": str(args.model_dir),
        "lexical_predecessor_chain_gate": predecessor_valid,
        "model_download_authorized_gate": decision_valid,
        "local_snapshot_present_gate": args.model_dir.is_dir(),
        "snapshot_manifest_present_gate": args.snapshot_manifest.is_file(),
        "local_snapshot_validation_gate": snapshot_valid,
        "embedding_execution_ready_gate": not block_reasons,
        "block_reasons": block_reasons,
        "database_write_gate": False,
        "training_gate": False,
        "lockbox_materialization_gate": False,
        "heldout_gate": False,
        "performance_claim_gate": False,
        "production_promotion_gate": False,
    }


def acquire_model(args: argparse.Namespace) -> dict[str, Any]:
    decision = _load_decision(args.decision)
    if args.snapshot_manifest.exists():
        raise FileExistsError("refusing to overwrite snapshot manifest")

    from huggingface_hub import snapshot_download

    contract = embedding_model_contract()
    resolved = snapshot_download(
        repo_id=MODEL_ID,
        revision=MODEL_REVISION,
        local_dir=args.model_dir,
        allow_patterns=[item["path"] for item in contract["expected_files"]],
        max_workers=4,
    )
    if Path(resolved).resolve() != args.model_dir.resolve():
        raise RuntimeError("snapshot_download returned an unexpected directory")
    manifest = inspect_local_model_snapshot(
        args.model_dir,
        decision,
        created_at=datetime.now(timezone.utc).isoformat(),
        acquisition_method="huggingface_snapshot_download_pinned_revision",
    )
    _write_json_new(args.snapshot_manifest, manifest)
    return {
        "status": manifest["status"],
        "model_id": manifest["model_id"],
        "immutable_revision": manifest["immutable_revision"],
        "total_verified_bytes": manifest["total_verified_bytes"],
        "embedding_snapshot_manifest_sha256": manifest[
            "embedding_snapshot_manifest_sha256"
        ],
        "next_step": "run_frozen_embedding_baseline",
    }


def seal_existing_model(args: argparse.Namespace) -> dict[str, Any]:
    decision = _load_decision(args.decision)
    manifest = inspect_local_model_snapshot(
        args.model_dir,
        decision,
        created_at=datetime.now(timezone.utc).isoformat(),
        acquisition_method="preexisting_local_snapshot_verified_after_user_approval",
    )
    _write_json_new(args.snapshot_manifest, manifest)
    return {
        "status": manifest["status"],
        "total_verified_bytes": manifest["total_verified_bytes"],
        "embedding_snapshot_manifest_sha256": manifest[
            "embedding_snapshot_manifest_sha256"
        ],
        "next_step": "run_frozen_embedding_baseline",
    }


def _execute_scores(
    inputs: dict[str, Any],
    model_dir: Path,
    batch_size: int,
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    encoder = _LocalE5Encoder(model_dir, batch_size)
    scores = score_embedding_questions(
        inputs["vocabulary"]["eligible_concepts"],
        inputs["generator_spec"]["questions"],
        encoder,
    )
    return scores, encoder.runtime_metadata()


def run(args: argparse.Namespace) -> dict[str, Any]:
    inputs = _load_predecessor_inputs(args)
    decision = _load_decision(args.decision)
    snapshot = _load_snapshot(
        args.snapshot_manifest,
        decision,
        args.model_dir,
    )
    scores, runtime = _execute_scores(inputs, args.model_dir, args.batch_size)
    artifact = build_embedding_baseline_artifact(
        inputs["vocabulary"],
        inputs["generator_spec"],
        inputs["labels"],
        inputs["lexical_artifact"],
        decision,
        snapshot,
        scores,
        bindings=_bindings(
            args,
            decision,
            snapshot,
            inputs["lexical_artifact"],
        ),
        runtime=runtime,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    validate_embedding_baseline_artifact(
        artifact,
        inputs["vocabulary"],
        inputs["generator_spec"],
        inputs["labels"],
        inputs["lexical_artifact"],
        decision,
        snapshot,
    )
    _write_json_new(args.output, artifact)
    return _artifact_summary(artifact)


def audit_existing(
    args: argparse.Namespace,
    *,
    rerun_model: bool,
) -> dict[str, Any]:
    inputs = _load_predecessor_inputs(args)
    decision = _load_decision(args.decision)
    snapshot = _load_snapshot(
        args.snapshot_manifest,
        decision,
        args.model_dir,
    )
    artifact = validate_embedding_baseline_artifact(
        _load_json(args.output),
        inputs["vocabulary"],
        inputs["generator_spec"],
        inputs["labels"],
        inputs["lexical_artifact"],
        decision,
        snapshot,
    )
    if rerun_model:
        scores, runtime = _execute_scores(inputs, args.model_dir, args.batch_size)
        expected = build_embedding_baseline_artifact(
            inputs["vocabulary"],
            inputs["generator_spec"],
            inputs["labels"],
            inputs["lexical_artifact"],
            decision,
            snapshot,
            scores,
            bindings=dict(artifact["bindings"]),
            runtime=runtime,
            created_at=str(artifact["created_at"]),
        )
        if artifact != expected:
            raise ValueError("model rerun does not reproduce embedding artifact")
    summary = _artifact_summary(artifact)
    summary["model_rerun_verified"] = rerun_model
    return summary


def _artifact_summary(artifact: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": artifact["status"],
        "candidate_count": artifact["candidate_count"],
        "question_count": artifact["question_count"],
        "aggregate_metrics": artifact["aggregate_metrics"],
        "partition_metrics": artifact["partition_metrics"],
        "heldout_gate": artifact["heldout_gate"],
        "performance_claim_gate": artifact["performance_claim_gate"],
        "production_promotion_gate": artifact["production_promotion_gate"],
        "embedding_baseline_artifact_sha256": artifact[
            "embedding_baseline_artifact_sha256"
        ],
        "next_step": artifact["next_step"],
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=(
            "readiness",
            "acquire-model",
            "seal-existing-model",
            "run",
            "audit-existing",
            "audit-with-model",
        ),
    )
    parser.add_argument("--vocabulary", type=Path, default=DEFAULT_VOCABULARY)
    parser.add_argument(
        "--generator-spec",
        type=Path,
        default=DEFAULT_GENERATOR_SPEC,
    )
    parser.add_argument("--labels", type=Path, default=DEFAULT_LABELS)
    parser.add_argument(
        "--lexical-artifact",
        type=Path,
        default=DEFAULT_LEXICAL_ARTIFACT,
    )
    parser.add_argument("--decision", type=Path, default=DEFAULT_DECISION)
    parser.add_argument("--model-dir", type=Path, default=DEFAULT_MODEL_DIR)
    parser.add_argument(
        "--snapshot-manifest",
        type=Path,
        default=DEFAULT_SNAPSHOT_MANIFEST,
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--batch-size", type=int, default=64)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    if args.command == "readiness":
        result = readiness(args)
    elif args.command == "acquire-model":
        result = acquire_model(args)
    elif args.command == "seal-existing-model":
        result = seal_existing_model(args)
    elif args.command == "run":
        result = run(args)
    elif args.command == "audit-existing":
        result = audit_existing(args, rerun_model=False)
    else:
        result = audit_existing(args, rerun_model=True)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
