"""Frozen local embedding relevance baseline for J1-R2.

The module is deliberately free of transformers, torch, Neo4j, and runtime
imports. It validates the user decision, pinned model snapshot, score matrix,
metrics, and self-hashed development artifact. Model acquisition and inference
live in the research CLI.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

from neural.baby.pending_question_semantics import canonical_json_sha256


EMBEDDING_BASELINE_ARTIFACT_VERSION = 1
EMBEDDING_MODEL_DECISION_VERSION = 1
EMBEDDING_SNAPSHOT_MANIFEST_VERSION = 1
BASELINE_ID = "frozen_local_embedding_cosine_v1"
PHASE = "J1-R2-E2"
MODEL_ID = "intfloat/multilingual-e5-small"
MODEL_REVISION = "614241f622f53c4eeff9890bdc4f31cfecc418b3"
EVALUATION_K = 8
DISPLAY_K = 20
QUERY_PREFIX = "query: "
CANDIDATE_PREFIX = "passage: "
MAX_LENGTH = 512
EMBEDDING_DIMENSION = 384
REQUIRED_AUTHORIZED_ACTIONS = (
    "download_pinned_model_snapshot",
    "seal_local_model_snapshot",
    "run_frozen_development_embedding_inference",
    "audit_frozen_development_embedding_artifact",
)
REQUIRED_FORBIDDEN_ACTIONS = (
    "database_write",
    "heldout_evaluation",
    "lockbox_materialization",
    "model_training",
    "performance_claim",
    "production_integration",
)
_SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


_EXPECTED_FILES = (
    {
        "path": "1_Pooling/config.json",
        "size": 200,
        "verification": "git_blob_sha1",
        "digest": "acbd4014202bf4dbc6c03229bcbeef7c4feafb58",
    },
    {
        "path": "config.json",
        "size": 655,
        "verification": "git_blob_sha1",
        "digest": "60a2a84020f1d74cc53ea9e8c4e91cf4af6c2b68",
    },
    {
        "path": "model.safetensors",
        "size": 470641600,
        "verification": "sha256",
        "digest": "1a55775f53449dac10a2bcbc312469fac40b96d53198c407081a831f81c98477",
    },
    {
        "path": "modules.json",
        "size": 387,
        "verification": "git_blob_sha1",
        "digest": "ac2039abdf6ff023b27c919bb9675cfe378cb10f",
    },
    {
        "path": "sentence_bert_config.json",
        "size": 57,
        "verification": "git_blob_sha1",
        "digest": "4eca68d85ecd3034cf4174d8a4033a75344ea62d",
    },
    {
        "path": "sentencepiece.bpe.model",
        "size": 5069051,
        "verification": "sha256",
        "digest": "cfc8146abe2a0488e9e2a0c56de7952f7c11ab059eca145a0a727afce0db2865",
    },
    {
        "path": "special_tokens_map.json",
        "size": 167,
        "verification": "git_blob_sha1",
        "digest": "e0b1d18ecd0ae4ff1d47bd297d910c0cf83e504b",
    },
    {
        "path": "tokenizer.json",
        "size": 17082730,
        "verification": "sha256",
        "digest": "0b44a9d7b51c3c62626640cda0e2c2f70fdacdc25bbbd68038369d14ebdf4c39",
    },
    {
        "path": "tokenizer_config.json",
        "size": 443,
        "verification": "git_blob_sha1",
        "digest": "059214673d9d6d2ee319411e2ffec8c024b816d5",
    },
)


def _require_sha256(value: Any, field: str) -> str:
    normalized = str(value or "")
    if not _SHA256_RE.fullmatch(normalized):
        raise ValueError(f"{field} must be a lowercase SHA-256")
    return normalized


def _validate_created_at(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("created_at must be an ISO timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("created_at must include a timezone")
    return str(value)


def _question_sha256(question: str) -> str:
    return hashlib.sha256(question.encode("utf-8")).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_blob_sha1(path: Path) -> str:
    size = path.stat().st_size
    digest = hashlib.sha1(usedforsecurity=False)
    digest.update(f"blob {size}\0".encode("ascii"))
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def embedding_model_contract() -> dict[str, Any]:
    """Return the immutable proposed model and inference contract."""

    prompt_template = {
        "query_prefix": QUERY_PREFIX,
        "candidate_prefix": CANDIDATE_PREFIX,
        "template": "{prefix}{text}",
    }
    pooling = {
        "method": "attention_mask_mean_pool_last_hidden_state",
        "l2_normalize": True,
        "similarity": "cosine_via_normalized_dot_product",
    }
    contract = {
        "phase": PHASE,
        "baseline_id": BASELINE_ID,
        "model_id": MODEL_ID,
        "immutable_revision": MODEL_REVISION,
        "repository": f"https://huggingface.co/{MODEL_ID}",
        "paper_arxiv_id": "2402.05672",
        "license": "mit",
        "language_requirement": "includes_korean",
        "embedding_dimension": EMBEDDING_DIMENSION,
        "max_length": MAX_LENGTH,
        "prompt_template": prompt_template,
        "prompt_template_sha256": canonical_json_sha256(prompt_template),
        "pooling": pooling,
        "pooling_sha256": canonical_json_sha256(pooling),
        "loading": {
            "library": "transformers",
            "auto_model_class": "AutoModel",
            "auto_tokenizer_class": "AutoTokenizer",
            "local_files_only": True,
            "trust_remote_code": False,
            "use_safetensors": True,
            "device": "cpu",
            "dtype": "float32",
            "model_eval": True,
            "torch_inference_mode": True,
            "trainable_parameter_count": 0,
        },
        "expected_files": [dict(item) for item in _EXPECTED_FILES],
        "expected_total_bytes": sum(int(item["size"]) for item in _EXPECTED_FILES),
        "external_api_allowed_for_embedding": False,
        "supervised_label_fit": False,
    }
    contract["embedding_model_contract_sha256"] = canonical_json_sha256(contract)
    return contract


def validate_embedding_model_decision(
    decision: Mapping[str, Any],
) -> dict[str, Any]:
    """Require explicit user authorization for the exact Stage-2 scope."""

    normalized = dict(decision)
    if normalized.get("embedding_model_decision_version") != (
        EMBEDDING_MODEL_DECISION_VERSION
    ):
        raise ValueError("unexpected embedding model decision version")
    supplied = _require_sha256(
        normalized.get("embedding_model_decision_sha256"),
        "embedding_model_decision_sha256",
    )
    unhashed = dict(normalized)
    unhashed.pop("embedding_model_decision_sha256", None)
    if supplied != canonical_json_sha256(unhashed):
        raise ValueError("embedding_model_decision_sha256 mismatch")

    contract = embedding_model_contract()
    required = {
        "phase": PHASE,
        "reviewer_role": "user",
        "decision": "approved",
        "model_id": MODEL_ID,
        "immutable_revision": MODEL_REVISION,
        "embedding_model_contract_sha256": contract[
            "embedding_model_contract_sha256"
        ],
    }
    for field, expected in required.items():
        if normalized.get(field) != expected:
            raise ValueError(f"embedding decision field mismatch: {field}")
    _validate_created_at(str(normalized.get("reviewed_at") or ""))
    if tuple(sorted(normalized.get("authorized_actions") or [])) != tuple(
        sorted(REQUIRED_AUTHORIZED_ACTIONS)
    ):
        raise ValueError("embedding decision authorized_actions mismatch")
    if tuple(sorted(normalized.get("forbidden_actions") or [])) != tuple(
        sorted(REQUIRED_FORBIDDEN_ACTIONS)
    ):
        raise ValueError("embedding decision forbidden_actions mismatch")
    if normalized.get("lockbox_materialization_authorized") is not False:
        raise ValueError("embedding decision must not authorize lockbox materialization")
    if normalized.get("training_authorized") is not False:
        raise ValueError("embedding decision must not authorize training")
    if normalized.get("database_write_authorized") is not False:
        raise ValueError("embedding decision must not authorize database writes")
    return normalized


def _validate_model_configuration(model_dir: Path) -> dict[str, Any]:
    config = json.loads((model_dir / "config.json").read_text(encoding="utf-8"))
    pooling = json.loads(
        (model_dir / "1_Pooling" / "config.json").read_text(encoding="utf-8")
    )
    tokenizer = json.loads(
        (model_dir / "tokenizer_config.json").read_text(encoding="utf-8")
    )
    expected_config = {
        "architectures": ["BertModel"],
        "hidden_size": EMBEDDING_DIMENSION,
        "max_position_embeddings": MAX_LENGTH,
        "model_type": "bert",
        "tokenizer_class": "XLMRobertaTokenizer",
    }
    for field, expected in expected_config.items():
        if config.get(field) != expected:
            raise ValueError(f"model config mismatch: {field}")
    if pooling.get("word_embedding_dimension") != EMBEDDING_DIMENSION:
        raise ValueError("pooling dimension mismatch")
    if pooling.get("pooling_mode_mean_tokens") is not True:
        raise ValueError("mean pooling is not enabled")
    for disabled in (
        "pooling_mode_cls_token",
        "pooling_mode_max_tokens",
        "pooling_mode_mean_sqrt_len_tokens",
    ):
        if pooling.get(disabled) is not False:
            raise ValueError(f"unexpected pooling mode enabled: {disabled}")
    if tokenizer.get("model_max_length") != MAX_LENGTH:
        raise ValueError("tokenizer max length mismatch")
    if tokenizer.get("tokenizer_class") != "XLMRobertaTokenizer":
        raise ValueError("tokenizer class mismatch")
    return {
        "model_config_sha256": canonical_json_sha256(config),
        "pooling_config_sha256": canonical_json_sha256(pooling),
        "tokenizer_config_sha256": canonical_json_sha256(tokenizer),
    }


def inspect_local_model_snapshot(
    model_dir: Path,
    decision: Mapping[str, Any],
    *,
    created_at: str,
    acquisition_method: str,
) -> dict[str, Any]:
    """Hash and validate every required local file against the pinned revision."""

    approved = validate_embedding_model_decision(decision)
    root = model_dir.resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"local model directory is missing: {root}")
    contract = embedding_model_contract()
    file_records = []
    for expected in contract["expected_files"]:
        relative = Path(str(expected["path"]))
        path = root / relative
        if not path.is_file():
            raise FileNotFoundError(f"required model file is missing: {relative}")
        size = path.stat().st_size
        if size != int(expected["size"]):
            raise ValueError(f"model file size mismatch: {relative}")
        method = str(expected["verification"])
        observed = _file_sha256(path) if method == "sha256" else _git_blob_sha1(path)
        if observed != expected["digest"]:
            raise ValueError(f"model file digest mismatch: {relative}")
        file_records.append(
            {
                "path": relative.as_posix(),
                "size": size,
                "expected_verification": method,
                "expected_digest": str(expected["digest"]),
                "actual_sha256": _file_sha256(path),
            }
        )

    configuration = _validate_model_configuration(root)
    manifest = {
        "embedding_snapshot_manifest_version": EMBEDDING_SNAPSHOT_MANIFEST_VERSION,
        "phase": PHASE,
        "status": "pinned_local_embedding_snapshot_verified",
        "created_at": _validate_created_at(created_at),
        "model_id": MODEL_ID,
        "immutable_revision": MODEL_REVISION,
        "embedding_model_contract_sha256": contract[
            "embedding_model_contract_sha256"
        ],
        "embedding_model_decision_sha256": approved[
            "embedding_model_decision_sha256"
        ],
        "acquisition_method": str(acquisition_method),
        "local_path_recorded": False,
        "files": file_records,
        "total_verified_bytes": sum(item["size"] for item in file_records),
        "configuration": configuration,
        "database_writes": False,
        "learning_enabled": False,
        "model_weights_changed": False,
        "lockbox_materialized": False,
        "heldout_gate": False,
        "performance_claim_gate": False,
        "production_promotion_gate": False,
    }
    manifest["embedding_snapshot_manifest_sha256"] = canonical_json_sha256(
        manifest
    )
    return manifest


def validate_embedding_snapshot_manifest(
    manifest: Mapping[str, Any],
    decision: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate a self-hashed snapshot manifest without reading model files."""

    normalized = dict(manifest)
    approved = validate_embedding_model_decision(decision)
    if normalized.get("embedding_snapshot_manifest_version") != (
        EMBEDDING_SNAPSHOT_MANIFEST_VERSION
    ):
        raise ValueError("unexpected embedding snapshot manifest version")
    supplied = _require_sha256(
        normalized.get("embedding_snapshot_manifest_sha256"),
        "embedding_snapshot_manifest_sha256",
    )
    unhashed = dict(normalized)
    unhashed.pop("embedding_snapshot_manifest_sha256", None)
    if supplied != canonical_json_sha256(unhashed):
        raise ValueError("embedding_snapshot_manifest_sha256 mismatch")
    contract = embedding_model_contract()
    if normalized.get("phase") != PHASE:
        raise ValueError("snapshot phase mismatch")
    if normalized.get("status") != "pinned_local_embedding_snapshot_verified":
        raise ValueError("snapshot status mismatch")
    _validate_created_at(str(normalized.get("created_at") or ""))
    if normalized.get("model_id") != MODEL_ID:
        raise ValueError("snapshot model ID mismatch")
    if normalized.get("immutable_revision") != MODEL_REVISION:
        raise ValueError("snapshot revision mismatch")
    if normalized.get("embedding_model_contract_sha256") != contract[
        "embedding_model_contract_sha256"
    ]:
        raise ValueError("snapshot model contract mismatch")
    if normalized.get("embedding_model_decision_sha256") != approved[
        "embedding_model_decision_sha256"
    ]:
        raise ValueError("snapshot user decision mismatch")
    if normalized.get("acquisition_method") not in {
        "huggingface_snapshot_download_pinned_revision",
        "preexisting_local_snapshot_verified_after_user_approval",
    }:
        raise ValueError("snapshot acquisition method mismatch")
    if normalized.get("local_path_recorded") is not False:
        raise ValueError("snapshot must not record a machine-local path")
    expected_by_path = {
        item["path"]: item for item in contract["expected_files"]
    }
    records = list(normalized.get("files") or [])
    if {item.get("path") for item in records} != set(expected_by_path):
        raise ValueError("snapshot file set mismatch")
    for record in records:
        expected = expected_by_path[str(record["path"])]
        if record.get("size") != expected["size"]:
            raise ValueError("snapshot file size record mismatch")
        if record.get("expected_verification") != expected["verification"]:
            raise ValueError("snapshot verification method mismatch")
        if record.get("expected_digest") != expected["digest"]:
            raise ValueError("snapshot expected digest mismatch")
        actual_sha256 = _require_sha256(
            record.get("actual_sha256"),
            f"snapshot.files.{record['path']}.actual_sha256",
        )
        if (
            expected["verification"] == "sha256"
            and actual_sha256 != expected["digest"]
        ):
            raise ValueError("snapshot LFS content SHA-256 mismatch")
    if normalized.get("total_verified_bytes") != contract["expected_total_bytes"]:
        raise ValueError("snapshot total byte count mismatch")
    configuration = dict(normalized.get("configuration") or {})
    if set(configuration) != {
        "model_config_sha256",
        "pooling_config_sha256",
        "tokenizer_config_sha256",
    }:
        raise ValueError("snapshot configuration hash set mismatch")
    for field, digest in configuration.items():
        _require_sha256(digest, f"snapshot.configuration.{field}")
    for field in (
        "database_writes",
        "learning_enabled",
        "model_weights_changed",
        "lockbox_materialized",
        "heldout_gate",
        "performance_claim_gate",
        "production_promotion_gate",
    ):
        if normalized.get(field) is not False:
            raise ValueError(f"snapshot forbidden gate is open: {field}")
    return normalized


