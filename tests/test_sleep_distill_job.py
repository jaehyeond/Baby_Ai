from pathlib import Path

import pytest

from scripts.research import sleep_distill_job as job


class FakeModel:
    def __init__(self, *, fail: bool = False):
        self.fail = fail

    def save_pretrained(self, path: str) -> None:
        target = Path(path)
        target.mkdir(parents=True, exist_ok=True)
        (target / "candidate.txt").write_text("new", encoding="utf-8")
        if self.fail:
            raise RuntimeError("candidate save failed")


def _redirect_adapter_paths(monkeypatch, tmp_path: Path) -> Path:
    checkpoint = tmp_path / "local_core_adapter"
    monkeypatch.setattr(job, "MDIR", tmp_path)
    monkeypatch.setattr(job, "CKPT", checkpoint)
    return checkpoint


def test_promoted_core_replaces_checkpoint_after_candidate_save(
    monkeypatch, tmp_path: Path
) -> None:
    checkpoint = _redirect_adapter_paths(monkeypatch, tmp_path)
    checkpoint.mkdir()
    (checkpoint / "old.txt").write_text("old", encoding="utf-8")

    job.save_promoted_core(FakeModel())

    assert (checkpoint / "candidate.txt").read_text(encoding="utf-8") == "new"
    assert not (checkpoint / "old.txt").exists()
    assert not (tmp_path / ".local_core_adapter_previous").exists()


def test_failed_candidate_save_preserves_existing_checkpoint(
    monkeypatch, tmp_path: Path
) -> None:
    checkpoint = _redirect_adapter_paths(monkeypatch, tmp_path)
    checkpoint.mkdir()
    (checkpoint / "old.txt").write_text("old", encoding="utf-8")

    with pytest.raises(RuntimeError, match="candidate save failed"):
        job.save_promoted_core(FakeModel(fail=True))

    assert (checkpoint / "old.txt").read_text(encoding="utf-8") == "old"
