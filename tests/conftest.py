"""Shared pytest fixtures: a fresh git repo in a temp dir for each test."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def tmp_repo(tmp_path: Path) -> Path:
    """Create a fresh git repo with one commit so SHA-based ops work."""
    repo = tmp_path / "repo"
    repo.mkdir()
    # git init + identity so commits don't fail
    env = {**os.environ,
           "GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "test@local",
           "GIT_COMMITTER_NAME": "test", "GIT_COMMITTER_EMAIL": "test@local",
           "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_SYSTEM": "/dev/null"}
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, env=env)
    (repo / "README.md").write_text("# test\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, env=env)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo, check=True, env=env)
    return repo