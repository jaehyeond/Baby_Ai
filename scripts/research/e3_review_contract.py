"""Generate or validate the J1-R2-E3 user-review decision contract."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from neural.baby.e3_review_contract import (  # noqa: E402
    build_e3_review_readiness,
    build_pending_review_template,
    file_bytes_sha256,
    validate_e3_review_decisions,
    validate_e3_review_readiness,
)


DEFAULT_PACKET = (
    PROJECT_ROOT
    / "scripts"
    / "research"
    / "inputs"
    / "j1_r2_embedding_hard_negative_review_packet_20260728.json"
)
DEFAULT_AUDIT = (
    PROJECT_ROOT
    / "claudedocs"
    / "research"
    / "j1_r2_embedding_hard_negative_vocabulary_audit_20260728.json"
)
DEFAULT_PROPOSAL = (
    PROJECT_ROOT
    / "claudedocs"
    / "research"
    / "J1_R2_E3_PRIMARY_REVIEW_AGENT_RECOMMENDATIONS_2026-07-28.md"
)
DEFAULT_DECISIONS = (
    PROJECT_ROOT
    / "claudedocs"
    / "research"
    / "j1_r2_e3_pending_review_decisions_20260912.json"
)
DEFAULT_READINESS = (
    PROJECT_ROOT
    / "claudedocs"
    / "research"
    / "j1_r2_e3_review_readiness_20260912.json"
)


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON object required: {path}")
    return payload


def _load_sources(
    args: argparse.Namespace,
) -> tuple[dict[str, Any], dict[str, Any], str, str]:
    packet = _load_json(args.packet)
    audit = _load_json(args.audit)
    proposal_raw = args.proposal.read_bytes()
    proposal_text = proposal_raw.decode("utf-8")
    return packet, audit, proposal_text, file_bytes_sha256(proposal_raw)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(
        payload, ensure_ascii=False, indent=2, sort_keys=True
    ) + "\n"
    if path.exists() and path.read_text(encoding="utf-8") == serialized:
        return
    if path.exists():
        raise ValueError("Output differs from existing evidence; select a new output path")
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(serialized)


def _generate(args: argparse.Namespace) -> int:
    packet, audit, proposal_text, proposal_sha256 = _load_sources(args)
    decisions = build_pending_review_template(
        packet, audit, proposal_text, proposal_sha256
    )
    readiness = build_e3_review_readiness(
        packet, audit, proposal_text, proposal_sha256, decisions
    )
    # Check both paths before writing either: never erase a user's reviewed labels.
    if args.decisions.resolve() == args.readiness.resolve():
        raise ValueError("Decision and readiness paths must be distinct")
    for path, payload in ((args.decisions, decisions), (args.readiness, readiness)):
        serialized = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        if path.exists() and path.read_text(encoding="utf-8") != serialized:
            raise ValueError("Output differs from existing evidence; select a new output path")
    _write_json(args.decisions, decisions)
    _write_json(args.readiness, readiness)
    print(
        "E3 pending review artifacts generated: "
        f"primary=60 diagnostic_only=24 pending=60 fit_eligible=0"
    )
    return 0


def _validate(args: argparse.Namespace) -> int:
    packet, audit, proposal_text, proposal_sha256 = _load_sources(args)
    decisions = validate_e3_review_decisions(
        packet,
        audit,
        proposal_text,
        proposal_sha256,
        _load_json(args.decisions),
        require_user_review=args.require_user_review,
    )
    readiness = validate_e3_review_readiness(
        packet,
        audit,
        proposal_text,
        proposal_sha256,
        decisions,
        _load_json(args.readiness),
    )
    if args.expect_incomplete:
        if decisions["status"] != "awaiting_user_review":
            raise ValueError("expected the E3 review to remain incomplete")
        if readiness["fit_row_contract_eligible_gate"] is not False:
            raise ValueError("incomplete review cannot be fit eligible")
        print("E3 review incomplete and fit ineligible")
    else:
        print(
            "E3 review contract valid: "
            f"status={decisions['status']} "
            "fit_row_contract_eligible="
            f"{str(readiness['fit_row_contract_eligible_gate']).lower()}"
        )
    return 0


def _add_common_paths(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--packet", type=Path, default=DEFAULT_PACKET)
    parser.add_argument("--audit", type=Path, default=DEFAULT_AUDIT)
    parser.add_argument("--proposal", type=Path, default=DEFAULT_PROPOSAL)
    parser.add_argument("--decisions", type=Path, default=DEFAULT_DECISIONS)
    parser.add_argument("--readiness", type=Path, default=DEFAULT_READINESS)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate = subparsers.add_parser(
        "generate", help="write the still-unreviewed decision template and readiness"
    )
    _add_common_paths(generate)
    generate.set_defaults(handler=_generate)

    validate = subparsers.add_parser(
        "validate", help="validate exact source binding, review state, and readiness"
    )
    _add_common_paths(validate)
    mode = validate.add_mutually_exclusive_group()
    mode.add_argument("--expect-incomplete", action="store_true")
    mode.add_argument("--require-user-review", action="store_true")
    validate.set_defaults(handler=_validate)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        return int(args.handler(args))
    except (OSError, UnicodeError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"E3 review contract error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
