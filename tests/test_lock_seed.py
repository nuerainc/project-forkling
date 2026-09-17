"""Tests for the heartbeat lock + inception seeds + detached HEAD detection."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from forkling.diary import Diary
from forkling.locking import HeartbeatLock, LockBusy
from forkling import tools


def test_lock_acquire_and_release(tmp_path):
    lock = HeartbeatLock(tmp_path)
    lock.acquire()
    assert lock.lock_path.exists()
    lock.release()
    assert not lock.lock_path.exists()


def test_lock_blocks_concurrent(tmp_path):
    lock1 = HeartbeatLock(tmp_path)
    lock1.acquire()
    try:
        lock2 = HeartbeatLock(tmp_path)
        with pytest.raises(LockBusy):
            lock2.acquire()
    finally:
        lock1.release()


def test_lock_releases_on_exit(tmp_path):
    lock = HeartbeatLock(tmp_path)
    with lock:
        assert lock.lock_path.exists()
    assert not lock.lock_path.exists()


def test_diary_seeds_roundtrip(tmp_path):
    d = Diary(tmp_path / "diary.jsonl")
    d.write("seed", "consider what cooperation looks like in nature", source="human")
    d.write("seed", "what would Mavis have done?", source="Mavis")
    d.write("run.start", "regular entry")  # not a seed
    seeds = d.seeds()
    assert len(seeds) == 2
    assert seeds[0]["source"] == "human"


def test_git_is_detached_on_normal_branch(tmp_path):
    repo = tmp_path / "r"
    repo.mkdir()
    env = {"PATH": "/usr/bin:/usr/local/bin",
           "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
           "HOME": str(tmp_path)}
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True,
                   capture_output=True, env=env)
    (repo / "f").write_text("x")
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True,
                   capture_output=True, env=env)
    subprocess.run(["git", "commit", "-m", "x"], cwd=repo, check=True,
                   capture_output=True, env=env)
    # On a branch (main), not detached.
    assert tools.git_is_detached(repo) is False


def test_git_clean_true_when_no_changes(tmp_path):
    repo = tmp_path / "r"
    repo.mkdir()
    env = {"PATH": "/usr/bin:/usr/local/bin",
           "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
           "HOME": str(tmp_path)}
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True,
                   capture_output=True, env=env)
    (repo / "f").write_text("x")
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True,
                   capture_output=True, env=env)
    subprocess.run(["git", "commit", "-m", "x"], cwd=repo, check=True,
                   capture_output=True, env=env)
    clean, _ = tools.git_clean(repo)
    assert clean is True


def test_git_clean_false_with_uncommitted(tmp_path):
    repo = tmp_path / "r"
    repo.mkdir()
    env = {"PATH": "/usr/bin:/usr/local/bin",
           "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
           "HOME": str(tmp_path)}
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True,
                   capture_output=True, env=env)
    (repo / "f").write_text("x")
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True,
                   capture_output=True, env=env)
    subprocess.run(["git", "commit", "-m", "x"], cwd=repo, check=True,
                   capture_output=True, env=env)
    (repo / "f").write_text("y")  # dirty change
    clean, porcelain = tools.git_clean(repo)
    assert clean is False
    assert "f" in porcelain