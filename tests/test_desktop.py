"""Tests for the desktop companion module.

The GUI itself cannot be exercised in a headless test environment, so we
test the snapshot function (``collect_status``) and the format helpers.
These are the bits the user actually sees on screen; if they break the
UI shows wrong numbers.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from forkling.config import Config
from forkling.desktop import (
    GREEN_MAX, YELLOW_MAX, _format_age, _status_color, collect_status,
)


def test_status_color_thresholds():
    assert _status_color(None) == ("NEVER", "#666666")
    label, _ = _status_color(5.0)
    assert label == "GREEN"
    label, _ = _status_color(GREEN_MAX - 1)
    assert label == "GREEN"
    label, _ = _status_color(GREEN_MAX + 1)
    assert label == "YELLOW"
    label, _ = _status_color(YELLOW_MAX - 1)
    assert label == "YELLOW"
    label, _ = _status_color(YELLOW_MAX + 1)
    assert label == "RED"
    label, _ = _status_color(10**9)
    assert label == "RED"


def test_format_age():
    assert _format_age(None) == "never"
    assert _format_age(5) == "5s ago"
    assert _format_age(120) == "2m ago"
    assert _format_age(3700) == "1.0h ago"
    assert _format_age(2 * 86400) == "2.0d ago"


def test_collect_status_with_no_data(tmp_path, monkeypatch):
    """A fresh fork with no state at all should still produce a status."""
    monkeypatch.setenv("FORKLING_MEMORY", str(tmp_path / "mem"))
    cfg = Config.from_env()
    status = collect_status(cfg, repo=tmp_path)
    # No heartbeat log -> status NEVER.
    assert status["status_label"] == "NEVER"
    assert status["ledger_count"] == 0
    assert status["diary_count"] == 0
    assert status["graveyard_count"] == 0
    assert status["family_count"] == 0
    assert status["diary_recent"] == []
    assert status["trace_recent"] == []
    # Clock is wall-time based; the specific stage changes as the
    # calendar progresses past day 7. We just assert it reports some
    # non-empty, well-formed stage label.
    assert isinstance(status["clock"]["stage"], str)
    assert status["clock"]["stage"].startswith("stage-")


def test_collect_status_with_real_data(tmp_path, monkeypatch):
    """When state exists, the snapshot should reflect it accurately."""
    mem = tmp_path / "mem"
    mem.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("FORKLING_MEMORY", str(mem))

    # Seed a diary.
    (mem / "diary.jsonl").write_text(
        json.dumps({"ts": time.time() - 60,
                    "kind": "self-improve.committed",
                    "content": "improved llm.py"})
        + "\n"
        + json.dumps({"ts": time.time() - 30,
                      "kind": "milestone",
                      "milestone": True,
                      "content": "first paper draft"})
        + "\n",
        encoding="utf-8",
    )

    # Seed a trace.
    (mem / "trace.jsonl").write_text(
        json.dumps({
            "ts": time.time() - 10, "kind": "plan",
            "model": "qwen3:4b", "used_llm": True,
            "latency_ms": 1234, "task": "list forkling",
            "prompt": "x", "response": "y", "system": "",
            "commit_sha": "", "meta": {}, "prev_hash": "0"*64,
            "hash": "a"*64,
        }) + "\n",
        encoding="utf-8",
    )

    # Seed a heartbeat log (very recent).
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".forkling").mkdir()
    (repo / ".forkling" / "heartbeat.log").write_text(
        json.dumps({"ran_at": time.time() - 5, "steps": []}) + "\n",
        encoding="utf-8",
    )

    cfg = Config.from_env()
    status = collect_status(cfg, repo=repo)

    # Recent heartbeat -> GREEN.
    assert status["status_label"] == "GREEN"
    # Diary should have the 2 entries (most recent first).
    assert len(status["diary_recent"]) == 2
    assert status["diary_recent"][0]["kind"] == "milestone"
    assert status["diary_recent"][1]["kind"] == "self-improve.committed"
    # Trace should have 1 entry.
    assert len(status["trace_recent"]) == 1
    assert status["trace_recent"][0]["kind"] == "plan"
    assert status["trace_recent"][0]["used_llm"] is True
    assert status["trace_stats"]["total"] == 1


def test_collect_status_red_for_old_heartbeat(tmp_path, monkeypatch):
    """A heartbeat older than YELLOW_MAX should be RED."""
    mem = tmp_path / "mem"
    mem.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("FORKLING_MEMORY", str(mem))

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".forkling").mkdir()
    # Heartbeat 5 hours ago.
    (repo / ".forkling" / "heartbeat.log").write_text(
        json.dumps({"ran_at": time.time() - 5 * 3600, "steps": []}) + "\n",
        encoding="utf-8",
    )
    cfg = Config.from_env()
    status = collect_status(cfg, repo=repo)
    assert status["status_label"] == "RED"


def test_desktop_cli_runs_in_sovereign_mode(tmp_path, monkeypatch):
    """If Tk is unavailable, the CLI should exit 0 with a friendly message,
    not crash. We simulate that by patching tkinter.Tk to raise TclError."""
    import sys
    monkeypatch.setenv("FORKLING_MEMORY", str(tmp_path / "mem"))

    # Import inside the test so the module loads first.
    import tkinter as tk

    class _BoomTcl(tk.TclError):
        pass

    real_tk = tk.Tk

    def _raise(*a, **kw):
        raise _BoomTcl("no display")

    monkeypatch.setattr(tk, "Tk", _raise)
    # Also patch the import inside forkling.desktop.
    import forkling.desktop as d
    monkeypatch.setattr(d.tk, "Tk", _raise)

    from forkling.__main__ import main
    rc = main(["desktop", "--repo", str(tmp_path)])
    # 0 = graceful "no display" exit. Anything else is a crash.
    assert rc == 0