def verify_snapshot_manifest_against_directory(
    manifest: Mapping[str, Any],
    decision: Mapping[str, Any],
    model_dir: Path,
) -> dict[str, Any]:
    """Re-hash local files and require exact agreement with the sealed manifest."""

    normalized = validate_embedding_snapshot_manifest(manifest, decision)
    expected = inspect_local_model_snapshot(
        model_dir,
        decision,
        created_at=str(normalized["created_at"]),
        acquisition_method=str(normalized["acquisition_method"]),
    )
    if normalized != expected:
        raise ValueError("local model snapshot does not match sealed manifest")
    return normalized


def _validate_unit_vectors(vectors: Sequence[Sequence[float]], field: str) -> int:
    if not vectors:
        raise ValueError(f"{field} vectors are empty")
    dimension = len(vectors[0])
    if dimension == 0:
        raise ValueError(f"{field} vector dimension is zero")
    for vector in vectors:
        if len(vector) != dimension:
            raise ValueError(f"{field} vector dimensions differ")
        if any(not math.isfinite(float(value)) for value in vector):
            raise ValueError(f"{field} vector contains non-finite values")
        norm = math.sqrt(sum(float(value) ** 2 for value in vector))
        if not math.isclose(norm, 1.0, rel_tol=0.0, abs_tol=1e-5):
            raise ValueError(f"{field} vectors must be L2 normalized")
    return dimension


