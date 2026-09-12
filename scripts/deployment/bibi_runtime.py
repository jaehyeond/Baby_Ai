"""Explicit local API lifecycle; secrets are read from a user-selected env file."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
from pathlib import Path
import sys
from urllib.request import urlopen
from urllib.error import HTTPError, URLError

from runtime_process import start, status, stop

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("start", "status", "stop", "initialize"))
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--python", type=Path, default=ROOT / ".runtime/venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python"))
    parser.add_argument("--state", type=Path, default=ROOT / ".runtime/api-process.json")
    parser.add_argument("--port", type=int, default=18000)
    parser.add_argument("--schema", action="store_true")
    parser.add_argument("--seed", action="store_true")
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("Choose a local unprivileged port")
    if args.command in {"start", "initialize"}:
        if args.env_file is None or not args.env_file.is_file():
            parser.error("An existing explicit --env-file is required")
        from dotenv import dotenv_values
        env = dict(os.environ)
        env.update({k: v for k, v in dotenv_values(args.env_file).items() if v is not None})
        env.update(PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8",
                   PYTHONPATH="", LOCAL_CORE_DISTILL="0", BABY_RUNTIME_INIT_SCHEMA_SEED="0",
                   TEMP=str(ROOT / ".runtime/tmp"), TMP=str(ROOT / ".runtime/tmp"))
        (ROOT / ".runtime/tmp").mkdir(parents=True, exist_ok=True)
        if args.command == "start":
            result = start([str(args.python.resolve()), "-B", "-m", "neural.baby.api_server",
                            "--host", "127.0.0.1", "--port", str(args.port)],
                           cwd=ROOT / ".runtime", env=env, state_path=args.state)
        else:
            if not args.schema and not args.seed:
                parser.error("Initialization requires --schema and/or --seed")
            if status(args.state)["running"]:
                parser.error("Stop the owned API before explicit initialization")
            command = [str(args.python.resolve()), "-B", "-m", "neural.baby.runtime_initialize"]
            command += [flag for flag, enabled in (("--schema", args.schema), ("--seed", args.seed)) if enabled]
            initialized = subprocess.run(command, cwd=ROOT / ".runtime", env=env, check=False)
            return initialized.returncode
    elif args.command == "stop":
        result = stop(args.state)
    else:
        result = status(args.state)
        try:
            with urlopen(f"http://127.0.0.1:{args.port}/health", timeout=8) as response:
                result["readiness"] = json.load(response)
        except HTTPError as exc:
            result["readiness_http_status"] = exc.code
            result["readiness"] = json.load(exc)
        except (URLError, TimeoutError):
            result["readiness"] = {"ready": False, "status": "unreachable"}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result.get("status") == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
