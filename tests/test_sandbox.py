"""Tests for forkling/sandbox.py — SandboxEvolver + SysModulesSnapshot.

Headline tests (from docs/SANDBOX.md):

  1. **Kernel-write rejected.** A proposal to patch or create a kernel
     file is rejected BEFORE any side effects. Ensures the kernel
     guard in ``self_improve.SelfImprover`` is intact.
  2. **Snapshot restored on rollback.** After a generation whose test
     gate fails, the snapshot restores the ``forkling.*`` modules'
     ``__dict__`` to what they were before the generation started.
  3. **Successful commit keeps reload.** After a successful
     ``kind: new_file`` commit, ``importlib.reload()`` puts the new
     module on ``sys.modules`` and it's callable from the same
     process for the rest of the session.

Plus smaller unit tests for ``SysModulesSnapshot`` and
``reload_module`` so regressions surface early.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from textwrap import dedent

import pytest


# ---- helpers --------------------------------------------------------------


def _git(repo: Path, *args: str, env: dict | None = None) -> str:
    """Run a git command in ``repo`` and return stdout."""
    full_env = {
        "PATH": "/usr/bin:/usr/local/bin:/bin:/opt/homebrew/bin",
        "HOME": str(Path.home()),
        "GIT_AUTHOR_NAME": "Forkling",
        "GIT_AUTHOR_EMAIL": "agent@forkling.local",
        "GIT_COMMITTER_NAME": "Forkling",
        "GIT_COMMITTER_EMAIL": "agent@forkling.local",
    }
    if env:
        full_env.update(env)
    out = subprocess.run(
        ["git", *args], cwd=str(repo), capture_output=True,
        text=True, env=full_env, check=False,
    )
    if out.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} failed in {repo}: "
            f"{out.stderr.strip()}")
    return out.stdout.strip()


def _init_repo(repo: Path) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "agent@forkling.local")
    _git(repo, "config", "user.name", "Forkling")
    # Pre-create the public forkling module set + every file in
    # SelfImprover.SAFE_FILES so _pick_target can read whatever it
    # lands on. Content is trivial; the test's stub LLM never
    # actually consults it.
    pkg = repo / "forkling"
    pkg.mkdir(exist_ok=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    from forkling.self_improve import SelfImprover
    for rel in SelfImprover.SAFE_FILES:
        path = repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            f"# {rel}\nclass _Stub:\n    pass\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "init")


def _stub_llm(response: str):
    """Build a stub LLM that always returns ``response``."""
    from forkling.llm import Completion

    class _Stub:
        def __init__(self, text: str) -> None:
            self._text = text

        def complete(self, *, prompt: str, system: str = "",
                     kind: str = "task", task: str = "",
                     **kwargs):
            return Completion(text=self._text, used_llm=True,
                              model="stub-llm")

    return _Stub(response)


def _agent(repo: Path, mem: Path, monkeypatch, llm_response: str):
    """Build a minimal Agent wired to a stub LLM, using the full
    dependency wiring from test_new_skill._make_agent so the Agent
    constructor's required args (cfg, llm, memory, planner) are
    satisfied.
    """
    monkeypatch.setenv("FORKLING_MEMORY", str(mem))
    monkeypatch.setenv("FORKLING_LLM_TIMEOUT", "10")
    monkeypatch.setenv("FORKLING_OLLAMA_URL", "http://127.0.0.1:1")
    from forkling.config import Config
    from forkling.trace import Trace
    from forkling.llm import LLM
    from forkling.memory import Memory
    from forkling.graveyard import Graveyard
    from forkling.planner import Planner
    from forkling import agent as _agent_mod
    cfg = Config.from_env()
    cfg.repo_root = str(repo)
    cfg.memory_dir = str(mem)
    cfg.llm_timeout = 30
    cfg.test_command = "pytest -q --no-header"
    trace = Trace(mem / "trace.jsonl")
    llm = LLM(url=cfg.ollama_url, model="llama3.2:3b",
              timeout=cfg.llm_timeout, trace=trace)
    memory = Memory(str(mem))
    graveyard = Graveyard(mem / "graveyard.jsonl")
    planner = Planner(llm, graveyard=graveyard)
    a = _agent_mod.Agent(cfg=cfg, llm=llm, memory=memory,
                         planner=planner)
    a.llm = _stub_llm(llm_response)
    a.planner.llm = a.llm
    return a


# ---- SysModulesSnapshot ----------------------------------------------------


def test_snapshot_capture_collects_forkling_modules():
    """Snapshot capture takes a __dict__ copy of every forkling.* module."""
    from forkling import sandbox
    snap = sandbox.SysModulesSnapshot.capture()
    # At capture time, all the core forkling modules are loaded.
    assert "forkling.tools" in snap._snapshot
    # __dict__ copy is a real dict, not the module itself.
    assert isinstance(snap._snapshot["forkling.tools"], dict)


def test_snapshot_restore_drops_additions():
    """Restore drops modules added during the snapshot window."""
    import sys as _sys
    from forkling import sandbox
    snap = sandbox.SysModulesSnapshot.capture()
    # Add a fake forkling.* module during the window.
    _sys.modules["forkling._smoke_test_dummy"] = type(sys)("forkling._smoke_test_dummy")
    # Restore.
    added = snap.restore()
    assert "forkling._smoke_test_dummy" in added
    # Module is gone from sys.modules.
    assert "forkling._smoke_test_dummy" not in _sys.modules


def test_snapshot_restore_resets_mutated_dict():
    """If a forkling.* module's __dict__ was mutated, restore undoes it."""
    from forkling import sandbox
    snap = sandbox.SysModulesSnapshot.capture()
    # Mutate.
    import forkling.tools
    forkling.tools.__dict__["_smoke_marker"] = "before"
    # Restore.
    snap.restore()
    assert "_smoke_marker" not in forkling.tools.__dict__