def score_embedding_questions(
    concepts: Iterable[Mapping[str, Any]],
    questions: Iterable[Mapping[str, Any]],
    encode_texts: Callable[[Sequence[str]], Sequence[Sequence[float]]],
) -> dict[str, list[dict[str, Any]]]:
    """Encode label-free text and return a full cosine ranking per question."""

    concept_records = sorted(
        (
            {
                "concept_id": str(item.get("concept_id") or ""),
                "concept_name": str(item.get("concept_name") or ""),
            }
            for item in concepts
        ),
        key=lambda item: item["concept_id"],
    )
    concept_ids = [item["concept_id"] for item in concept_records]
    if not concept_records or any(not item for item in concept_ids):
        raise ValueError("concepts require non-empty IDs")
    if len(concept_ids) != len(set(concept_ids)):
        raise ValueError("concept IDs must be unique")
    if any(not item["concept_name"].strip() for item in concept_records):
        raise ValueError("concept names must be non-empty")

    question_records = sorted(
        (
            {
                "question_id": str(item.get("question_id") or ""),
                "order": int(item.get("order")),
                "question": str(item.get("question") or ""),
            }
            for item in questions
        ),
        key=lambda item: item["order"],
    )
    if not question_records or any(
        not item["question_id"] or not item["question"].strip()
        for item in question_records
    ):
        raise ValueError("questions require IDs and text")

    candidate_inputs = [
        f"{CANDIDATE_PREFIX}{item['concept_name']}" for item in concept_records
    ]
    query_inputs = [
        f"{QUERY_PREFIX}{item['question']}" for item in question_records
    ]
    candidate_vectors = [
        [float(value) for value in vector]
        for vector in encode_texts(candidate_inputs)
    ]
    query_vectors = [
        [float(value) for value in vector] for vector in encode_texts(query_inputs)
    ]
    candidate_dimension = _validate_unit_vectors(
        candidate_vectors, "candidate"
    )
    query_dimension = _validate_unit_vectors(query_vectors, "query")
    if candidate_dimension != query_dimension:
        raise ValueError("query and candidate dimensions differ")
    if len(candidate_vectors) != len(concept_records):
        raise ValueError("candidate encoder output count mismatch")
    if len(query_vectors) != len(question_records):
        raise ValueError("query encoder output count mismatch")

    results: dict[str, list[dict[str, Any]]] = {}
    for question, query in zip(question_records, query_vectors, strict=True):
        rows = []
        for concept, candidate in zip(
            concept_records, candidate_vectors, strict=True
        ):
            raw_score = sum(
                query[index] * candidate[index]
                for index in range(candidate_dimension)
            )
            score = round(max(-1.0, min(1.0, raw_score)), 12)
            rows.append(
                {
                    "concept_id": concept["concept_id"],
                    "concept_name": concept["concept_name"],
                    "score": score,
                }
            )
        rows.sort(key=lambda item: (-item["score"], item["concept_id"]))
        results[question["question_id"]] = rows
    return results


