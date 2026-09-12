"""Owned local process lifecycle, including Windows Python redirector children."""
from __future__ import annotations
from contextlib import contextmanager
import json
import os
from pathlib import Path
import subprocess

import psutil


def process_identity(pid: int):
    try:
        process = psutil.Process(pid)
        if process.status() == psutil.STATUS_ZOMBIE:
            return None
        return str(process.create_time())
    except psutil.NoSuchProcess:
        return None


@contextmanager
def lifecycle_lock(state_path):
    state_path.parent.mkdir(parents=True, exist_ok=True)
    lock = state_path.with_suffix(".lock")
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise RuntimeError("Lifecycle operation locked; inspect owner before retrying") from None
    try:
        with os.fdopen(descriptor, "w") as stream:
            stream.write(str(os.getpid()))
        yield
    finally:
        lock.unlink()


def status(state_path: Path):
    if not state_path.exists():
        return {"running": False, "status": "not_started"}
    state = json.loads(state_path.read_text(encoding="utf-8"))
    current = process_identity(state["pid"])
    matching = current is not None and current == state["process_identity"]
    return {**state, "running": matching,
            "status": "running" if matching else "stopped_or_pid_reused"}


def _terminate_owned(process):
    # psutil captures creation time and checks PID reuse before signalling.
    descendants = process.children(recursive=True)
    for child in reversed(descendants):
        try:
            child.terminate()
        except psutil.NoSuchProcess:
            pass
    try:
        process.terminate()
    except psutil.NoSuchProcess:
        pass
    _, alive = psutil.wait_procs([*descendants, process], timeout=10)
    if alive:
        raise RuntimeError("Owned runtime processes did not stop within 10 seconds")


def start(command: list[str], *, cwd: Path, env: dict, state_path: Path):
    with lifecycle_lock(state_path):
        if status(state_path)["running"]:
            raise RuntimeError("This runtime is already running")
        env = {k.upper(): str(v) for k, v in env.items()} if os.name == "nt" else env
        options = {"creationflags": subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == "nt" else {"start_new_session": True}
        child = None
        try:
            with state_path.with_suffix(".stdout.log").open("ab") as out, state_path.with_suffix(".stderr.log").open("ab") as err:
                child = psutil.Popen(command, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                                     stdout=out, stderr=err, **options)
            identity = process_identity(child.pid)
            if identity is None:
                raise RuntimeError("Process exited before ownership could be recorded; inspect private logs")
            state = {"pid": child.pid, "process_identity": identity,
                     "executable": str(Path(command[0]).resolve()), "working_directory": str(cwd.resolve())}
            temporary = state_path.with_suffix(".json.tmp")
            temporary.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
            temporary.replace(state_path)
            return {**state, "running": True, "status": "started_not_ready"}
        except BaseException:
            if child is not None and child.is_running():
                _terminate_owned(child)
            raise


def stop(state_path: Path):
    with lifecycle_lock(state_path):
        current = status(state_path)
        if not current["running"]:
            return current
        process = psutil.Process(current["pid"])
        if str(process.create_time()) != current["process_identity"]:
            raise RuntimeError("Runtime process identity changed")
        _terminate_owned(process)
        return status(state_path)
