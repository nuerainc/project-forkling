"""Sandbox mode — in-process hot-reload for fresh modules.

The default ``Evolver`` writes a new module to disk, runs ``pytest -q``,
and either commits or rolls back. After a successful ``kind: new_file``
commit, the *next* generation's ``SelfImprover`` instance is a fresh
process (or a fresh import) and would see the new module — but within a
*single* ``Evolver.run_forever`` session, the module is on disk and
not loaded in the running interpreter. The agent's own LLM calls for
that session cannot *use* the new module.

Sandbox mode closes that gap. After every successful ``new_file`` commit,
the new module is ``importlib.reload()``-ed into the live process, so
the rest of the session sees it. State is pinned per generation via
``SysModulesSnapshot`` so a rollback path can revert cleanly.

Design rules (full rationale in ``docs/SANDBOX.md``):

  1. **Kernel is non-writable.** Files in ``SelfImprover.KERNEL_FILES``
     cannot be patched or created. This is enforced *before* any change
     touches the working tree.
  2. **State is pinned per generation.** Every entry in
     ``sys.modules[forkling.*]`` is snapshotted at the start of each
     generation; on rollback the snapshot is restored.
  3. **Selection (pytest) still happens after reload.** The test gate
     never moves; sandbox mode just makes the agent's *own* runtime
     reflect what survived pytest.
  4. **Same protocol.** ``kind: patch | new_file | noop`` — only the
     executor differs.

This module is **opt-in**. ``forkling evolve --sandbox`` activates it.
The default (``Evolver``) remains the safe baseline.
"""

from __future__ import annotations

import importlib
import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Iterable

from . import tools
from .evolve import Evolver
from .self_improve import SelfImprover


# Anything we snapshot / restore lives under these prefixes.
SANDBOX_PREFIXES = ("forkling.",)


class SysModulesSnapshot:
    """Capture-and-restore wrapper for ``sys.modules[forkling.*]``.

    Usage::

        snap = SysModulesSnapshot.capture()
        try:
            ... # do things that may add/replace forkling.* modules
        except Exception:
            snap.restore()
            raise

    ``capture`` returns a snapshot of *every* module in
    ``sys.modules`` whose name starts with one of ``SANDBOX_PREFIXES``.
    ``restore`` puts those modules back, dropping any entries that
    weren't in the snapshot and resetting each surviving module's
    ``__dict__`` to the captured version.

    Note: this only protects ``forkling.*`` modules. Anything else in
    ``sys.modules`` (stdlib, third-party) is left untouched.
    """

    def __init__(self, snapshot: dict[str, dict]):
        # Map of module-name → module-__dict__ copy at capture time.
        self._snapshot = snapshot
        # Also remember which module objects were in sys.modules at
        # capture time, so we can drop additions later.
        self._names = set(snapshot.keys())

    @classmethod
    def capture(cls) -> "SysModulesSnapshot":
        snap: dict[str, dict] = {}
        for name, mod in list(sys.modules.items()):
            if not _is_sandbox_module(name):
                continue
            try:
                snap[name] = dict(vars(mod))
            except Exception:
                # Modules with locked __dict__ (rare) get an empty
                # snapshot; restore will just drop them.
                snap[name] = {}
        return cls(snap)

    def restore(self) -> list[str]:
        """Restore the snapshot. Returns the list of module names that
        were *added* during the snapshot window (and are now dropped).
        """
        added: list[str] = []
        for name, mod in list(sys.modules.items()):
            if not _is_sandbox_module(name):
                continue
            if name not in self._names:
                # Newly added during the snapshot window — drop it.
                added.append(name)
                try:
                    del sys.modules[name]
                except KeyError:
                    pass
        # Now restore __dict__ of surviving modules.
        for name, saved_dict in self._snapshot.items():
            mod = sys.modules.get(name)
            if mod is None:
                # Module was deleted during the window; re-import it.
                try:
                    mod = importlib.import_module(name)
                except Exception:
                    continue
            try:
                # Reset module __dict__ in place; references held by
                # callers continue to point to the same module object.
                mod.__dict__.clear()
                mod.__dict__.update(saved_dict)
            except Exception:
                # Best effort. If __dict__ can't be cleared (frozen
                # module, etc.), just leave it.
                pass
        return added


def _is_sandbox_module(name: str) -> bool:
    return any(name == p or name.startswith(p)
               for p in SANDBOX_PREFIXES)


def reload_module(module_name: str) -> ModuleType | None:
    """Reload a single module by name. Returns the reloaded module, or
    None if the module isn't in ``sys.modules`` or can't be reloaded.

    The point of this helper is to make hot-reload explicit and
    auditable. We don't use ``importlib.reload(sys.modules[name])``
    inline anywhere else — always go through this so the call site is
    grep-able.
    """
    if module_name not in sys.modules:
        return None
    try:
        return importlib.reload(sys.modules[module_name])
    except Exception:
        return None


def reload_module_from_path(module_name: str, path: str | Path) -> ModuleType | None:
    """Reload a module using a specific file path. Useful after a
    ``kind: new_file`` write where the file is on disk but the in-memory
    module either doesn't exist yet or was loaded from a stale path.

    Equivalent to ``importlib.reload(sys.modules[name])`` if the module
    is already loaded; otherwise behaves like a fresh ``spec_from_file``
    import.

    Returns the reloaded module, or None on failure.
    """
    p = Path(path)
    if module_name in sys.modules:
        return reload_module(module_name)
    spec = importlib.util.spec_from_file_location(module_name, p)
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    try:
        spec.loader.exec_module(mod)
    except Exception:
        try:
            del sys.modules[module_name]
        except KeyError:
            pass
        return None
    return mod


