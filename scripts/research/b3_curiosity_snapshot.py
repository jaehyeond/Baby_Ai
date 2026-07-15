"""Inspect B3 cue normalization and pre-turn predictions without a live turn.

This mirrors the conversation endpoint's pre-handler path but never calls the
LLM and never records an Experience.  It is safe for screening candidate
messages before the paid, graph-mutating B3 pilot.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from neural.baby.conversation_handler import _extract_concepts_from_response
from neural.baby.live_curiosity import build_curiosity_cue_terms
from neural.baby.neo4j_db import BrainDatabase, close_driver, init_driver


async def build_message_snapshot(db: Any, message: str) -> dict[str, Any]:
    """Return the exact endpoint cue candidates and read-only DB snapshot."""

    extracted_terms = _extract_concepts_from_response("", message)
    cue_terms = build_curiosity_cue_terms(
        message,
        extracted_terms=extracted_terms,
    )
    snapshot = await db.prepare_curiosity_prediction(
        message,
        cue_terms=cue_terms,
    )
    return {
        "message": message,
        "extracted_terms": extracted_terms,
        "cue_terms": cue_terms,
        "snapshot": snapshot,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read-only B3 cue normalization and prediction snapshots",
    )
    parser.add_argument(
        "--message",
        action="append",
        required=True,
        help="Candidate conversation message; may be repeated",
    )
    return parser.parse_args()


async def _run(messages: list[str]) -> list[dict[str, Any]]:
    await init_driver()
    try:
        db = BrainDatabase()
        return [await build_message_snapshot(db, message) for message in messages]
    finally:
        await close_driver()


def main() -> None:
    args = _parse_args()
    report = asyncio.run(_run(args.message))
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
