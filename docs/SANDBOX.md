# Sandbox Mode — Plan for In-Process Hot-Reload (Pre-Implementation Doc)

> **Status:** Planning. Not yet built.
> **Audience:** the next maintainer (including future me) and any external
> reader wondering why we're adding a second evolutionary pathway when the
> file-system pathway already works.
> **Decision to make:** is the risk/benefit profile of letting the agent
> `importlib.reload()` a freshly-written module inside the same generation
> worth the failure modes it opens up?

---

## Why this doc exists

The current `Evolver` writes a new module to disk, runs `pytest -q`, and
either commits or rolls back. Every successful generation is a real git
commit; the cache of "what tools the agent has" lives entirely in the
git history. Each cycle is a discrete boundary — once a generation
starts, the agent's own runtime isn't modified mid-thought.

That design choices two things on purpose:

1. **No in-process hot-reload.** The agent cannot
   `importlib.reload(forkling.wave)` after writing `forkling/wave.py`
   and continue executing with the new module loaded.
2. **The kernel is non-writable to the agent.** Files like
   `agent.py`, `llm.py`, `planner.py`, `config.py`, `diary.py`,
   `capability.py`, `graveyard.py`, `trace.py`, `goals.py`,
   `locking.py`, `self_improve.py`, `evolve.py`, `__main__.py`,
   `desktop.py`, `tray.py`, `daemon.py` cannot be touched by either
   `kind: patch` or `kind: new_file`. Anything outside that list in
   `forkling/` is fair game.

The reason we don't already do hot-reload is that the failure modes
people describe for self-modifying harnesses (a bad refactor wiping
short-term state, compounding hallucination fixing its own error
handler) are real, and the design constraint we picked — "selection
pressure outside the agent's head" — is exactly how we side-step them.

But the user's question — paraphrased — is: *is that the only way?*
This doc is the answer: **no, but the second way needs explicit
guardrails and an A/B comparison.** This document sketches what those
guardrails look like before we write the code.

---

## What "Sandbox Mode" actually means

A new module of the evolve loop, roughly:

```python
class SandboxEvolver:
    """Like Evolver, but lets the agent in-process reload its own
    fresh modules during a single generation."""

    KERNEL_FILES = frozenset({
        "agent.py", "llm.py", "planner.py", "config.py",
        "diary.py", "capability.py", "graveyard.py",
        "trace.py", "goals.py", "locking.py",
        "self_improve.py", "evolve.py", "__main__.py",
        "desktop.py", "tray.py", "daemon.py",
    })

    def run_one_generation(self):
        ...
        # Inside the test step, after writing forkling/<x>.py:
        if module_name in self.scratch_modules:
            importlib.reload(sys.modules[module_name])
            # Mutated state is visible for the rest of the cycle.
        ...
```

Two non-trivial changes from the current loop:

1. **In-process re-import.** After the agent writes a new module to
   `forkling/<x>.py` (kind: new_file), we `importlib.reload()` it
   *within the same generation* so that any tools the agent calls for
   the rest of that cycle see the new module. The agent can therefore
   immediately use the capability it just wrote.

2. **Pin module state, not the process.** Before the generation we
   snapshot every `sys.modules[forkling.*]` entry's `__dict__`. After
   the generation, we restore the snapshot only on rollback. A
   successful `git commit` keeps the reloaded state.

The kernel files are *never* importable for reload — they are
whitelisted out. The agent cannot rewrite or reload `agent.py`,
`llm.py`, etc., even if it tries.

---

## Failure modes we explicitly accept vs. block

| Failure mode                                          | Current loop | Sandbox loop |
|-------------------------------------------------------|--------------|--------------|
| Agent rewrites own `agent.py` mid-generation          | impossible   | impossible (kernel protected) |
| Agent rewrites own `tools.py` mid-generation          | impossible   | impossible (kernel protected) |
| Agent writes a module that misbehaves on reload       | n/a          | test gate catches it on rollback |
| Agent reloads partial state, leaves dangling refs     | n/a          | snapshot/restore on rollback |
| Agent's reload breaks an unrelated module's view      | n/a          | bounded to one module per cycle |
| Hallucination compounds across cycles                 | blocked (each cycle gated) | blocked (each cycle gated) |

The key invariant: **the kernel is non-writable**, **state is
pinned per generation**, and **selection (pytest) still happens
after reload**. None of the failure modes the user raised
("wipe its short-term state," "corrupt its system prompt mid-thought")
are reachable because:

- *short-term state* = agent.py / memory.py / diary.py → kernel
- *system prompt mid-thought* = llm.py → kernel
- *infinite regression* = pytest still external, agent still can't
  rewrite Config.test_command

---

## A/B comparison protocol

Stage 4 of the 365-day cycle (per `docs/ROADMAP.md`) is the model-size
study. We can graft the sandbox comparison onto that:

1. **Baseline branch:** current `Evolver` (no hot-reload).
2. **Treatment branch:** new `SandboxEvolver` (one re-import per cycle).
3. **Same model, same data, same goal pool.** Only the in-process
   visibility of new modules changes.
4. **Outcome metric:** are the two branches producing *different*
   rates of `{committed, rolled_back, noop}` over a fixed budget of
   N generations? Same metric the paper already tracks.
5. **Safety metric:** how many kernel-write attempts happened (must
   be zero); how many state-snapshot-restore events happened (count
   + reason); how many cycles ended in compounding-hallucination
   patterns (manual review, defined as 3+ rollbacks in a row whose
   `before_sha` is itself a rollback).

If sandbox scores the same on `committed` rate AND never opens a
kernel-write path, we keep it as the default for stage 5+. If it
opens even one kernel-write path, we revert.

---

## Implementation outline (only after this plan is approved)

1. Add `forkling/sandbox.py` with `SandboxEvolver`. Mirrors the
   public surface of `Evolver` so we can A/B in tests.
2. Add `KERNEL_FILES` constant alongside `SAFE_FILES`.
3. Add `--sandbox` flag to `forkling evolve`.
4. Add `SysModulesSnapshot` helper in `tools.py` — captures and
   restores `sys.modules[forkling.*]` `__dict__` around a generation.
5. New tests: `tests/test_sandbox.py`. Headline test:
   "kernel-write proposal rejected before reload",
   "snapshot restored on rollback",
   "successful commit keeps the new module loaded".
6. Same `kind: patch | new_file | noop` protocol; only the executor
   differs.
7. Add a stage-4 entry to `paper/papers/` describing the comparison.

---

## What this doc is NOT

- Not a promise to ship sandbox mode unconditionally. The decision
  to ship rests on the A/B result.
- Not a relaxation of "stdlib only" or "pytest -q is the gate."
  Those still hold.
- Not a relaxation of per-fork memory isolation. Sandbox mode is
  still per-process; the `FORKLING_MEMORY` env var still governs
  where `~/.forkling/*` files live.

---

## Open questions for the user

1. Is the kernel list above right, or should anything currently in
   the kernel be moved out (e.g. is `desktop.py` truly kernel, or
   is it decoration)?
2. Should sandbox mode default to OFF and require `--sandbox`, or
   should it be the only mode in stage 5+ and the file-system mode
   archived as "legacy"?
3. Do we want sandbox mode to log *every* `importlib.reload` to the
   trace, or only the ones that survive the gate?
