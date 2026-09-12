"""Recovery boundaries and owned lifecycle failure cases."""
import importlib.util
import json
import os
from pathlib import Path
import sys
import time

import psutil
import pytest

DEPLOYMENT = Path(__file__).resolve().parents[1] / "scripts/deployment"


def load(name):
    spec = importlib.util.spec_from_file_location(name, DEPLOYMENT / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_restore_paths_reject_workspace_root_and_escape(tmp_path):
    confined = load("neo4j_recovery").confined
    for target in (tmp_path, tmp_path / "../outside"):
        with pytest.raises(ValueError):
            confined(tmp_path, target)
    assert confined(tmp_path, tmp_path / "restore") == tmp_path / "restore"


def test_process_lifecycle_blocks_duplicate_start_and_stops_redirector_children(tmp_path):
    runtime = load("runtime_process")
    state = tmp_path / "process.json"
    command = [sys.executable, "-B", "-c", "import time; time.sleep(30)"]
    result = runtime.start(command, cwd=tmp_path, env=dict(os.environ), state_path=state)
    try:
        time.sleep(0.2)
        parent = psutil.Process(result["pid"])
        children = parent.children(recursive=True)
        with pytest.raises(RuntimeError, match="already running"):
            runtime.start(command, cwd=tmp_path, env=dict(os.environ), state_path=state)
        assert runtime.status(state)["running"]
        assert not runtime.stop(state)["running"]
        assert all(not child.is_running() for child in children)
    finally:
        if runtime.status(state)["running"]:
            runtime.stop(state)


def test_reused_pid_is_never_signalled(tmp_path, monkeypatch):
    runtime = load("runtime_process")
    state = tmp_path / "process.json"
    state.write_text(json.dumps({"pid": os.getpid(), "process_identity": "old-process"}))
    monkeypatch.setattr(runtime, "_terminate_owned", lambda _: pytest.fail("reused PID signalled"))
    assert not runtime.stop(state)["running"]


def test_lifecycle_lock_excludes_concurrent_operations(tmp_path):
    runtime = load("runtime_process")
    state = tmp_path / "process.json"
    with runtime.lifecycle_lock(state):
        with pytest.raises(RuntimeError, match="locked"):
            with runtime.lifecycle_lock(state):
                pytest.fail("conflicting owner acquired lock")


def test_e3_generator_preserves_preexisting_review(tmp_path):
    spec = importlib.util.spec_from_file_location("e3_cli", DEPLOYMENT.parent / "research/e3_review_contract.py")
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    decisions, readiness = tmp_path / "decisions.json", tmp_path / "readiness.json"
    reviewed = '{"status":"user_reviewed","evidence":"preserve-me"}\n'
    decisions.write_text(reviewed, encoding="utf-8")
    assert cli.main(["generate", "--decisions", str(decisions), "--readiness", str(readiness)]) == 1
    assert decisions.read_text(encoding="utf-8") == reviewed
    assert not readiness.exists()
