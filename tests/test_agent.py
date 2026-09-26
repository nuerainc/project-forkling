"""End-to-end test: the Agent runs a plan against a fresh repo and
correctly rolls back a self-change that breaks tests."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from forkling import tools
from forkling.agent import Agent
from forkling.config import Config
from forkling.llm import LLM
from forkling.memory import Memory
from forkling.planner import Planner


REPO_ROOT = Path(__file__).resolve().parents[1]


def _copy_pkg(dest: Path) -> None:
    import shutil
    shutil.copytree(REPO_ROOT / "forkling", dest / "forkling")


def _git_init(repo: Path) -> None:
    env = {**os.environ,
           "GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "test@local",
           "GIT_COMMITTER_NAME": "test", "GIT_COMMITTER_EMAIL": "test@local",
           "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_SYSTEM": "/dev/null"}
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, env=env)
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, env=env)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo, check=True, env=env)


def test_agent_reads_a_file(tmp_path: Path):
    repo = tmp_path / "r"
    repo.mkdir()
    _copy_pkg(repo)
    (repo / "hi.txt").write_text("hi there\n")
    _git_init(repo)

    cfg = Config(
        repo_root=str(repo), memory_dir=str(tmp_path / "mem"),
        test_command="true",  # never blocks
        ollama_url="http://127.0.0.1:1",  # force fallback
        ollama_model="none", llm_timeout=1,
    )
    llm = LLM(url=cfg.ollama_url, model=cfg.ollama_model, timeout=cfg.llm_timeout)
    agent = Agent(cfg=cfg, llm=llm, memory=Memory(cfg.memory_dir),
                  planner=Planner(llm))

    result = agent.run("read hi.txt")
    # "read hi.txt" matches the rule-based "read" intent; first step is a read.
    first = result.steps[0]
    assert first.action == "read"
    assert "hi there" in first.output


def test_agent_rolls_back_on_failing_test(tmp_path: Path, monkeypatch):
    repo = tmp_path / "r"
    repo.mkdir()
    _copy_pkg(repo)
    _git_init(repo)

    cfg = Config(
        repo_root=str(repo), memory_dir=str(tmp_path / "mem"),
        # Test command always fails, simulating a broken self-edit.
        test_command="false",
        ollama_url="http://127.0.0.1:1",
        ollama_model="none", llm_timeout=1,
    )
    llm = LLM(url=cfg.ollama_url, model=cfg.ollama_model, timeout=cfg.llm_timeout)
    agent = Agent(cfg=cfg, llm=llm, memory=Memory(cfg.memory_dir),
                  planner=Planner(llm))

    initial_sha = tools.git_current_sha(repo)
    # "improve X" yields a 4-step plan with patch+test+commit. Test will fail;
    # the agent should record ok=False and roll back via the test step.
    result = agent.run("improve forkling/agent.py")
    assert result.ok is False
    # The agent checked out the pre-run SHA.
    assert tools.git_current_sha(repo) == initial_sha