"""Online backup, isolated restore and private-content-free graph comparison.

Use the same Neo4j Enterprise distribution as the source. Never stops the source,
overwrites a database, copies credentials, or enables schema initialization.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(",", ":")).encode()).hexdigest()


def normalized(value):
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        return {"float_hex": value.hex()}
    if isinstance(value, dict):
        return {str(k): normalized(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [normalized(v) for v in value]
    return {"type": type(value).__name__, "value": str(value)}


def graph_fingerprint(uri, username, password, database="neo4j"):
    from neo4j import GraphDatabase, READ_ACCESS, unit_of_work
    with GraphDatabase.driver(uri, auth=(username, password), connection_timeout=5,
                              max_transaction_retry_time=0) as driver:
        with driver.session(database=database, default_access_mode=READ_ACCESS) as session:
            @unit_of_work(timeout=120)
            def read(tx):
                nodes, labels = {}, Counter()
                for row in tx.run("MATCH (n) RETURN elementId(n) AS key, labels(n) AS labels, properties(n) AS properties"):
                    nodes[row["key"]] = digest({"labels": sorted(row["labels"]), "properties": normalized(row["properties"])})
                    labels.update(row["labels"])
                edges, types = [], Counter()
                for row in tx.run("MATCH (a)-[r]->(b) RETURN elementId(a) AS a, elementId(b) AS b, type(r) AS type, properties(r) AS properties"):
                    edges.append(digest({"a": nodes[row["a"]], "b": nodes[row["b"]], "type": row["type"], "properties": normalized(row["properties"])}))
                    types.update([row["type"]])
                indexes = [normalized(dict(r)) for r in tx.run("SHOW INDEXES YIELD name,type,entityType,labelsOrTypes,properties,options RETURN name,type,entityType,labelsOrTypes,properties,options")]
                constraints = [normalized(dict(r)) for r in tx.run("SHOW CONSTRAINTS YIELD name,type,entityType,labelsOrTypes,properties RETURN name,type,entityType,labelsOrTypes,properties")]
                return {"nodes": len(nodes), "relationships": len(edges),
                        "label_counts": dict(sorted(labels.items())),
                        "relationship_counts": dict(sorted(types.items())),
                        "node_properties_sha256": digest(sorted(nodes.values())),
                        "relationship_properties_sha256": digest(sorted(edges)),
                        "indexes_sha256": digest(sorted(indexes, key=lambda r: r["name"])),
                        "constraints_sha256": digest(sorted(constraints, key=lambda r: r["name"])),
                        "method": "sorted property multisets and property-identified endpoints; identical nodes are indistinguishable"}
            return session.execute_read(read)


def confined(root: Path, path: Path) -> Path:
    root, path = root.resolve(), path.resolve()
    if path == root or not path.is_relative_to(root):
        raise ValueError("Target must be strictly inside the recovery workspace")
    return path


def admin_command(java: Path, distribution: Path, *args):
    if not java.is_file() or not (distribution / "lib").is_dir():
        raise ValueError("Existing Java executable and Neo4j lib directory required")
    return [str(java), "-Xmx512m", "--add-opens=java.base/java.nio=ALL-UNNAMED",
            "-cp", str(distribution / "lib" / "*"), "org.neo4j.cli.AdminTool", *args]


def admin_env(home: Path, conf: Path, temp: Path):
    temp.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env.update(NEO4J_HOME=str(home), NEO4J_CONF=str(conf), TEMP=str(temp), TMP=str(temp))
    return env


def write_new(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("backup", "restore"):
        sub = commands.add_parser(name)
        sub.add_argument("--java", type=Path, required=True)
        sub.add_argument("--distribution", type=Path, required=True)
        sub.add_argument("--workspace", type=Path, required=True)
        sub.add_argument("--database", default="neo4j")
        sub.add_argument("--output", type=Path, required=True)
    backup = commands.choices["backup"]
    backup.add_argument("--from-address", default="127.0.0.1:6362")
    restore = commands.choices["restore"]
    restore.add_argument("--backup", type=Path, required=True)
    restore.add_argument("--target", type=Path, required=True)
    restore.add_argument("--server-id", type=Path, help="Original data/server_id, required for a full system restore")
    compare = commands.add_parser("compare")
    compare.add_argument("--env-file", type=Path, required=True)
    compare.add_argument("--restored-uri", required=True)
    compare.add_argument("--database", default="neo4j")
    compare.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists; preserve previous evidence")
    if args.command == "compare":
        from dotenv import dotenv_values
        config = dotenv_values(args.env_file)
        auth = (config["NEO4J_USERNAME"], config["NEO4J_PASSWORD"], args.database)
        before = graph_fingerprint(config["NEO4J_URI"], *auth)
        restored = graph_fingerprint(args.restored_uri, *auth)
        after = graph_fingerprint(config["NEO4J_URI"], *auth)
        result = {"captured_at_utc": datetime.now(timezone.utc).isoformat(),
                  "source_before": before, "restored": restored, "source_after": after,
                  "source_stable": before == after, "restore_matches": before == restored,
                  "read_only": True, "same_version_restore_only": True}
        write_new(args.output, result)
        print(json.dumps({k: result[k] for k in ("source_stable", "restore_matches")}))
        return 0 if before == restored == after else 1
    if not re.fullmatch(r"[a-z][a-z0-9.-]{2,62}", args.database):
        parser.error("Invalid database name")
    root = args.workspace.resolve()
    root.mkdir(parents=True, exist_ok=True)
    conf = confined(root, root / "admin-conf")
    conf.mkdir(exist_ok=True)
    (conf / "neo4j.conf").write_text(
        "server.directories.logs=" + (root / "admin-logs").as_posix() + "\n"
        "server.memory.heap.initial_size=128m\nserver.memory.heap.max_size=512m\n", encoding="utf-8")
    if args.command == "backup":
        backup_dir = confined(root, root / "backups")
        backup_dir.mkdir(exist_ok=True)
        previous = set(backup_dir.glob("*.backup"))
        cmd = admin_command(args.java, args.distribution, "database", "backup",
                            "--from=" + args.from_address, "--to-path=backups", "--type=FULL",
                            "--pagecache=256m", "--include-metadata=" + ("none" if args.database == "system" else "all"), args.database)
        subprocess.run(cmd, cwd=root, env=admin_env(args.distribution, conf, root / "tmp"), check=True)
        paths = sorted(set(backup_dir.glob("*.backup")) - previous)
        if len(paths) != 1:
            raise RuntimeError("Expected exactly one new backup")
        result = {"database": args.database, "backup": str(paths[0]),
                  "sha256": hashlib.sha256(paths[0].read_bytes()).hexdigest(),
                  "bytes": paths[0].stat().st_size, "consistent_online_backup": True}
        if args.database == "system":
            identity = args.distribution / "data/server_id"
            if not identity.is_file():
                raise ValueError("System backup requires the original data/server_id")
            identity_backup = paths[0].with_suffix(".server_id")
            with identity_backup.open("xb") as stream:
                stream.write(identity.read_bytes())
            result["server_id_file"] = str(identity_backup)
            result["server_id_sha256"] = hashlib.sha256(identity_backup.read_bytes()).hexdigest()
    else:
        target = confined(root, args.target)
        if (target / "data" / "databases" / args.database).exists():
            raise ValueError("Destination database exists; refusing overwrite")
        if target == args.distribution.resolve() or args.distribution.resolve().is_relative_to(target):
            raise ValueError("Destination overlaps source distribution")
        if not args.backup.is_file():
            raise ValueError("Backup file missing")
        if args.database == "system":
            if args.server_id is None or not args.server_id.is_file():
                raise ValueError("Full system restore requires --server-id from the same source")
            destination_id = target / "data/server_id"
            if destination_id.exists() and destination_id.read_bytes() != args.server_id.read_bytes():
                raise ValueError("Target already has a different server identity; use a fresh target")
        target.mkdir(parents=True, exist_ok=True)
        restore_conf = target / "conf"
        restore_conf.mkdir(exist_ok=True)
        # Do not replace a configured target instance.
        config_path = restore_conf / "neo4j.conf"
        if not config_path.exists():
            config_path.write_text(
                "server.directories.data=data\nserver.directories.logs=logs\n"
                "server.memory.heap.initial_size=128m\nserver.memory.heap.max_size=512m\nserver.memory.pagecache.size=256m\n"
                "server.default_listen_address=127.0.0.1\nserver.default_advertised_address=127.0.0.1\n"
                "server.bolt.listen_address=127.0.0.1:17687\nserver.bolt.advertised_address=127.0.0.1:17687\n"
                "server.http.listen_address=127.0.0.1:17474\nserver.http.advertised_address=127.0.0.1:17474\n"
                "server.cluster.listen_address=127.0.0.1:16000\nserver.cluster.advertised_address=127.0.0.1:16000\n"
                "server.cluster.raft.listen_address=127.0.0.1:17000\nserver.cluster.raft.advertised_address=127.0.0.1:17000\n"
                "server.routing.listen_address=127.0.0.1:17688\nserver.routing.advertised_address=127.0.0.1:17688\n"
                "server.https.enabled=false\nserver.backup.enabled=false\nserver.metrics.enabled=false\n", encoding="utf-8")
        for line in config_path.read_text(encoding="utf-8").splitlines():
            key, _, value = line.partition("=")
            if key.strip() in {"server.directories.data", "server.directories.transaction.logs.root", "server.directories.logs"}:
                confined(target, target / value.strip())
        if args.database == "system":
            destination_id.parent.mkdir(parents=True, exist_ok=True)
            if not destination_id.exists():
                shutil.copyfile(args.server_id, destination_id)
        # Relative paths avoid Windows drive letters being interpreted as URI schemes.
        relative_backup = os.path.relpath(args.backup.resolve(), root)
        cmd = admin_command(args.java, args.distribution, "database", "restore",
                            "--from-path=" + relative_backup, args.database)
        subprocess.run(cmd, cwd=root, env=admin_env(target, restore_conf, root / "tmp"), check=True)
        result = {"database": args.database, "target": str(target), "restored": True,
                  "source_stopped": False, "overwrite": False, "requires_start_and_comparison": True}
    result["captured_at_utc"] = datetime.now(timezone.utc).isoformat()
    write_new(args.output, result)
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
