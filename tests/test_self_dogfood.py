"""The dogfood test: prove the agent can improve itself.

We copy the ``dogfood`` package into a temp git repo, give it a real pytest
suite, run :class:`SelfImprover`, and verify:

* either a real commit + tag was produced, OR a noop was returned cleanly
* the test suite still passes either way
* the agent never silently broke itself
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from dogfood import tools
from dogfood.agent import Agent
from dogfood.config import Config
from dogfood.llm import LLM
from dogfood.memory import Memory
from dogfood.planner import Planner
from dogfood.self_improve import SelfImprover


REPO_ROOT = Path(__file__).resolve().parents[1]


def _copy_package(dest: Path) -> None:
    """Copy the dogfood package + tests into a temp git repo."""
    shutil.copytree(REPO_ROOT / "dogfood", dest / "dogfood")
    # Copy a small subset of tests so the suite is real but fast.
    tests_dest = dest / "tests"
    tests_dest.mkdir(exist_ok=True)
    (tests_dest / "__init__.py").write_text("")
    shutil.copy(REPO_ROOT / "tests" / "test_memory.py", tests_dest / "test_memory.py")
    (tests_dest / "conftest.py").write_text(
        "import sys\nfrom pathlib import Path\nsys.path.insert(0, str(Path(__file__).resolve().parents[1]))\n"
    )


def _init_repo_with_initial_commit(repo: Path) -> str:
    import os
    env = {**os.environ,
           "GIT_AUTHOR_NAME": "dogfood", "GIT_AUTHOR_EMAIL": "dogfood@local",
           "GIT_COMMITTER_NAME": "dogfood", "GIT_COMMITTER_EMAIL": "dogfood@local",
           "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_SYSTEM": "/dev/null"}
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, env=env)
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, env=env)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo, check=True, env=env)
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, env=env, text=True
    ).strip()


def test_self_improver_keeps_suite_green(tmp_path: Path):
    # Use a copy so we never touch the user's real repo.
    repo = tmp_path / "df"
    repo.mkdir()
    _copy_package(repo)
    initial_sha = _init_repo_with_initial_commit(repo)

    cfg = Config(
        repo_root=str(repo),
        memory_dir=str(tmp_path / "mem"),
        test_command="pytest -q tests/test_memory.py",
        # Force the fallback path so this test is deterministic offline.
        ollama_url="http://127.0.0.1:1",
        ollama_model="none",
        llm_timeout=1,
    )
    llm = LLM(url=cfg.ollama_url, model=cfg.ollama_model, timeout=cfg.llm_timeout)
    memory = Memory(cfg.memory_dir)
    agent = Agent(cfg=cfg, llm=llm, memory=memory, planner=Planner(llm))

    si = SelfImprover(agent)
    result = si.propose_and_apply()

    # Either we shipped a change or no change was needed — both are OK.
    assert result.ok, f"self-improve reported failure: {result.to_dict()}"

    # Final state: tests must still pass.
    test = subprocess.run(
        ["pytest", "-q", "tests/test_memory.py"], cwd=repo,
        capture_output=True, text=True, env={**__import__("os").environ,
                                            "PYTHONPATH": str(repo)},
    )
    assert test.returncode == 0, (
        f"tests broken after self-improve\nstdout:\n{test.stdout}\nstderr:\n{test.stderr}"
    )

    # If we did ship a change, verify the SHA moved forward and a tag exists.
    if result.committed:
        assert result.after_sha != initial_sha
        tags = tools._git(repo, "tag", "--list").stdout
        assert "self-" in tags
    else:
        assert result.after_sha == initial_sha