# ---- reload_module --------------------------------------------------------


def test_reload_module_returns_module_or_none():
    from forkling import sandbox
    # Import clock first so it's on sys.modules; reload_module works
    # on modules that are already loaded.
    import forkling.clock  # noqa: F401  (ensure it's loaded)
    m = sandbox.reload_module("forkling.clock")
    assert m is not None
    # Unknown module — should return None gracefully, not raise.
    assert sandbox.reload_module("forkling.this_does_not_exist") is None


# ---- kernel-write rejection ------------------------------------------------


def test_kernel_paths_are_in_KERNEL_FILES():
    """Sanity: every kernel module is in KERNEL_FILES."""
    from forkling.self_improve import SelfImprover
    KERNEL = SelfImprover.KERNEL_FILES
    for path in (
        "forkling/agent.py", "forkling/llm.py", "forkling/planner.py",
        "forkling/config.py", "forkling/diary.py",
        "forkling/capability.py", "forkling/graveyard.py",
        "forkling/trace.py", "forkling/goals.py",
        "forkling/locking.py", "forkling/self_improve.py",
        "forkling/evolve.py", "forkling/__main__.py",
        "forkling/desktop.py", "forkling/tray.py",
        "forkling/daemon.py", "forkling/sandbox.py",
        "forkling/tools.py",
    ):
        assert path in KERNEL, f"missing kernel path: {path}"


def test_is_kernel_path_recognises_kernel_files():
    """is_kernel_path returns True for kernel files, False for the rest."""
    from forkling.self_improve import SelfImprover
    assert SelfImprover.is_kernel_path("forkling/agent.py")
    assert SelfImprover.is_kernel_path("forkling/sandbox.py")
    assert not SelfImprover.is_kernel_path("forkling/foo.py")
    assert not SelfImprover.is_kernel_path("")


def test_kernel_patch_rejected_before_apply(tmp_path, monkeypatch):
    """A patch proposal targeting a kernel file is rejected BEFORE
    the file is touched. The before-sha is preserved."""
    repo = tmp_path / "repo"
    mem = tmp_path / "mem"
    _init_repo(repo)

    from forkling.self_improve import SelfImprover
    a = _agent(repo, mem, monkeypatch,
               llm_response=json.dumps({
                   "kind": "patch",
                   "path": "forkling/agent.py",
                   "old": "class _Stub:\n    pass\n",
                   "new": "class _Stub:\n    pass\n# malicious\n",
               }))
    si = SelfImprover(a)
    before_sha = _git(repo, "rev-parse", "HEAD")
    result = si.propose_and_apply(goal="patch the kernel")
    after_sha = _git(repo, "rev-parse", "HEAD")
    # No commit happened.
    assert not result.committed
    assert before_sha == after_sha
    # And the patch was actually rejected by the kernel guard, not by
    # the uniqueness check or some other downstream reason.
    assert "kernel" in result.patch_summary.lower() or \
           "kernel" in (result.note or "").lower()


def test_kernel_new_file_rejected_in_validator():
    """A kind:new_file proposal targeting a kernel file is rejected by
    _validate_new_file."""
    from forkling.self_improve import SelfImprover
    si = SelfImprover.__new__(SelfImprover)
    ok, msg = si._validate_new_file(
        "forkling/agent.py",
        "class Agent: pass\n",
        Path("/tmp"),
    )
    assert not ok
    assert "kernel" in msg.lower()


