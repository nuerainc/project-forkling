"""Tests for the kind=new_file path of SelfImprover.

True agency: the agent can write brand-new modules that give it new
skills. Selection (pytest) gates every addition — the file lands in
the repo only if all tests still pass.

These tests cover the validator, the rollback path, the success path,
and the integration with the evolve loop.
"""

from __future__ import annotations

import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest

from forkling.agent import Agent
from forkling.capability import CapabilityLedger
from forkling.config import Config
from forkling.diary import Diary
from forkling.graveyard import Graveyard
from forkling.llm import LLM
from forkling.memory import Memory
from forkling.planner import Planner
from forkling.self_improve import SelfImproveResult, SelfImprover
from forkling.trace import Trace


def _make_agent(repo: Path, mem_dir: Path) -> Agent:
    """Build a minimal Agent wired into the repo at `repo`."""
    cfg = Config.from_env()
    cfg.repo_root = str(repo)
    cfg.memory_dir = str(mem_dir)
    cfg.llm_timeout = 30
    cfg.test_command = "pytest -q --no-header"
    trace = Trace(mem_dir / "trace.jsonl")
    llm = LLM(url=cfg.ollama_url, model="llama3.2:3b",
              timeout=cfg.llm_timeout, trace=trace)
    memory = Memory(str(mem_dir))
    graveyard = Graveyard(mem_dir / "graveyard.jsonl")
    planner = Planner(llm, graveyard=graveyard)
    return Agent(cfg=cfg, llm=llm, memory=memory, planner=planner)


