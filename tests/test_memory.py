"""Tests for the JSON-backed memory store."""

from __future__ import annotations

from pathlib import Path

from dogfood.memory import Memory


def test_kv_roundtrip(tmp_path: Path):
    m = Memory(tmp_path)
    assert m.recall("missing", default="x") == "x"
    m.remember("foo", 42)
    # New instance to prove persistence
    m2 = Memory(tmp_path)
    assert m2.recall("foo") == 42


def test_log_is_capped(tmp_path: Path):
    m = Memory(tmp_path)
    for i in range(Memory.MAX_LOG + 100):
        m.log("ping", i=i)
    snap = m.snapshot()
    assert len(snap["log"]) == Memory.MAX_LOG


def test_runs_is_capped(tmp_path: Path):
    m = Memory(tmp_path)
    for i in range(Memory.MAX_RUNS + 5):
        m.record_run(f"task-{i}", ok=True, sha_after="abc", steps=1)
    snap = m.snapshot()
    assert len(snap["runs"]) == Memory.MAX_RUNS


def test_atomic_write_does_not_corrupt_on_failure(tmp_path: Path, monkeypatch):
    m = Memory(tmp_path)
    m.remember("a", 1)
    # Force the rename to fail; memory should still load the prior state.
    def boom(*a, **kw):
        raise OSError("disk full")
    monkeypatch.setattr("os.replace", boom)
    try:
        m.remember("a", 2)
    except OSError:
        pass
    # Old value should still be readable
    m2 = Memory(tmp_path)
    assert m2.recall("a") == 1