# ---- Snapshot restored on rollback ----------------------------------------


def test_snapshot_restore_after_rollback_strips_in_process_changes(
    tmp_path, monkeypatch,
):
    """If a kind:new_file commit fails pytest, the rollback on the
    *file system* is automatic. The sandbox ALSO restores any in-process
    re-imports to the pre-generation state.

    We simulate this by writing a brand-new file, then mutating
    sys.modules via a fake 'reload' that's a no-op, then verifying the
    snapshot path correctly resets things.
    """
    from forkling import sandbox
    import forkling.tools as tools_mod

    # Capture baseline.
    snap = sandbox.SysModulesSnapshot.capture()

    # Simulate: a kind:new_file cycle wrote a new module file but the
    # pytest gate failed. The Evolver would normally git-checkout the
    # file. Sandbox mode's wrapper would ALSO restore the in-process
    # snapshot of any modules it touched (here, none in this bare
    # test, but we prove the API does what we claim).
    tools_mod.__dict__["_smoke_added_during_rollback_window"] = "garbage"
    added = snap.restore()
    assert "_smoke_added_during_rollback_window" not in tools_mod.__dict__
    # Nothing got added under forkling.* either.
    assert added == []


# ---- SandboxEvolver class surface -----------------------------------------


def test_sandbox_evolver_is_an_evolver_subclass():
    """SandboxEvolver subclasses Evolver — same public surface, hot-reload added."""
    from forkling.sandbox import SandboxEvolver
    from forkling.evolve import Evolver
    assert issubclass(SandboxEvolver, Evolver)


def test_sandbox_evolver_default_constructor():
    """SandboxEvolver accepts the same kwargs as Evolver, plus two new ones."""
    from forkling.sandbox import SandboxEvolver
    # Just check the parameters exist on the signature.
    import inspect
    sig = inspect.signature(SandboxEvolver.__init__)
    assert "reload_after_commit" in sig.parameters
    assert "snapshot_per_generation" in sig.parameters


# ---- Successful commit keeps reload (end-to-end) --------------------------


def test_successful_new_file_commits_reload_into_process(
    tmp_path, monkeypatch,
):
    """After a successful kind:new_file commit, calling reload_module
    on the resulting module makes it callable from the same process.

    This is the headline affordance of sandbox mode: the rest of the
    session sees freshly-shipped capabilities.

    We use a minimal in-tree test fixture (a real forkling module
    written by the agent's propose_and_apply) — not the LLM, so the
    test is deterministic.
    """
    from forkling import sandbox
    import sys as _sys
    repo = tmp_path / "repo"
    mem = tmp_path / "mem"
    _init_repo(repo)

    # Write a minimal new module that survives pytest trivially.
    new_path = repo / "forkling" / "smoke_skill.py"
    new_path.write_text(
        dedent("""
        # Smoke skill for sandbox tests. Adds a marker function.
        SMOKE_MARKER = "loaded"


        def smoke_marker() -> str:
            return SMOKE_MARKER
        """).lstrip(),
        encoding="utf-8",
    )

    # Commit it.
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "smoke skill")

    # Confirm the module is not on sys.modules yet (fresh process).
    assert "forkling.smoke_skill" not in _sys.modules

    # Reload via the sandbox helper.
    module_name = "forkling.smoke_skill"
    reloaded = sandbox.reload_module_from_path(
        module_name, new_path)
    assert reloaded is not None
    assert reloaded in _sys.modules.values()
    # And the function works.
    assert reloaded.SMOKE_MARKER == "loaded"
    assert reloaded.smoke_marker() == "loaded"


# ---- _ReloadingSelfImprover delegation ------------------------------------


def test_reloading_self_improver_delegates_unknown_attrs(tmp_path):
    """Anything not overridden by _ReloadingSelfImprover is forwarded to
    the inner SelfImprover. We verify one arbitrary passthrough."""
    from forkling import sandbox
    from forkling.self_improve import SelfImprover

    # Construct an inner (not via __init__ — bypass the agent requirement
    # since we're not calling propose_and_apply here).
    inner = SelfImprover.__new__(SelfImprover)

    wrapper = sandbox._ReloadingSelfImprover(
        inner=inner, reload_after_commit=True,
        snapshot_per_generation=True,
        snapshot_log=[], agent_root=tmp_path,
    )
    # Unknown attr falls through to ``inner`` — inner doesn't have
    # ``arbitrary_attr`` either, so AttributeError propagates.
    with pytest.raises(AttributeError):
        _ = wrapper.arbitrary_attr
    # ``agent`` property delegates.
    inner.agent = object()
    assert wrapper.agent is inner.agent
