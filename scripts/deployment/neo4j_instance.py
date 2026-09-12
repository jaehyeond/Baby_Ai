"""Start/stop an already restored, loopback-only Neo4j development instance."""
from __future__ import annotations
import argparse
import json
import os
import socket
from pathlib import Path

from neo4j_recovery import confined
from runtime_process import start, status, stop

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("start", "stop", "status"))
    parser.add_argument("--home", type=Path, required=True)
    parser.add_argument("--java", type=Path)
    parser.add_argument("--distribution", type=Path)
    args = parser.parse_args()
    home = confined(ROOT / ".runtime", args.home)
    state = home / "process.json"
    if args.command == "start":
        if not args.java or not args.java.is_file() or not args.distribution or not (args.distribution / "lib").is_dir():
            parser.error("Existing --java and --distribution required")
        config = dict(line.split("=", 1) for line in (home / "conf/neo4j.conf").read_text().splitlines() if "=" in line and not line.lstrip().startswith("#"))
        if config.get("server.default_listen_address") != "127.0.0.1":
            parser.error("This restore verifier only starts loopback-bound instances")
        for key, value in config.items():
            if key.endswith("listen_address") and not value.startswith("127.0.0.1"):
                parser.error("All explicit listeners must use loopback")
            if key.endswith("listen_address") and ":" in value:
                host, port = value.rsplit(":", 1)
                with socket.socket() as probe:
                    try:
                        probe.bind((host, int(port)))
                    except OSError:
                        parser.error("A configured restore port is unavailable")
        for key in ("server.directories.data", "server.directories.logs", "server.directories.transaction.logs.root"):
            if key in config:
                confined(home, home / config[key])
        if not (home / "data/databases/neo4j").is_dir():
            parser.error("Restore the database before starting")
        env = dict(os.environ)
        env.update(NEO4J_HOME=str(home), NEO4J_CONF=str(home / "conf"),
                   TEMP=str(ROOT / ".runtime/tmp"), TMP=str(ROOT / ".runtime/tmp"))
        cmd = [str(args.java.resolve()), "-Xms128m", "-Xmx512m", "--add-opens=java.base/java.nio=ALL-UNNAMED",
               "--add-opens=java.base/java.io=ALL-UNNAMED", "-cp", str(args.distribution.resolve() / "lib" / "*"),
               "com.neo4j.server.enterprise.Neo4jEnterprise", "--home-dir=" + str(home), "--config-dir=" + str(home / "conf")]
        result = start(cmd, cwd=ROOT, env=env, state_path=state)
    elif args.command == "stop":
        result = stop(state)
    else:
        result = status(state)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