def _ranking_metrics(
    ranking: list[Mapping[str, Any]],
    positive_ids: set[str],
    *,
    k: int = EVALUATION_K,
) -> dict[str, float]:
    if not positive_ids:
        raise ValueError("at least one reviewed positive is required")
    rank_by_id = {
        str(item["concept_id"]): rank
        for rank, item in enumerate(ranking, start=1)
    }
    if not positive_ids.issubset(rank_by_id):
        raise ValueError("reviewed positive is outside candidate vocabulary")
    positive_ranks = sorted(rank_by_id[item] for item in positive_ids)
    recall = sum(rank <= k for rank in positive_ranks) / len(positive_ranks)
    dcg = sum(
        1.0 / math.log2(rank + 1.0)
        for rank in positive_ranks
        if rank <= k
    )
    ideal_dcg = sum(
        1.0 / math.log2(rank + 1.0)
        for rank in range(1, min(k, len(positive_ranks)) + 1)
    )
    return {
        f"recall_at_{k}": round(recall, 12),
        f"ndcg_at_{k}": round(dcg / ideal_dcg if ideal_dcg else 0.0, 12),
        "mrr": round(1.0 / positive_ranks[0], 12),
    }


def _average_precision_reviewed_pool(
    score_by_id: Mapping[str, float],
    labels: Iterable[Mapping[str, Any]],
) -> float:
    reviewed = sorted(
        (
            {
                "concept_id": str(item.get("concept_id") or ""),
                "label": int(item.get("label")),
                "score": score_by_id[str(item.get("concept_id") or "")],
            }
            for item in labels
        ),
        key=lambda item: (-item["score"], item["concept_id"]),
    )
    positive_count = sum(item["label"] == 1 for item in reviewed)
    if positive_count == 0:
        raise ValueError("reviewed pool requires a positive label")
    hits = 0
    precision_sum = 0.0
    for rank, item in enumerate(reviewed, start=1):
        if item["label"] == 1:
            hits += 1
            precision_sum += hits / rank
    return round(precision_sum / positive_count, 12)


