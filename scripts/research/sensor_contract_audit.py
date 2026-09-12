"""Audit captured W6 sensor/action/outcome JSON or JSONL without DB writes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from neural.baby.sensor_contract import audit_records  # noqa: E402


def load_records(path: Path) -> list[Any]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".jsonl":
        records: list[Any] = []
        for line_number, line in enumerate(text.splitlines(), start=1):
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as error:
                raise ValueError(f"invalid JSONL at line {line_number}: {error.msg}") from error
        return records
    try:
        document = json.loads(text)
    except json.JSONDecodeError as error:
        raise ValueError(f"invalid JSON: {error.msg}") from error
    if isinstance(document, list):
        return document
    if isinstance(document, dict) and isinstance(document.get("records"), list):
        return document["records"]
    if isinstance(document, dict):
        return [document]
    raise ValueError("JSON input must be a record, a record list, or an object with a records list")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read-only W6 strict sensor/action/outcome capture audit"
    )
    parser.add_argument("capture", type=Path, help="captured .json or .jsonl file")
    parser.add_argument(
        "--require-bibi-agency",
        action="store_true",
        help="return exit 2 unless at least one valid Bibi action/outcome chain exists",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = audit_records(load_records(args.capture))
    except (OSError, ValueError) as error:
        print(json.dumps({"input_error": str(error)}, ensure_ascii=False, sort_keys=True))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    if not result["record_validity_gate"]:
        return 2
    if args.require_bibi_agency and not result["bibi_agency_evidence_gate"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
