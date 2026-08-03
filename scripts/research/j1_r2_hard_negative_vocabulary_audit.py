"""Generate or audit the J1-R2-E3 pending human-review diagnostic."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from neural.baby.candidate_universe import (  # noqa: E402
    validate_candidate_vocabulary,
)
from neural.baby.pending_question_semantics import (  # noqa: E402
    canonical_json_sha256,
)
from neural.baby.relevance_embedding_baseline import (  # noqa: E402
    validate_embedding_baseline_artifact,
)
from neural.baby.relevance_hard_negative_vocabulary_audit import (  # noqa: E402
    EVALUATION_K,
    POSITIVE_NEIGHBOR_RADIUS,
    TOP_UNJUDGED_PER_QUESTION,
    build_hard_negative_vocabulary_outputs,
    validate_hard_negative_review_packet,
    validate_hard_negative_vocabulary_audit,
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
DEFAULT_EMBEDDING_DECISION = (
    PROJECT_ROOT
    / "scripts"
    / "research"
    / "inputs"
    / "j1_r2_embedding_model_review_decision_20260728.json"
)
DEFAULT_SNAPSHOT_MANIFEST = (
    PROJECT_ROOT
    / "scripts"
    / "research"
    / "manifests"
    / "j1_r2_multilingual_e5_small_snapshot_20260728.json"
)
DEFAULT_EMBEDDING_ARTIFACT = (
    PROJECT_ROOT
    / "claudedocs"
    / "research"
    / "j1_r2_embedding_baseline_development_20260728.json"
)
DEFAULT_REVIEW_PACKET = (
    PROJECT_ROOT
    / "scripts"
    / "research"
    / "inputs"
    / "j1_r2_embedding_hard_negative_review_packet_20260728.json"
)
DEFAULT_AUDIT_ARTIFACT = (
    PROJECT_ROOT
    / "claudedocs"
    / "research"
    / "j1_r2_embedding_hard_negative_vocabulary_audit_20260728.json"
)
AUDIT_MODULE = (
    PROJECT_ROOT
    / "neural"
    / "baby"
    / "relevance_hard_negative_vocabulary_audit.py"
)
AUDIT_CLI = Path(__file__).resolve()


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json_new(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(rendered)
        handle.write("\n")


def _paths(args: argparse.Namespace) -> dict[str, Path]:
    return {
        "candidate_vocabulary": args.vocabulary,
        "development_generator_spec": args.generator_spec,
        "development_labels": args.labels,
        "lexical_baseline_artifact": args.lexical_artifact,
        "embedding_model_decision": args.embedding_decision,
        "embedding_snapshot_manifest": args.snapshot_manifest,
        "embedding_baseline_artifact": args.embedding_artifact,
        "hard_negative_audit_module": AUDIT_MODULE,
        "hard_negative_audit_cli": AUDIT_CLI,
    }


def _bindings(args: argparse.Namespace) -> dict[str, Any]:
    input_file_sha256s = {
        name: _file_sha256(path) for name, path in _paths(args).items()
    }
    implementation_bundle = {
        "hard_negative_audit_module": input_file_sha256s[
            "hard_negative_audit_module"
        ],
        "hard_negative_audit_cli": input_file_sha256s[
            "hard_negative_audit_cli"
        ],
        "selection_contract": {
            "top_unjudged_per_question": TOP_UNJUDGED_PER_QUESTION,
            "positive_neighbor_radius": POSITIVE_NEIGHBOR_RADIUS,
            "positive_neighbor_only_for_positive_outside_top_k": True,
            "top_k": EVALUATION_K,
        },
    }
    vocabulary = _load_json(args.vocabulary)
    generator_spec = _load_json(args.generator_spec)
    labels = _load_json(args.labels)
    embedding = _load_json(args.embedding_artifact)
    return {
        "candidate_vocabulary_sha256": str(
            vocabulary["candidate_vocabulary_sha256"]
        ),
        "generator_spec_sha256": str(generator_spec["generator_spec_sha256"]),
        "development_label_pack_sha256": str(
            labels["development_label_pack_sha256"]
        ),
        "embedding_baseline_artifact_sha256": str(
            embedding["embedding_baseline_artifact_sha256"]
        ),
        "implementation_bundle_sha256": canonical_json_sha256(
            implementation_bundle
        ),
        "input_file_sha256s": input_file_sha256s,
    }


def _validated_inputs(
    args: argparse.Namespace,
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
]:
    vocabulary = validate_candidate_vocabulary(_load_json(args.vocabulary))
    generator_spec = _load_json(args.generator_spec)
    labels = _load_json(args.labels)
    lexical = _load_json(args.lexical_artifact)
    decision = _load_json(args.embedding_decision)
    snapshot = _load_json(args.snapshot_manifest)
    embedding = validate_embedding_baseline_artifact(
        _load_json(args.embedding_artifact),
        vocabulary,
        generator_spec,
        labels,
        lexical,
        decision,
        snapshot,
    )
    return vocabulary, generator_spec, labels, embedding


def _readiness(args: argparse.Namespace) -> dict[str, Any]:
    block_reasons = []
    try:
        _validated_inputs(args)
        bindings = _bindings(args)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        bindings = None
        block_reasons.append(f"sealed_input_validation_failed:{type(exc).__name__}")
    if args.review_packet.exists():
        block_reasons.append("review_packet_already_exists_refuse_overwrite")
    if args.audit_output.exists():
        block_reasons.append("audit_artifact_already_exists_refuse_overwrite")
    return {
        "phase": "J1-R2-E3",
        "status": (
            "ready_for_read_only_diagnostic"
            if not block_reasons
            else "blocked_fail_closed"
        ),
        "block_reasons": block_reasons,
        "bindings_ready_gate": bindings is not None,
        "diagnostic_generation_gate": not block_reasons,
        "automatic_label_assignment_gate": False,
        "training_data_materialization_gate": False,
        "database_write_gate": False,
        "learned_head_fit_gate": False,
        "lockbox_materialization_gate": False,
        "heldout_gate": False,
        "performance_claim_gate": False,
        "production_promotion_gate": False,
    }


def _generate(args: argparse.Namespace) -> dict[str, Any]:
    readiness = _readiness(args)
    if not readiness["diagnostic_generation_gate"]:
        raise ValueError(
            "diagnostic generation blocked: "
            + ", ".join(readiness["block_reasons"])
        )
    vocabulary, generator_spec, labels, embedding = _validated_inputs(args)
    bindings = _bindings(args)
    created_at = datetime.now(timezone.utc).isoformat()
    packet, audit = build_hard_negative_vocabulary_outputs(
        vocabulary,
        generator_spec,
        labels,
        embedding,
        bindings=bindings,
        created_at=created_at,
    )
    _write_json_new(args.review_packet, packet)
    _write_json_new(args.audit_output, audit)
    return _summary(packet, audit)


def _audit_existing(args: argparse.Namespace) -> dict[str, Any]:
    vocabulary, generator_spec, labels, embedding = _validated_inputs(args)
    bindings = _bindings(args)
    packet = validate_hard_negative_review_packet(
        _load_json(args.review_packet),
        vocabulary,
        generator_spec,
        labels,
        embedding,
        expected_bindings=bindings,
    )
    audit = validate_hard_negative_vocabulary_audit(
        _load_json(args.audit_output),
        packet,
        vocabulary,
        generator_spec,
        labels,
        embedding,
        expected_bindings=bindings,
    )
    return _summary(packet, audit)


def _summary(
    packet: Mapping[str, Any],
    audit: Mapping[str, Any],
) -> dict[str, Any]:
    selection = audit["selection_summary"]
    vocabulary = audit["vocabulary_quality"]
    return {
        "status": audit["status"],
        "hard_negative_review_packet_sha256": packet[
            "hard_negative_review_packet_sha256"
        ],
        "hard_negative_vocabulary_audit_sha256": audit[
            "hard_negative_vocabulary_audit_sha256"
        ],
        "question_count": packet["question_count"],
        "review_row_count": packet["review_row_count"],
        "unique_selected_concept_count": selection[
            "unique_selected_concept_count"
        ],
        "flagged_vocabulary_concept_count": vocabulary[
            "flagged_concept_count"
        ],
        "normalized_surface_collision_group_count": vocabulary[
            "normalized_surface_collision_group_count"
        ],
        "boundary_punctuation_variant_group_count": vocabulary[
            "boundary_punctuation_variant_group_count"
        ],
        "review_complete_gate": False,
        "training_data_materialization_gate": False,
        "learned_head_fit_gate": False,
        "next_step": packet["next_step"],
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=("readiness", "generate", "audit-existing"),
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
    parser.add_argument(
        "--embedding-decision",
        type=Path,
        default=DEFAULT_EMBEDDING_DECISION,
    )
    parser.add_argument(
        "--snapshot-manifest",
        type=Path,
        default=DEFAULT_SNAPSHOT_MANIFEST,
    )
    parser.add_argument(
        "--embedding-artifact",
        type=Path,
        default=DEFAULT_EMBEDDING_ARTIFACT,
    )
    parser.add_argument(
        "--review-packet",
        type=Path,
        default=DEFAULT_REVIEW_PACKET,
    )
    parser.add_argument(
        "--audit-output",
        type=Path,
        default=DEFAULT_AUDIT_ARTIFACT,
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "readiness":
        result = _readiness(args)
    elif args.command == "generate":
        result = _generate(args)
    else:
        result = _audit_existing(args)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