def _mean(values: Iterable[float]) -> float:
    materialized = list(values)
    return round(sum(materialized) / len(materialized), 12) if materialized else 0.0


def _validate_runtime(runtime: Mapping[str, Any]) -> dict[str, Any]:
    normalized = dict(runtime)
    required = {
        "device": "cpu",
        "dtype": "float32",
        "deterministic_algorithms": True,
        "embedding_dimension": EMBEDDING_DIMENSION,
        "trainable_parameter_count": 0,
    }
    for field, expected in required.items():
        if normalized.get(field) != expected:
            raise ValueError(f"embedding runtime mismatch: {field}")
    for field in (
        "python_version",
        "torch_version",
        "transformers_version",
    ):
        if not str(normalized.get(field) or ""):
            raise ValueError(f"embedding runtime field is missing: {field}")
    for field in (
        "batch_size",
        "encoded_batch_count",
        "max_non_padding_tokens",
        "model_parameter_count",
    ):
        try:
            value = int(normalized.get(field))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"embedding runtime field is invalid: {field}") from exc
        if value < 1:
            raise ValueError(f"embedding runtime field must be positive: {field}")
    if int(normalized["max_non_padding_tokens"]) > MAX_LENGTH:
        raise ValueError("embedding runtime exceeded max token length")
    return normalized


