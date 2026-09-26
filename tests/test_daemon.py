"""Tests for the daemon module.

The daemon is a persistent process; these tests use ``max_ticks`` and
``--skip-improve`` to exercise short-lived loops without needing real
heartbeat work. The HeartbeatLock inside run_tick uses a file-based
lock, so we just need a tempdir repo for each test.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

import pytest

from forkling import daemon as _daemon
from forkling.config import Config


def _make_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".forkling").mkdir()
    return repo


def _make_cfg(tmp_path: Path) -> Config:
    cfg = Config.from_env()
    cfg.memory_dir = str(tmp_path / "mem")
    return cfg


def test_is_running_false_initially(tmp_path):
    repo = _make_repo(tmp_path)
    assert _daemon.is_running(repo) is False


def test_daemon_writes_and_removes_pidfile(tmp_path):
    repo = _make_repo(tmp_path)
    cfg = _make_cfg(tmp_path)
    d = _daemon.Daemon(cfg, repo, every_seconds=1, max_ticks=1,
                       skip_improve=True)
    assert not d.pid_path.exists()
    d._write_pidfile()
    assert d.pid_path.exists()
    assert int(d.pid_path.read_text(encoding="utf-8")) > 0
    assert _daemon.is_running(repo)
    d._remove_pidfile()
    assert not d.pid_path.exists()
    assert not _daemon.is_running(repo)


def test_daemon_writes_status_file(tmp_path):
    repo = _make_repo(tmp_path)
    cfg = _make_cfg(tmp_path)
    d = _daemon.Daemon(cfg, repo, every_seconds=1, max_ticks=1,
                       skip_improve=True)
    d._write_status()
    assert d.status_path.exists()
    payload = json.loads(d.status_path.read_text(encoding="utf-8"))
    assert payload["pid"] > 0
    assert payload["tick_count"] == 0
    assert payload["repo"] == str(repo)


def test_daemon_run_tick_invokes_heartbeat_subprocess(tmp_path, monkeypatch):
    """run_tick should call `python -m forkling heartbeat` via subprocess."""
    repo = _make_repo(tmp_path)
    cfg = _make_cfg(tmp_path)
    captured: dict = {}

    real_run = subprocess.run

    def fake_run(argv, **kwargs):
        captured["argv"] = argv
        captured["cwd"] = kwargs.get("cwd")
        # Return a fake successful result without actually invoking
        # python -m forkling heartbeat.
        class _R:
            returncode = 0
            stdout = ""
            stderr = ""
        return _R()

    monkeypatch.setattr(_daemon.subprocess, "run", fake_run)
    d = _daemon.Daemon(cfg, repo, every_seconds=1, max_ticks=1,
                       skip_improve=True)
    ok = d.run_tick()
    assert ok is True
    assert captured["argv"][:3] == [sys.executable, "-m", "forkling"]
    assert captured["argv"][3] == "heartbeat"
    assert "--skip-improve" in captured["argv"]
    assert captured["cwd"] == str(repo)
    assert d._tick_count == 1
    assert d._last_tick_ok is True


def test_daemon_run_tick_handles_failure(tmp_path, monkeypatch):
    repo = _make_repo(tmp_path)
    cfg = _make_cfg(tmp_path)

    def fake_run(argv, **kwargs):
        class _R:
            returncode = 1
            stdout = ""
            stderr = "boom"
        return _R()

    monkeypatch.setattr(_daemon.subprocess, "run", fake_run)
    d = _daemon.Daemon(cfg, repo, every_seconds=1, max_ticks=1,
                       skip_improve=True)
    ok = d.run_tick()
    assert ok is False
    assert d._last_tick_ok is False


def test_daemon_run_forever_exits_after_max_ticks(tmp_path, monkeypatch):
    """With max_ticks=2 and a fake heartbeat, the daemon should run
    2 ticks and then exit cleanly."""
    repo = _make_repo(tmp_path)
    cfg = _make_cfg(tmp_path)

    def fake_run(argv, **kwargs):
        class _R:
            returncode = 0
            stdout = ""
            stderr = ""
        return _R()

    monkeypatch.setattr(_daemon.subprocess, "run", fake_run)
    d = _daemon.Daemon(cfg, repo, every_seconds=1, max_ticks=2,
                       skip_improve=True)
    # Override the sleep to be very short so the test is fast.
    monkeypatch.setattr(d, "_interruptible_sleep",
                        lambda seconds: True)
    rc = d.run_forever()
    assert rc == 0
    assert d._tick_count == 2
    assert not d.pid_path.exists()


def test_daemon_stop_flag_halts_run_forever(tmp_path, monkeypatch):
    repo = _make_repo(tmp_path)
    cfg = _make_cfg(tmp_path)

    def fake_run(argv, **kwargs):
        class _R:
            returncode = 0
            stdout = ""
            stderr = ""
        return _R()

    monkeypatch.setattr(_daemon.subprocess, "run", fake_run)
    d = _daemon.Daemon(cfg, repo, every_seconds=1, max_ticks=10,
                       skip_improve=True)

    # Replace _interruptible_sleep so the daemon runs ticks quickly and
    # checks the stop flag on each iteration.
    real_sleep = d._interruptible_sleep
    sleep_calls = {"n": 0}

    def fake_sleep(seconds):
        sleep_calls["n"] += 1
        if d._should_stop():
            return False
        return True

    monkeypatch.setattr(d, "_interruptible_sleep", fake_sleep)

    # Write the stop flag *before* run_forever starts; should be
    # detected on the first tick's sleep call.
    d.stop_path.touch()

    rc = d.run_forever()
    assert rc == 0
    # The stop flag should have been cleared in the finally block.
    assert not d.stop_path.exists()


def test_daemon_request_stop_sets_flag(tmp_path):
    repo = _make_repo(tmp_path)
    cfg = _make_cfg(tmp_path)
    d = _daemon.Daemon(cfg, repo, every_seconds=1, max_ticks=10,
                       skip_improve=True)
    d.request_stop()
    assert d.stop_path.exists()
    assert d._stop_event.is_set()


def test_daemon_cli_start_then_stop(tmp_path, monkeypatch):
    """End-to-end test: start the daemon in a subprocess with --max-ticks 1
    so it exits on its own, then verify is_running flips True then False."""
    repo = _make_repo(tmp_path)
    cfg = _make_cfg(tmp_path)

    # Use the real subprocess.run inside the daemon (it's the
    # heartbeat subprocess we want to stub). We can avoid hitting the
    # real heartbeat by using a heartbeat that doesn't exist in this
    # tmp repo — the daemon's _invoke_heartbeat will fail with a
    # non-zero exit, which we treat as a soft warning (default mode).
    # max_ticks=2 with a 2s interval keeps the daemon alive long enough to
    # observe the pidfile even when the heartbeat subprocess fails fast
    # (e.g. forkling not pip-installed, so `python -m forkling` in the tmp
    # repo exits immediately), then it exits on its own.
    import os
    env = os.environ.copy()
    env["FORKLING_MEMORY"] = str(tmp_path / "mem")
    env["FORKLING_REPO"] = str(repo)

    # Spawn the daemon as a subprocess. It will run heartbeat (which
    # may fail since the tmp repo isn't a real Forkland repo, but the
    # daemon's run_tick treats non-zero as a soft warning unless
    # --restart-on-failure is set, so the daemon keeps running).
    proc = subprocess.Popen(
        [sys.executable, "-m", "forkling", "daemon", "start",
         "--repo", str(repo), "--every", "2", "--max-ticks", "2"],
        env=env,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    # Give it a moment to write the pidfile.
    deadline = time.time() + 5.0
    while time.time() < deadline and not (repo / ".forkling" / "daemon.pid").exists():
        time.sleep(0.1)
    assert (repo / ".forkling" / "daemon.pid").exists(), (
        "daemon should have written its pidfile within 5 seconds")

    rc = proc.wait(timeout=30)
    assert rc == 0
    # After exit, the pidfile should be cleaned up.
    assert not (repo / ".forkling" / "daemon.pid").exists()


def test_daemon_cli_status_when_not_running(tmp_path, monkeypatch, capsys):
    repo = _make_repo(tmp_path)
    cfg = _make_cfg(tmp_path)
    from forkling.__main__ import main
    monkeypatch.setenv("FORKLING_MEMORY", str(tmp_path / "mem"))
    rc = main(["daemon", "status", "--repo", str(repo)])
    assert rc == 1
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert payload["running"] is False


def test_daemon_log_emits_diary_entry(tmp_path, monkeypatch):
    repo = _make_repo(tmp_path)
    mem = tmp_path / "mem"
    mem.mkdir()
    monkeypatch.setenv("FORKLING_MEMORY", str(mem))
    cfg = Config.from_env()
    d = _daemon.Daemon(cfg, repo, every_seconds=1, max_ticks=1,
                       skip_improve=True)
    d._log("daemon.test", "hello from the test")
    lines = (mem / "diary.jsonl").read_text(encoding="utf-8").splitlines()
    assert any("daemon.test" in line for line in lines)
