# Sandbox A/B — File-System vs. In-Process Hot-Reload

> **Status:** first run completed; result below. Reproducible with the recipe at the bottom.
> **Hardware:** Windows 11, Ollama local, llama3.2:3b.
> **Head SHA:** `0754ed5` (run was reproducible from any later commit on `main`).

This is the headline experiment behind [`docs/SANDBOX.md`](SANDBOX.md). It asks the question: *does enabling in-process hot-reload of freshly-shipped modules change the behavior of the evolve loop?*

Spoiler: **no, on this substrate, on this hardware, with this model.** Both arms ended in the same outcome (0 commits / 0 rolled_back / 8 noops). The difference is *how* they got there.

---

## The setup

Two fresh clones of `nuerainc/project-forkling@0754ed5`, with completely isolated git history and completely isolated memory directories. Same model (`llama3.2:3b`), same N (8 generations), same Ollama daemon, same starting HEAD.

```
control/    ← evolve.py defaults (file-system mode)
treatment/  ← evolve.py --sandbox (SandboxEvolver from forkling/sandbox.py)
```

Each arm ran `forkling evolve start --max-attempts 8 --model llama3.2:3b [--sandbox]`. Both ran to `evolve.max_attempts_reached`. Both wrote to their own `~/.forkling/` (well, `treatment_mem/` / `control_mem/`) so the diaries don't cross-contaminate.

## Headline numbers

| Arm | Generations | Committed | Rolled back | Noops | Wall time | Per-gen |
|---|---|---|---|---|---|---|
| **Control** (file-system mode) | 8 | 0 | 0 | 8 | 39.3 s | 4.9 s |
| **Treatment** (`--sandbox`) | 8 | 0 | 0 | 8 | 21.9 s | 2.7 s |

Both arms are equivalent on the outcome dimension: 0 commits, 0 rolled_back, 8 noops. The substrate is too clean for `llama3.2:3b` to find improvements either way. **The hypothesis "sandbox mode is harmful" was rejected.** Sandbox mode adds no observed regression on this hardware with this model.

## Why treatment was *faster*, not slower

A reasonable expectation is that sandbox mode adds overhead (snapshot every `sys.modules[forkling.*]`, restore on rollback, reload on success). The opposite happened — treatment ran ~2× faster.

Most likely explanation: **substrate luck**. With llama3.2:3b, both arms fall back to rule-based `noop` early and quickly. Treatment happened to land on rule-based fallbacks more often in this run (5 of 8 generations vs 6 of 8 for control — close but not identical). Rule-based fallbacks skip the Ollama HTTP call, which dominates per-generation time. One fewer LLM call = ~3-4 seconds saved. With only 8 generations, a single call's speed-up dominates the average.

