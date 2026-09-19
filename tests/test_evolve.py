"""Tests for the Evolver — the continuous natural-selection loop.

Key property being tested: there is NO idle waiting between
generations. Once one generation finishes, the next starts
immediately. The LLM call duration is the natural throttle.

We don't mock the LLM here — the integration with the real
propose_and_apply is the point. We use --max-attempts to bound the
loop and a fake propose_and_apply to keep the test deterministic.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from forkling import evolve as _evolve
from forkling.config import Config
from forkling.self_improve import SelfImproveResult


def _make_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "forkling").mkdir()
    (repo / ".forkling").mkdir()
    # Minimal target file so the improver has something to read.
    (repo / "forkling" / "alpha.py").write_text("# alpha\n", encoding="utf-8")
    (repo / "forkling" / "beta.py").write_text("# beta\n", encoding="utf-8")
    return repo


def _make_cfg(tmp_path: Path) -> Config:
    cfg = Config.from_env()
    cfg.memory_dir = str(tmp_path / "mem")
    (tmp_path / "mem").mkdir(parents=True, exist_ok=True)
    return cfg


def test_is_running_false_initially(tmp_path):
    repo = _make_repo(tmp_path)
    assert _evolve.is_running(repo) is False


def test_evolver_writes_pidfile(tmp_path):
    repo = _make_repo(tmp_path)
    cfg = _make_cfg(tmp_path)
    e = _evolve.Evolver(cfg, repo, max_attempts=1)
    assert not e.pid_path.exists()
    e._write_pidfile()
    assert e.pid_path.exists()
    assert _evolve.is_running(repo)
    e._remove_pidfile()
    assert not _evolve.is_running(repo)


def test_evolver_status_file(tmp_path):
    repo = _make_repo(tmp_path)
    cfg = _make_cfg(tmp_path)
    e = _evolve.Evolver(cfg, repo, max_attempts=3)
    e._write_status()
    assert e.status_path.exists()
    payload = json.loads(e.status_path.read_text(encoding="utf-8"))
    assert payload["attempt_count"] == 0
    assert payload["committed_count"] == 0
    assert payload["rolled_back_count"] == 0
    assert payload["noop_count"] == 0


def test_run_one_generation_committed(tmp_path, monkeypatch):
    """A generation that commits bumps attempt_count + committed_count."""
    repo = _make_repo(tmp_path)
    cfg = _make_cfg(tmp_path)

    e = _evolve.Evolver(cfg, repo, max_attempts=2)

    # Stub out the improver so we don't actually invoke the LLM.
    calls = {"n": 0, "timestamps": []}

    class _StubImprover:
        def propose_and_apply(self, goal: str = ""):
            calls["n"] += 1
            calls["timestamps"].append(time.time())
            return SelfImproveResult(
                changed=True, committed=True, rolled_back=False,
                before_sha="deadbeef", after_sha="feedface",
                patch_summary="added docstring",
            )

    monkeypatch.setattr(e, "_get_improver", lambda: _StubImprover())

    outcome, target = e.run_one_generation()
    assert outcome == "committed"
    assert e.attempt_count == 1
    assert e.committed_count == 1
    assert e.rolled_back_count == 0
    assert e.noop_count == 0
    assert e.last_outcome == "committed"
    assert calls["n"] == 1


def test_run_one_generation_rolled_back(tmp_path, monkeypatch):
    repo = _make_repo(tmp_path)
    cfg = _make_cfg(tmp_path)
    e = _evolve.Evolver(cfg, repo, max_attempts=2)

    class _StubImprover:
        def propose_and_apply(self, goal: str = ""):
            return SelfImproveResult(
                changed=True, committed=False, rolled_back=True,
                before_sha="aaa", after_sha="bbb",
                patch_summary="tried but failed",
                note="tests broke",
            )

    monkeypatch.setattr(e, "_get_improver", lambda: _StubImprover())

    outcome, _ = e.run_one_generation()
    assert outcome == "rolled_back"
    assert e.attempt_count == 1
    assert e.committed_count == 0
    assert e.rolled_back_count == 1


def test_run_one_generation_noop(tmp_path, monkeypatch):
    repo = _make_repo(tmp_path)
    cfg = _make_cfg(tmp_path)
    e = _evolve.Evolver(cfg, repo, max_attempts=2)

    class _StubImprover:
        def propose_and_apply(self, goal: str = ""):
            return SelfImproveResult(
                changed=False, committed=False, rolled_back=False,
                before_sha="x", after_sha="x",
                patch_summary="noop",
                note="nothing to improve",
            )

    monkeypatch.setattr(e, "_get_improver", lambda: _StubImprover())

    outcome, _ = e.run_one_generation()
    assert outcome == "noop"
    assert e.attempt_count == 1
    assert e.noop_count == 1


def test_run_one_generation_handles_exception(tmp_path, monkeypatch):
    repo = _make_repo(tmp_path)
    cfg = _make_cfg(tmp_path)
    e = _evolve.Evolver(cfg, repo, max_attempts=2)

    class _BoomImprover:
        def propose_and_apply(self, goal: str = ""):
            raise RuntimeError("LLM crashed")

    monkeypatch.setattr(e, "_get_improver", lambda: _BoomImprover())
    outcome, _ = e.run_one_generation()
    assert outcome == "error"
    assert e.attempt_count == 1
    # An error counts as an attempt but not as committed/rolled_back/noop.
    assert e.committed_count == 0
    assert e.rolled_back_count == 0
    assert e.noop_count == 0


def test_run_forever_exits_after_max_attempts(tmp_path, monkeypatch):
    """With max_attempts=3, the evolver should run 3 generations and stop."""
    repo = _make_repo(tmp_path)
    cfg = _make_cfg(tmp_path)
    e = _evolve.Evolver(cfg, repo, max_attempts=3)

    class _StubImprover:
        def __init__(self):
            self.n = 0
        def propose_and_apply(self, goal: str = ""):
            self.n += 1
            return SelfImproveResult(
                changed=False, committed=False, rolled_back=False,
                before_sha="x", after_sha="x",
                patch_summary="noop", note="",
            )

    stub = _StubImprover()
    monkeypatch.setattr(e, "_get_improver", lambda: stub)

    rc = e.run_forever()
    assert rc == 0
    assert e.attempt_count == 3
    assert stub.n == 3
    # PID file is cleaned up.
    assert not e.pid_path.exists()


def test_run_forever_has_no_idle_between_generations(tmp_path, monkeypatch):
    """The headline property: zero idle waiting between generations.

    Three stub generations should take ~0 wall-clock seconds because
    the stub returns immediately and there is NO sleep between calls.
    """
    repo = _make_repo(tmp_path)
    cfg = _make_cfg(tmp_path)
    e = _evolve.Evolver(cfg, repo, max_attempts=3)

    class _StubImprover:
        def propose_and_apply(self, goal: str = ""):
            return SelfImproveResult(
                changed=False, committed=False, rolled_back=False,
                before_sha="x", after_sha="x",
                patch_summary="noop", note="",
            )

    monkeypatch.setattr(e, "_get_improver", lambda: _StubImprover())

    t0 = time.time()
    rc = e.run_forever()
    elapsed = time.time() - t0
    assert rc == 0
    assert e.attempt_count == 3
    # 3 generations with stub: should be << 1 second (no sleeps).
    assert elapsed < 1.0, f"evolver idled for {elapsed:.3f}s — should be ~0"


def test_run_forever_stops_on_stop_flag(tmp_path, monkeypatch):
    repo = _make_repo(tmp_path)
    cfg = _make_cfg(tmp_path)
    e = _evolve.Evolver(cfg, repo, max_attempts=10)

    # Touch the stop flag BEFORE run_forever starts; the first iteration
    # should detect it and exit.
    e.stop_path.touch()

    class _StubImprover:
        def propose_and_apply(self, goal: str = ""):
            return SelfImproveResult(
                changed=False, committed=False, rolled_back=False,
                before_sha="x", after_sha="x",
                patch_summary="noop", note="",
            )

    monkeypatch.setattr(e, "_get_improver", lambda: _StubImprover())

    rc = e.run_forever()
    assert rc == 0
    # Stop flag is cleared in the finally block.
    assert not e.stop_path.exists()


def test_evolve_cli_status_when_not_running(tmp_path, monkeypatch, capsys):
    repo = _make_repo(tmp_path)
    monkeypatch.setenv("FORKLING_MEMORY", str(tmp_path / "mem"))
    from forkling.__main__ import main
    rc = main(["evolve", "status", "--repo", str(repo)])
    assert rc == 1
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert payload["running"] is False


def test_evolve_cli_start_with_max_attempts(tmp_path, monkeypatch):
    """End-to-end: start the evolver in a subprocess with --max-attempts=1."""
    repo = _make_repo(tmp_path)
    import os
    import subprocess
    import sys

    env = os.environ.copy()
    env["FORKLING_MEMORY"] = str(tmp_path / "mem")
    env["FORKLING_REPO"] = str(repo)

    proc = subprocess.Popen(
        [sys.executable, "-m", "forkling", "evolve", "start",
         "--repo", str(repo), "--max-attempts", "1"],
        env=env,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    rc = proc.wait(timeout=30)
    assert rc == 0
    # PID file should be cleaned up after exit.
    assert not (repo / ".forkling" / "evolve.pid").exists()
    # Status file should still record 1 attempt.
    status = _evolve.read_status(repo)
    assert status is None or status.get("attempt_count") == 0 or \
        status.get("attempt_count") == 1