class SandboxEvolver(Evolver):
    """Like ``Evolver``, but performs ``importlib.reload()`` of every
    freshly-committed ``kind: new_file`` module so the rest of the
    session sees the new capability immediately.

    Subclasses ``Evolver`` rather than rewriting it. The only override
    is ``_get_improver`` — it returns a wrapped ``SelfImprover`` whose
    ``_handle_new_file`` reloads the new module after a successful
    commit.

    All other behaviour, including ``_reflect_cycle`` and the goal
    pipeline, is inherited unchanged.
    """

    # The sandbox itself is never reloaded by a generation. The
    # kernel-list lives in ``SelfImprover.KERNEL_FILES``; this module
    # is in that list (see ``self_improve.py``).
    RELOAD_LOG_KIND = "sandbox.reloaded"

    def __init__(self, *args, reload_after_commit: bool = True,
                 snapshot_per_generation: bool = True, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.reload_after_commit = reload_after_commit
        self.snapshot_per_generation = snapshot_per_generation
        # Snapshot history for diagnostics. Per generation: one entry.
        self._snapshot_log: list[dict] = []

    # ---- entry-point overrides --------------------------------------------

    def _get_improver(self) -> SelfImprover:
        """Return a ``SelfImprover`` wrapped to reload new_file commits."""
        improver = super()._get_improver()
        return _ReloadingSelfImprover(
            inner=improver,
            reload_after_commit=self.reload_after_commit,
            snapshot_per_generation=self.snapshot_per_generation,
            snapshot_log=self._snapshot_log,
            agent_root=self.repo,
        )


class _ReloadingSelfImprover:
    """Wraps a ``SelfImprover`` and reloads after a successful
    ``kind: new_file`` commit. Delegates everything else.

    Implemented as a thin wrapper rather than a subclass so the original
    ``SelfImprover`` logic stays untouched. The reload happens *after*
    the commit lands and *after* pytest passes — exactly the moment when
    the new module is safe to use.
    """

    def __init__(self, *, inner: SelfImprover,
                 reload_after_commit: bool,
                 snapshot_per_generation: bool,
                 snapshot_log: list[dict],
                 agent_root: Path) -> None:
        self._inner = inner
        self._reload_after_commit = reload_after_commit
        self._snapshot_per_generation = snapshot_per_generation
        self._snapshot_log = snapshot_log
        self._agent_root = Path(agent_root)

    # Delegate every attribute access to the inner improver; the only
    # method we override is ``propose_and_apply``.
    def __getattr__(self, name):
        return getattr(self._inner, name)

    @property
    def agent(self):
        return self._inner.agent

    def propose_and_apply(self, goal: str = ""):
        """Wrap ``propose_and_apply`` to add snapshot+reload semantics.

        Lifecycle of one generation in sandbox mode:

          1. ``SysModulesSnapshot.capture()`` — pin every
             ``sys.modules[forkling.*]`` entry's ``__dict__``.
          2. Delegate to ``inner.propose_and_apply(goal)``.
          3. If the result is ``kind: new_file`` and committed:
               - ``importlib.reload(sys.modules[forkling.<new>])``
               - log a ``sandbox.reloaded`` diary entry
          4. If the result was rolled back OR if reload fails:
               - ``SysModulesSnapshot.restore()``
               - log a ``sandbox.restored`` diary entry
          5. Always append the snapshot metadata to ``_snapshot_log``
             for later diagnostics.
        """
        snap: SysModulesSnapshot | None = None
        if self._snapshot_per_generation:
            snap = SysModulesSnapshot.capture()

        result = self._inner.propose_and_apply(goal=goal)

        reloaded: str | None = None
        restored: bool = False
        try:
            if (self._reload_after_commit
                    and result.committed
                    and result.kind == "new_file"
                    and result.new_skill):
                module_name = f"forkling.{result.new_skill}"
                # Ensure the module is on sys.modules before reloading.
                if module_name not in sys.modules:
                    # First-time import using the file we just committed.
                    file_path = self._agent_root / "forkling" / f"{result.new_skill}.py"
                    if file_path.exists():
                        reload_module_from_path(module_name, file_path)
                if module_name in sys.modules:
                    reloaded_module = reload_module(module_name)
                    if reloaded_module is not None:
                        reloaded = module_name
                        self._inner.agent.diary.write(
                            SandboxEvolver.RELOAD_LOG_KIND,
                            f"reloaded {module_name} after commit {result.after_sha[:7]}",
                            module=module_name,
                            sha_after=result.after_sha,
                            proposal_kind=result.kind,
                        )
        finally:
            # If anything failed or we just need to roll back the
            # runtime state — restore the snapshot. Note: a successful
            # commit *also* leaves the snapshot in place (we want the
            # new module to stay loaded), so we only restore on
            # rollback / failure.
            if snap is not None:
                should_restore = (
                    not result.committed
                    or result.rolled_back
                    or (reloaded is None
                        and result.kind == "new_file"
                        and result.committed)
                )
                if should_restore:
                    added = snap.restore()
                    restored = True
                    self._inner.agent.diary.write(
                        "sandbox.restored",
                        f"rolled back forkling.* modules; "
                        f"dropped additions: {added or '(none)'}",
                        added=added,
                        sha_before=result.before_sha,
                        sha_after=result.after_sha,
                        proposal_kind=result.kind,
                    )

        self._snapshot_log.append({
            "committed": result.committed,
            "rolled_back": result.rolled_back,
            "kind": result.kind,
            "new_skill": result.new_skill,
            "reloaded": reloaded,
            "restored": restored,
            "before_sha": result.before_sha,
            "after_sha": result.after_sha,
        })

        return result
