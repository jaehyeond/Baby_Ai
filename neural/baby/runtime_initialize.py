"""Explicit installed-runtime schema/seed entry point; ordinary startup never calls it."""
from __future__ import annotations
import argparse
import asyncio
import json

from .neo4j_db import init_driver, close_driver, get_brain_db
from .runtime_readiness import run_explicit_initialization


async def initialize(schema: bool, seed: bool):
    try:
        await init_driver()
        return await run_explicit_initialization(get_brain_db(), include_schema=schema, include_seed=seed)
    finally:
        await close_driver()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--schema", action="store_true")
    parser.add_argument("--seed", action="store_true")
    args = parser.parse_args()
    if not args.schema and not args.seed:
        parser.error("Choose --schema and/or --seed explicitly")
    result = asyncio.run(initialize(args.schema, args.seed))
    print(json.dumps(result, indent=2))
    return 1 if result["status"] == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
