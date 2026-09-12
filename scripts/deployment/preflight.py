"""Read-only infrastructure inventory for Bibi deployment and relocation.

Does not import the API (whose startup creates schema/seeds), write to Neo4j,
start Docker, call a model API, or include credentials in the report.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import logging
import os
from pathlib import Path
import shutil
import socket
from datetime import datetime, timezone
from urllib.parse import urlsplit

from dotenv import dotenv_values
from neo4j import GraphDatabase, Query, READ_ACCESS


ROOT = Path(__file__).resolve().parents[2]
LABELS = (
    "Concept", "Experience", "UserModel", "Person", "BabyState",
    "BrainRegion", "PendingQuestion", "SleepLog", "CuriosityLog",
)


def endpoint_status(raw: str | None, default_port: int) -> dict:
    if not raw:
        return {"configured": False}
    result: dict = {"configured": True}
    try:
        endpoint = urlsplit(raw)
        hostname = endpoint.hostname
        port = endpoint.port or default_port
        if not hostname:
            return {"configured": True, "error_type": "InvalidEndpoint"}
        result = {
            "configured": True, "scheme": endpoint.scheme,
            "hostname": hostname, "port": port,
        }
        socket.getaddrinfo(hostname, port)
        result["dns"] = "ok"
        with socket.create_connection((hostname, port), timeout=4):
            result["tcp"] = "ok"
        return result
    except (OSError, ValueError) as exc:
        # Exception messages can contain URLs and must never be emitted.
        result["error_type"] = type(exc).__name__
        result["error_code"] = getattr(exc, "errno", None)
        return result


def graph_inventory(config: dict) -> dict:
    result: dict = {"read_only": True, "authentication": "not_checked"}
    required = ("NEO4J_URI", "NEO4J_USERNAME", "NEO4J_PASSWORD")
    if any(not config.get(key) for key in required):
        result["error_type"] = "MissingConfiguration"
        return result
    try:
        with GraphDatabase.driver(
            config["NEO4J_URI"],
            auth=(config["NEO4J_USERNAME"], config["NEO4J_PASSWORD"]),
            connection_timeout=5,
            max_transaction_retry_time=0,
        ) as driver:
            driver.verify_connectivity()
            result["authentication"] = "ok"
            with driver.session(
                database=config.get("NEO4J_DATABASE") or None,
                default_access_mode=READ_ACCESS,
            ) as session:
                def query(text: str) -> list[dict]:
                    return [dict(row) for row in session.run(Query(text, timeout=15))]

                result["components"] = query(
                    "CALL dbms.components() YIELD name, versions, edition "
                    "RETURN name, versions, edition"
                )
                result["label_counts"] = {
                    label: query(f"MATCH (n:{label}) RETURN count(n) AS n")[0]["n"]
                    for label in LABELS
                }
                result["total_nodes"] = query("MATCH (n) RETURN count(n) AS n")[0]["n"]
                result["relationships"] = query(
                    "MATCH ()-[r]->() RETURN count(r) AS n"
                )[0]["n"]
                result["experience_metadata"] = query(
                    "MATCH (e:Experience) "
                    "RETURN max(toString(e.created_at)) AS latest_created_at, "
                    "count(e.embedding) AS with_embedding"
                )[0]
                result["indexes"] = query(
                    "SHOW INDEXES YIELD name, type, state RETURN name, type, state"
                )
                result["constraints"] = query(
                    "SHOW CONSTRAINTS YIELD name, type RETURN name, type"
                )
                result["inventory_complete"] = True
    except Exception as exc:
        result["error_type"] = type(exc).__name__
        result["inventory_complete"] = False
    # A running Enterprise server does not identify the actual store format.
    result["store_format"] = "not_verified"
    result["restore_compatibility_verified"] = False
    result["consistent_backup"] = False
    return result


def collect(output: Path) -> dict:
    config = dict(dotenv_values(ROOT / ".env"))
    for key, value in os.environ.items():
        if key.startswith(("NEO4J_", "REDIS_")):
            config[key] = value
    disks = []
    paths = [Path("C:/"), Path("D:/"), Path("E:/")] if os.name == "nt" else [Path("/")]
    for path in paths:
        if path.exists():
            usage = shutil.disk_usage(path)
            disks.append({
                "path": str(path), "free_bytes": usage.free,
                "total_bytes": usage.total,
                "free_gib": round(usage.free / 2**30, 2),
            })
    packages = {}
    for name in ("fastapi", "uvicorn", "neo4j", "redis", "google-genai",
                 "openai", "python-dotenv", "httpx", "pydantic"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    fingerprints = {}
    for relative in (
        "neural/baby/conversation_handler.py", "neural/baby/redis_client.py",
        "neural/baby/api_server.py",
        "frontend/baby-dashboard/src/hooks/useIdleSleep.ts",
    ):
        path = ROOT / relative
        fingerprints[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    adapter = ROOT / "models/local_core_adapter"
    adapter_files = [path for path in adapter.rglob("*") if path.is_file()] if adapter.exists() else []
    return {
        "schema_version": 1,
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "workspace": str(ROOT),
        "report_path": str(output),
        "disks": disks,
        "endpoints": {
            "neo4j": endpoint_status(config.get("NEO4J_URI"), 7687),
            "redis": endpoint_status(config.get("REDIS_URL"), 6379),
            "local_api": endpoint_status("http://127.0.0.1:8000", 8000),
        },
        "neo4j": graph_inventory(config),
        "installed_packages": packages,
        "source_sha256": fingerprints,
        "local_adapter": {
            "present": adapter.exists(), "file_count": len(adapter_files),
            "bytes": sum(path.stat().st_size for path in adapter_files),
            "copied_or_loaded": False,
        },
        "actions": {
            "database_write": False, "api_start": False, "docker_start": False,
            "image_download": False, "model_download": False,
            "model_api_call": False, "paid_resource_creation": False,
        },
        "limits": [
            "Counts are an inventory, not a consistent backup or proof of full data integrity.",
            "TCP reachability is not an application-level health check.",
            "Neo4j store-format and target restore compatibility remain unverified.",
            "Unattended operation and operation while the PC is off are not verified.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.suffix != ".json" or not output.is_relative_to(ROOT):
        parser.error("output must be a JSON file inside the project workspace")
    logging.disable(logging.CRITICAL)
    report = collect(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if not report["neo4j"].get("inventory_complete", False):
        print("PREFLIGHT_INCOMPLETE: database inventory failed; see sanitized report")
        return 1
    print("PREFLIGHT_RECORDED")
    print(f"Neo4j inventory complete: {report['neo4j'].get('inventory_complete', False)}")
    print("Always-on operation verified: False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