def _init_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "forkling").mkdir()
    (repo / ".forkling").mkdir()
    # Minimal existing file so `git add` doesn't complain.
    (repo / "README.md").write_text("# test\n", encoding="utf-8")
    # Minimal test file so pytest has something to run.
    (repo / "tests").mkdir()
    (repo / "tests" / "test_dummy.py").write_text(
        "def test_dummy():\n    assert True\n", encoding="utf-8")
    # Pre-create every file in SelfImprover.SAFE_FILES so _pick_target
    # can read whatever it lands on. Content is trivial; the test's
    # stub LLM never actually consults it.
    for name in ("agent.py", "planner.py", "memory.py", "tools.py",
                 "config.py", "llm.py"):
        (repo / "forkling" / name).write_text(
            f"# {name}\nclass _Stub:\n    pass\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=repo, check=True)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=repo, check=True)
    return repo


# ---- validator ----------------------------------------------------------


def test_validate_new_file_rejects_non_forkling_path():
    """The path must start with 'forkling/'."""
    repo = Path("/tmp")  # unused for this test
    si = SelfImprover(agent=None)  # type: ignore[arg-type]
    ok, msg = si._validate_new_file("not_forkling/foo.py",
                                    "x = 1\n", repo)
    assert not ok
    assert "forkling/" in msg


def test_validate_new_file_rejects_non_py_extension():
    si = SelfImprover(agent=None)  # type: ignore[arg-type]
    ok, msg = si._validate_new_file("forkling/foo.txt", "x = 1\n",
                                    Path("/tmp"))
    assert not ok
    assert ".py" in msg


def test_validate_new_file_rejects_path_traversal():
    si = SelfImprover(agent=None)  # type: ignore[arg-type]
    ok, msg = si._validate_new_file("forkling/../../etc/passwd.py",
                                    "x = 1\n", Path("/tmp"))
    assert not ok
    assert "traversal" in msg.lower() or "forkling" in msg


def test_validate_new_file_rejects_existing_file(tmp_path):
    repo = _init_repo(tmp_path)
    (repo / "forkling" / "alpha.py").write_text("x = 1\n", encoding="utf-8")
    si = SelfImprover(agent=None)  # type: ignore[arg-type]
    ok, msg = si._validate_new_file("forkling/alpha.py", "y = 2\n", repo)
    assert not ok
    assert "exists" in msg


def test_validate_new_file_rejects_empty_content():
    si = SelfImprover(agent=None)  # type: ignore[arg-type]
    ok, msg = si._validate_new_file("forkling/alpha.py", "   \n  ",
                                    Path("/tmp"))
    assert not ok
    assert "empty" in msg


def test_validate_new_file_rejects_invalid_python():
    si = SelfImprover(agent=None)  # type: ignore[arg-type]
    ok, msg = si._validate_new_file("forkling/alpha.py",
                                    "def broken(:\n", Path("/tmp"))
    assert not ok
    assert "Python" in msg or "invalid" in msg.lower()


def test_validate_new_file_rejects_third_party_import():
    si = SelfImprover(agent=None)  # type: ignore[arg-type]
    ok, msg = si._validate_new_file("forkling/alpha.py",
                                    "import requests\nx = 1\n",
                                    Path("/tmp"))
    assert not ok
    assert "third-party" in msg or "requests" in msg


def test_validate_new_file_accepts_clean_stdlib_module():
    si = SelfImprover(agent=None)  # type: ignore[arg-type]
    ok, msg = si._validate_new_file(
        "forkling/alpha.py",
        '"""A new capability."""\n'
        'import json\nimport pathlib\nfrom collections import Counter\n\n'
        'def count_words(text: str) -> int:\n'
        '    return len(text.split())\n',
        Path("/tmp"),
    )
    assert ok, msg


# ---- end-to-end with a stub LLM ----------------------------------------


class _StubLLM:
    """LLM that returns a scripted JSON proposal, then 'end'."""

    def __init__(self, proposals: list[dict]):
        self._proposals = list(proposals)
        self.calls = []

    def complete(self, prompt, system=None, kind="complete", task=""):
        from forkling.llm import Completion
        self.calls.append({"prompt": prompt, "system": system,
                           "kind": kind, "task": task})
        if not self._proposals:
            proposal = {"kind": "noop",
                        "reason": "stub: out of scripted proposals"}
        else:
            proposal = self._proposals.pop(0)
        return Completion(text=json.dumps(proposal), used_llm=True,
                          model="stub")


def test_new_file_committed_creates_module_and_records_skill(tmp_path):
    repo = _init_repo(tmp_path)
    mem = tmp_path / "mem"
    mem.mkdir()

    agent = _make_agent(repo, mem)
    # Replace the LLM with a stub that proposes a new_file.
    new_module = (
        '"""Adds a word-counting capability."""\n'
        'import json\nfrom collections import Counter\n\n'
        'def count_words(text: str) -> int:\n'
        '    return Counter(text.split())\n\n'
        'def main() -> int:\n'
        '    return sum(count_words("hello world there").values())\n'
    )
    agent.llm = _StubLLM([{"kind": "new_file",
                          "path": "forkling/wordcount.py",
                          "content": new_module}])
    agent.planner.llm = agent.llm  # in case planner reuses it

    si = SelfImprover(agent)
    result = si.propose_and_apply(goal="add a wordcount tool")
    assert result.committed, (
        f"new_file should have committed; got: "
        f"kind={result.kind} note={result.note}")
    assert result.kind == "new_file"
    assert result.new_skill == "wordcount"
    # The file should exist in the repo.
    new_path = repo / "forkling" / "wordcount.py"
    assert new_path.exists()
    assert "count_words" in new_path.read_text(encoding="utf-8")
    # It should be importable as a real Python module.
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "wordcount", str(new_path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.count_words("a b c") == Counter({"a": 1, "b": 1, "c": 1})
    # Ledger entry with action=self-improve.new_skill.
    ledger_path = mem / "capabilities.jsonl"
    entries = [json.loads(line) for line in
               ledger_path.read_text(encoding="utf-8").splitlines()
               if line.strip()]
    new_skill_entries = [e for e in entries
                         if e.get("action") == "self-improve.new_skill"]
    assert len(new_skill_entries) == 1
    assert new_skill_entries[0]["target"] == "forkling/wordcount.py"
    assert new_skill_entries[0]["extra"]["skill"] == "wordcount"
    # Diary milestone.
    diary_path = mem / "diary.jsonl"
    diary = [json.loads(line) for line in
             diary_path.read_text(encoding="utf-8").splitlines()
             if line.strip()]
    milestones = [e for e in diary if e.get("milestone")]
    assert any("new skill shipped: wordcount" in e.get("content", "")
               for e in milestones)


def test_new_file_rolled_back_when_tests_fail(tmp_path):
    """If the new module breaks pytest, it gets deleted (rolled back)."""
    repo = _init_repo(tmp_path)
    mem = tmp_path / "mem"
    mem.mkdir()

    # Add a passing test that the new module will break.
    (repo / "tests" / "test_must_pass.py").write_text(
        "def test_must_pass():\n    assert False  # force a failure\n",
        encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "add failing test"],
                   cwd=repo, check=True)

    agent = _make_agent(repo, mem)
    new_module = (
        '"""This would be a new skill if it did not break tests."""\n'
        'x = 1\n'
    )
    agent.llm = _StubLLM([{"kind": "new_file",
                          "path": "forkling/broken.py",
                          "content": new_module}])
    agent.planner.llm = agent.llm
    si = SelfImprover(agent)
    result = si.propose_and_apply(goal="add a broken skill to test rollback")
    assert result.rolled_back, "expected rollback on test failure"
    assert result.kind == "new_file"
    assert not result.committed
    # The file should have been deleted.
    assert not (repo / "forkling" / "broken.py").exists()
    # Graveyard should record the failure.
    gv_path = mem / "graveyard.jsonl"
    gv_entries = [json.loads(line) for line in
                  gv_path.read_text(encoding="utf-8").splitlines()
                  if line.strip()]
    assert any("tests failed" in e.get("reason", "")
               for e in gv_entries)


def test_new_file_rejected_when_path_collides(tmp_path):
    repo = _init_repo(tmp_path)
    mem = tmp_path / "mem"
    mem.mkdir()
    # Pre-create a file that the LLM will try to overwrite.
    (repo / "forkling" / "exists.py").write_text(
        "x = 'preexisting'\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "precreate"],
                   cwd=repo, check=True)

    agent = _make_agent(repo, mem)
    agent.llm = _StubLLM([{"kind": "new_file",
                          "path": "forkling/exists.py",
                          "content": "y = 2\n"}])
    agent.planner.llm = agent.llm
    si = SelfImprover(agent)
    result = si.propose_and_apply(goal="overwrite a real file")
    assert not result.committed
    assert not result.changed
    assert "exists" in result.note
    # Original content untouched.
    assert (repo / "forkling" / "exists.py").read_text(
        encoding="utf-8") == "x = 'preexisting'\n"


def test_patch_path_still_works(tmp_path):
    """Regression: the existing patch path is unaffected."""
    repo = _init_repo(tmp_path)
    mem = tmp_path / "mem"
    mem.mkdir()

    # Pre-create a target file with known content.
    (repo / "forkling" / "memory.py").write_text(
        "class Memory:\n    pass\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init memory"],
                   cwd=repo, check=True)

    agent = _make_agent(repo, mem)
    agent.llm = _StubLLM([{"kind": "patch",
                          "path": "forkling/memory.py",
                          "old": "    pass\n",
                          "new": "    pass\n\n    def hello(self):\n"
                                 "        return 'world'\n"}])
    agent.planner.llm = agent.llm
    si = SelfImprover(agent)
    result = si.propose_and_apply(goal="add a hello method")
    assert result.committed
    assert result.kind == "patch"
    assert "hello" in (repo / "forkling" / "memory.py").read_text(
        encoding="utf-8")


def test_selfimprove_result_has_kind_and_new_skill_fields():
    """The dataclass has the new fields kind and new_skill."""
    r = SelfImproveResult(changed=False, committed=False, rolled_back=False,
                          before_sha="a", after_sha="a",
                          patch_summary="x", kind="new_file",
                          new_skill="wordcount")
    assert r.kind == "new_file"
    assert r.new_skill == "wordcount"
    d = r.to_dict()
    assert d["kind"] == "new_file"
    assert d["new_skill"] == "wordcount"