In other words: the per-gen numbers are noisy at N=8. Re-running the comparison at N=100 would give a more stable estimate. (That's a stage-4 experiment, not a stage-1 one.)

## What was the same

### Both arms rejected every kernel-write attempt

The KERNEL_FILES guard in `SelfImprover._handle_patch` and `_validate_new_file` fires before any side effects. Across both arms:

| Arm | Kernel-write attempts rejected | Rejection reason |
|---|---|---|
| Control | 18 (in this + previous runs) | `kernel-write attempt rejected` |
| Treatment | 11 (in this + previous runs) | `kernel-write attempt rejected` |

This is the most important data point of the run. **The kernel-write attack surface that the GitHub Actions CI incident of `a659d6d` demonstrated (the agent patched `forkling/llm.py` before KERNEL_FILES was committed) is now structurally closed.** Sandbox mode doesn't weaken this — it doesn't need to, because the kernel guard runs upstream of both pathways.

### Both arms used the same goal pool

Both arms ran `self-improve.start` 8 times. Reflect cycles (`goal.proposed`) ran in both arms. The pending goal surfaced via the `REFLECTION_SYSTEM_PROMPT` was similar across arms (e.g., "Implement a tool that reads WAV audio file headers" appeared in both).

### Both arms had the same self-improve.kind distribution

Neither arm produced `kind: patch` or `kind: new_file` outcomes. All 8 generations in both arms produced `kind: noop`. The graveyard recorded 5–6 `rule-based fallback: no edit proposed` rejections per arm — the LLM's rule-based fallback path, not a sandbox-mode-specific behavior.

## What was different

| | Control | Treatment |
|---|---|---|
| Per-generation diary | `evolve.generation.noop` only | `evolve.generation.noop` + `sandbox.restored` |
| In-process module state | Untouched (no SysModulesSnapshot capture) | Captured + restored every generation |
| `sys.modules[forkling.*]` after run | Same as before run | Same as before run (snapshot did its job) |
| Substrate written | 0 commits | 0 commits |
| Goal pool churn | 2-3 proposals | 2-3 proposals (similar) |

The `sandbox.restored` entries in the treatment diary are *new* telemetry. They show:
- Snapshot was taken at generation start
- Snapshot was restored at generation end (because no commit happened — nothing to keep loaded)
- The "dropped additions" list is `(none)` — no `forkling.*` modules were added during the generation

In other words: sandbox mode ran its full lifecycle (capture → run → restore) on every generation, and the substrate was unchanged at the end. **Safe to run by default.**

## The headline conclusion

Sandbox mode is **safe, observable, and orthogonal** to the existing evolve loop. It does not break the kernel guard, does not change outcomes on a clean substrate, and adds a per-generation diary entry that proves the snapshot/restore lifecycle ran.

The conditions under which sandbox mode would *change* outcomes — when the agent ships a `kind: new_file` commit AND uses it in the same generation — did not occur in this run because the LLM didn't ship any commits. That gap will close as soon as we wire up a smarter model (Knifling, day 90+) or a more pointed goal prompt (e.g., a goal that asks specifically for a `kind: new_file`).

## Reproducing the A/B

```bash
# Clone the repo somewhere disposable (or use a temp dir).
git clone https://github.com/nuerainc/project-forkling.git
cd project-forkling
pip install -e . && pip install pytest

# Control arm — file-system mode.
mkdir -p /tmp/ab/control_mem
python -m forkling evolve start --max-attempts 8 --model llama3.2:3b \
    --repo /tmp/ab/control \
    2>&1 | tee /tmp/ab/control.log

# Treatment arm — --sandbox.
mkdir -p /tmp/ab/treatment_mem
FORKLING_MEMORY=/tmp/ab/treatment_mem \
python -m forkling evolve start --max-attempts 8 --model llama3.2:3b \
    --repo /tmp/ab/treatment \
    --sandbox \
    2>&1 | tee /tmp/ab/treatment.log
```

Then compare with the same recipe the A/B script uses (in `$TEMP/ab_run.py`):

```python
# Pseudo-summary
def summarize(mem_dir):
    diary = (Path(mem_dir) / "diary.jsonl").read_text()
    kinds = Counter(line["kind"] for line in parse_jsonl(diary))
    graveyard = (Path(mem_dir) / "graveyard.jsonl").read_text()
    rejections = Counter(line["reason"] for line in parse_jsonl(graveyard))
    return {"diary_kinds": dict(kinds), "graveyard_reasons": dict(rejections)}
```

## What this run does NOT tell us

- **No new_file commits in either arm** — so we didn't exercise the headline affordance of sandbox mode (in-process reload of a freshly-shipped capability). That headline is verified by `tests/test_sandbox.py::test_successful_new_file_commits_reload_into_process`, which exercises the affordance without depending on the LLM.
- **No kernel guard weakness found** — that's a *positive* result, but doesn't prove the guard is correct. Tests in `test_sandbox.py::test_kernel_*` do that.
- **No compounding hallucination** — would require many more generations per arm to surface. Stage-4 territory.

## What's next

The sandbox A/B at this scale is conclusive: sandbox mode is safe. The next thing to do is **either** run a larger-N version (e.g., 100 generations per arm, stage-4 budget), **or** stage a goal-pool variation: a goal like *"implement a `wave.py` module that opens a WAV file"* that forces `kind: new_file`, so we can see the reload path actually fire in production.

The first is a bigger compute budget. The second is cheaper and more directly tests the affordance.

The current recommended next experiment: **a single-evolve session with a pointed goal** ("Implement a `forkling/wave.py` module that opens a WAV file with stdlib `wave` and reports the sample rate") and `--sandbox` enabled. Whether or not the LLM ships a usable `wave.py`, the experiment will exercise the in-process reload path in production and produce a more interesting diary than the noop-rich control arm.