def build_embedding_baseline_artifact(
    vocabulary: Mapping[str, Any],
    generator_spec: Mapping[str, Any],
    label_pack: Mapping[str, Any],
    lexical_artifact: Mapping[str, Any],
    decision: Mapping[str, Any],
    snapshot_manifest: Mapping[str, Any],
    score_rows_by_question: Mapping[str, Sequence[Mapping[str, Any]]],
    *,
    bindings: Mapping[str, Any],
    runtime: Mapping[str, Any],
    created_at: str,
) -> dict[str, Any]:
    """Build the complete development-only frozen embedding artifact."""

    approved = validate_embedding_model_decision(decision)
    snapshot = validate_embedding_snapshot_manifest(snapshot_manifest, approved)
    lexical_hash = _require_sha256(
        lexical_artifact.get("lexical_baseline_artifact_sha256"),
        "lexical_baseline_artifact_sha256",
    )
    if lexical_artifact.get("baseline_id") != "lexical_char_ngram_tfidf_v1":
        raise ValueError("unexpected predecessor baseline")
    if lexical_artifact.get("question_count") != len(
        generator_spec.get("questions") or []
    ):
        raise ValueError("lexical predecessor question count mismatch")
    if lexical_artifact.get("candidate_count") != len(
        vocabulary.get("eligible_concepts") or []
    ):
        raise ValueError("lexical predecessor candidate count mismatch")
    if bindings.get("lexical_baseline_artifact_sha256") != lexical_hash:
        raise ValueError("embedding binding does not match lexical artifact")
    if bindings.get("embedding_model_decision_sha256") != approved[
        "embedding_model_decision_sha256"
    ]:
        raise ValueError("embedding binding does not match user decision")
    if bindings.get("embedding_snapshot_manifest_sha256") != snapshot[
        "embedding_snapshot_manifest_sha256"
    ]:
        raise ValueError("embedding binding does not match model snapshot")
    if bindings.get("embedding_model_contract_sha256") != (
        embedding_model_contract()["embedding_model_contract_sha256"]
    ):
        raise ValueError("embedding binding does not match model contract")
    for field, value in bindings.items():
        if field == "input_file_sha256s":
            for path, digest in dict(value).items():
                _require_sha256(digest, f"input_file_sha256s.{path}")
        else:
            _require_sha256(value, f"bindings.{field}")

    concepts = sorted(
        (
            {
                "concept_id": str(item.get("concept_id") or ""),
                "concept_name": str(item.get("concept_name") or ""),
            }
            for item in vocabulary.get("eligible_concepts") or []
        ),
        key=lambda item: item["concept_id"],
    )
    concept_name_by_id = {
        item["concept_id"]: item["concept_name"] for item in concepts
    }
    concept_ids = set(concept_name_by_id)
    labels_by_question = {
        str(item.get("question_id") or ""): item
        for item in label_pack.get("entries") or []
    }
    questions = sorted(
        generator_spec.get("questions") or [],
        key=lambda item: int(item["order"]),
    )
    if set(score_rows_by_question) != {
        str(item["question_id"]) for item in questions
    }:
        raise ValueError("embedding score question set mismatch")

    question_results = []
    for question_item in questions:
        question_id = str(question_item.get("question_id") or "")
        question = str(question_item.get("question") or "")
        question_hash = _question_sha256(question)
        if question_hash != question_item.get("question_sha256"):
            raise ValueError(f"question hash mismatch: {question_id}")
        label_entry = labels_by_question.get(question_id)
        if not label_entry or label_entry.get("question_sha256") != question_hash:
            raise ValueError(f"reviewed labels do not bind question: {question_id}")

        ranking = []
        seen = set()
        for raw in score_rows_by_question[question_id]:
            concept_id = str(raw.get("concept_id") or "")
            if concept_id in seen:
                raise ValueError("duplicate concept in embedding score rows")
            seen.add(concept_id)
            score = float(raw.get("score"))
            if not math.isfinite(score) or score < -1.0 or score > 1.0:
                raise ValueError("embedding cosine score is invalid")
            ranking.append(
                {
                    "concept_id": concept_id,
                    "concept_name": concept_name_by_id.get(concept_id, ""),
                    "score": round(score, 12),
                }
            )
        if seen != concept_ids:
            raise ValueError("embedding scores do not cover full candidate vocabulary")
        ranking.sort(key=lambda item: (-item["score"], item["concept_id"]))

        labels = list(label_entry.get("labels") or [])
        if any(int(item.get("label")) not in (0, 1) for item in labels):
            raise ValueError("reviewed labels must be binary")
        reviewed_ids = {str(item.get("concept_id") or "") for item in labels}
        if not reviewed_ids.issubset(concept_ids):
            raise ValueError("reviewed label is outside candidate vocabulary")
        positive_labels = [item for item in labels if int(item["label"]) == 1]
        positive_ids = {str(item["concept_id"]) for item in positive_labels}
        rank_by_id = {
            item["concept_id"]: rank for rank, item in enumerate(ranking, start=1)
        }
        score_by_id = {item["concept_id"]: item["score"] for item in ranking}
        metrics = _ranking_metrics(ranking, positive_ids)
        metrics["reviewed_pool_average_precision"] = (
            _average_precision_reviewed_pool(score_by_id, labels)
        )
        target_partitions = sorted(
            {str(item.get("partition") or "") for item in positive_labels}
        )
        partition = target_partitions[0] if len(target_partitions) == 1 else "mixed"
        full_score_rows = [
            {"concept_id": item["concept_id"], "score": item["score"]}
            for item in ranking
        ]
        question_results.append(
            {
                "question_id": question_id,
                "question_sha256": question_hash,
                "target_partition": partition,
                "positive_concept_ids": sorted(positive_ids),
                "positive_ranks": {
                    concept_id: rank_by_id[concept_id]
                    for concept_id in sorted(positive_ids)
                },
                "positive_scores": {
                    concept_id: score_by_id[concept_id]
                    for concept_id in sorted(positive_ids)
                },
                "reviewed_pool": [
                    {
                        "concept_id": str(item["concept_id"]),
                        "label": int(item["label"]),
                        "score": score_by_id[str(item["concept_id"])],
                        "full_vocabulary_rank": rank_by_id[str(item["concept_id"])],
                    }
                    for item in labels
                ],
                "metrics": metrics,
                "full_ranking_sha256": canonical_json_sha256(full_score_rows),
                "full_ranked_scores": full_score_rows,
                "top_ranked_concepts": ranking[:DISPLAY_K],
            }
        )

    metric_names = (
        f"recall_at_{EVALUATION_K}",
        f"ndcg_at_{EVALUATION_K}",
        "mrr",
        "reviewed_pool_average_precision",
    )
    aggregate = {
        f"macro_{name}": _mean(
            float(item["metrics"][name]) for item in question_results
        )
        for name in metric_names
    }
    partition_groups: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for item in question_results:
        partition_groups[str(item["target_partition"])].append(item)
    partition_metrics = {
        partition: {
            "question_count": len(items),
            **{
                f"macro_{name}": _mean(
                    float(item["metrics"][name]) for item in items
                )
                for name in metric_names
            },
        }
        for partition, items in sorted(partition_groups.items())
    }

    artifact = {
        "embedding_baseline_artifact_version": EMBEDDING_BASELINE_ARTIFACT_VERSION,
        "phase": PHASE,
        "baseline_id": BASELINE_ID,
        "status": "development_frozen_embedding_baseline_completed_not_for_claim",
        "created_at": _validate_created_at(created_at),
        "configuration": embedding_model_contract(),
        "bindings": dict(bindings),
        "runtime": _validate_runtime(runtime),
        "candidate_count": len(concepts),
        "question_count": len(question_results),
        "aggregate_metrics": aggregate,
        "partition_metrics": partition_metrics,
        "questions": question_results,
        "unjudged_policy": (
            "unjudged_concepts_compete_in_full_ranking_but_are_never_supervised_"
            "as_negatives"
        ),
        "embedding_baseline_execution_gate": True,
        "database_writes": False,
        "learning_enabled": False,
        "gradient_enabled": False,
        "optimizer_steps": 0,
        "model_weights_changed": False,
        "external_embedding_api_used": False,
        "gpu_inference_executed": False,
        "lockbox_materialized": False,
        "heldout_gate": False,
        "performance_claim_gate": False,
        "production_promotion_gate": False,
        "next_step": "review_embedding_result_before_any_learned_head_fit",
    }
    artifact["embedding_baseline_artifact_sha256"] = canonical_json_sha256(
        artifact
    )
    return artifact


def validate_embedding_baseline_artifact(
    artifact: Mapping[str, Any],
    vocabulary: Mapping[str, Any],
    generator_spec: Mapping[str, Any],
    label_pack: Mapping[str, Any],
    lexical_artifact: Mapping[str, Any],
    decision: Mapping[str, Any],
    snapshot_manifest: Mapping[str, Any],
) -> dict[str, Any]:
    """Recompute all derived fields from stored full scores and reject drift."""

    normalized = dict(artifact)
    supplied = _require_sha256(
        normalized.get("embedding_baseline_artifact_sha256"),
        "embedding_baseline_artifact_sha256",
    )
    unhashed = dict(normalized)
    unhashed.pop("embedding_baseline_artifact_sha256", None)
    if supplied != canonical_json_sha256(unhashed):
        raise ValueError("embedding_baseline_artifact_sha256 mismatch")
    score_rows = {
        str(item["question_id"]): list(item.get("full_ranked_scores") or [])
        for item in normalized.get("questions") or []
    }
    expected = build_embedding_baseline_artifact(
        vocabulary,
        generator_spec,
        label_pack,
        lexical_artifact,
        decision,
        snapshot_manifest,
        score_rows,
        bindings=dict(normalized.get("bindings") or {}),
        runtime=dict(normalized.get("runtime") or {}),
        created_at=str(normalized.get("created_at") or ""),
    )
    if normalized != expected:
        raise ValueError("embedding baseline artifact does not match bound inputs")
    return normalized
