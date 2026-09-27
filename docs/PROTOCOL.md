# Forkling Protocol v0.1 (draft, explicitly provisional)

**Status:** v0.1 draft — describes the harness as of exp001–003
(**protocol 1**, `forkling/experiment.py`).
v4r1 (`paper/hypothesis_v4r1.md`) introduces **protocol 2**
(`forkling/experiment2.py`) and ships a v0.2 protocol revision as an
addendum at the end of this file. **Read v0.2 first** before
running or extending a published result.

**Not a frozen spec.** Fields and procedures here are derived from how
`forkling/*.py` actually runs *today*. v1.0 will lock these; until
then, expect breaking changes.

This document defines a *lab-notebook* level spec for running a
Forkling organism: setup, runtime, evaluation, reporting. The
audience is a researcher cloning the repo and wanting to reproduce
or extend a published result. A lab student should be able to
onboard in a day using this doc plus the schema and family-setup
docs as companions.

What is *not* in v0.1:
- **Cross-fork speciation protocol** (§4 in the strategic
  plan). The family setup is documented in `docs/FAMILY_SETUP.md`
  but does not yet have a pre-registered experimental design.
- **Forkling-30/90/365 dataset releases.** Only the day-7
  `paper/datasets/*.zip` artifacts exist today.
- **Multi-environment SLOs.** Single-machine runs only.

---

## 1. Setup

### 1.1 Hardware floor (per organism)

- **Disk:** ~6 GB free (qwen2.5-coder:3b + qwen2.5-coder:7b
  optionally, plus ollama runtime + working tree).
- **RAM:** ≥ 4 GB. Tested on 4 GB RTX 2050 (qwen2.5-coder:3b
  fits fully in VRAM; qwen2.5-coder:7b partial-offloads).
- **OS:** Windows / Linux / macOS. Tested on Windows.
- **Network:** outbound HTTP to `http://127.0.0.1:11434`
  (Ollama default), no external API access.

### 1.2 Software

- Python ≥ 3.10 (uses `dict[str, ...]` PEP-585 syntax).
- `ollama` ≥ 0.4 with ≥ one model pulled
  (`qwen2.5-coder:3b` is the default per
  `paper/MODEL_DECISION.md`).
- `pytest` (the only dev dependency).
- **No third-party runtime libraries.** Stdlib only at runtime.

### 1.3 State directory

Default: `~/.forkling/`. Override per fork:

```bash
export FORKLING_MEMORY=/path/to/fork-state   # Git Bash / Linux
$env:FORKLING_MEMORY = 'D:\path\to\fork-state'  # PowerShell
```

Layout:

```
$FORKLING_MEMORY/
  diary.jsonl              # chat diary (free-form)
  capabilities.jsonl       # SHA-256-chained ledger
  goals.jsonl              # goal proposals + status updates
  graveyard.jsonl          # rejected patches with reasons
  trace.jsonl              # LLM I/O trace  [v0.2]
  model-benchmark.jsonl    # one-shot model probes  [v0.2]
  memory.json              # single-file memory snapshot
  family.json              # registry of opt-in forks  [v1.0]
  evolve.pid               # current evolve-loop pid (if running)
  evolve.stop              # touchfile to request graceful stop
  evolve.status.json       # current evolve-loop metrics (if running)
```

Schema: see `docs/SCHEMA.md`.

### 1.4 Working-tree assumption

The agent evolves a *real* git checkout. Successful proposals
become real commits. Every commit's SHA is recorded in the
capability ledger's `agent_sha` field.

---

## 2. Runtime

### 2.1 Evolve loop (default)

```bash
python -m forkling evolve \
    --repo /path/to/checkout \
    [--model qwen2.5-coder:3b] \
    [--max-attempts 100] \
    [--reflect-every 5]
```

The loop is `Evolver.run_forever`-style: **no idle waiting.** Each
attempt runs back-to-back, throttled only by the LLM response
time and the pytest gate. Termination is by `--max-attempts`
or by `touch $FORKLING_MEMORY/evolve.stop`.

**Vocabulary** (kept honest because the noop rate is high —
see `FAILURE_TAXONOMY.md`):

- `attempt`: one cycle through the loop.
- `generation`: an attempt whose commit landed in git. The
  Dawkins sense — a heritable change.
- `noop`: an attempt that produced no commit (kernel guard,
  validator, or rule-based fallback).
- `rolled-back`: an attempt whose commit was reverted by
  `git checkout` because pytest failed.

Most attempts are noops or rolled-back. **That is selection
pressure, not a bug.** The interesting metric is *generations
per day*, not *attempts per day*.

### 2.2 Sandbox mode (optional)

```bash
python -m forkling evolve --sandbox ...
```

Hot-reloads `forkling/*` modules into the running interpreter
after every successful `kind:new_file` commit. Useful for
letting the agent *use* what it just wrote in the same session.
Documented in `docs/SANDBOX.md`. **Opt-in only**; the default
is the safe disk-only baseline.

### 2.3 Reflection cycles

Every `reflect_every` generations, the LLM is asked to read the
diary + ledger and propose its own goals (`Goals.add`). These
goals steer the next generations' target files. Default: 5.

### 2.4 Family registry

`forkling family sync` pulls (read-only) the *ledgers* of
opted-in siblings. **No code merging across forks**. Sibling
substrates remain sovereign. Documented in
`docs/FAMILY_SETUP.md`.

---

## 3. Evaluation

### 3.1 Benchmarks

Frozen benchmarks live under `bench/`. Each is a JSONL manifest
plus per-task directories with `buggy.py`, `visible_tests.py`,
`held_out_tests.py`, `expected.py`. Validation procedure:
`python bench/validate_bench.py --bench <bench.jsonl>`.

| Benchmark | Status | Tasks | Calibration target (arm N pass@5) |
|---|---|---|---|
| `FORKLAND-BENCH-001.jsonl` | frozen | 10 | n/a (saturated at 0.90 — see exp003) |
| `FORKLAND-BENCH-002.jsonl` | proof-of-concept | 3 (calibration pending) | [0.2, 0.4] |
| New candidate pools | drafting | tbd | tbd |

**Naming note:** `FORKLAND` is one fork in the family (see
`FAMILY_SETUP.md`); benchmarks are family-scoped. We use
`FORKLAND-BENCH-NNN` because that's the canonical name the
running code emits. v1.0 may rename to `FORKLING-BENCH-NNN`.

### 3.2 Experiment driver

```bash
python -m forkling experiment run \
    --bench bench/FORKLAND-BENCH-002.jsonl \
    --k 10 --model qwen2.5-coder:3b --seed 20261025 \
    --arms N,P,I,R \
    --out results/exp004.json
```

Arms:
- **N** (no-iterate): K independent draws, no iteration.
- **P** (post-hoc re-rank): K independent draws, pick best by
  visible tests.
- **I** (in-loop select): iterate, keep iff visible tests pass.
- **R** (in-loop random): iterate, accept with p=0.5.

Statistical test: paired Mann–Whitney U on per-task pass@5
(exact permutation for N≤10). Alpha = 0.05. **No Bonferroni
correction** — the project has one primary comparison per
experiment.

### 3.3 Pre-registration

Every experiment file `paper/hypothesis_vN.md` freezes:

- The mechanism question (typically falsifiable, mechanism-level).
- The arms and the primary comparison.
- The benchmark and its calibration procedure (if not yet
  frozen).
- The stopping rule (typically K=10 per task per arm).
- The statistical test and alpha.

A pre-registration is *committed* before any pilot data is
viewed under its design. Pilot data is *not* allowed to
modify the pre-registration; the only exception is the
explicit model-swap clause (see `MODEL_DECISION.md` for
how this was applied in exp002).

---

## 4. Reporting

### 4.1 Result files

Single JSON per experiment: `results/exp00N.json`. Schema
includes `config`, `metrics`, `per_task_pass_at_5`, `stats`,
`records`. Re-derivable from the checkpoint JSONL
(`results/exp00N.ckpt.jsonl`) alone.

### 4.2 Result writeups

Per-experiment prose: `paper/exp00N_results.md`. Required
sections: TL;DR; pre-registered endpoint; per-task breakdown;
sanity checks; interpretation per the rules in
`hypothesis_vN.md`; reproducibility command; sign-off.

### 4.3 Dataset releases

Zip-bundled: `paper/datasets/forkling-dataset-<timestamp>-<stage>-<label>.zip`.
Contents: state-dir JSONL files + `config.yaml` snapshot +
`fitness-snapshot.json` derived metrics + `git-log-snapshot.txt`
commits. Re-derivable from the bundle alone using
`forkling/paper.py`.

### 4.4 What the schema does not promise

See `docs/SCHEMA.md` §8. Repeating here for emphasis:

- v0.1 is provisional. v1.0 will lock fields.
- SHA-256 over JSON is **not** a security primitive. The
  chain prevents accidental rewrites, not adversarial ones.

---

## 5. What is NOT in v0.1 (and why)

- **Canonical evolution targets** (the strategic-plan §1 ask).
  These need a pre-registered "fitness floor" definition.
  The current fitness function (`paper/fitness-snapshot.json`)
  computes smartness + skill as one-shot metrics; a target
  definition requires deciding what counts as an
  improvement, which is its own pre-registration.
- **Cross-fork speciation experiment** (strategic-plan §4).
  The family setup is documented but the experimental design
  for deliberate speciation has not been pre-registered.
- **Forkling-30/90/365 reference runs.** We are not at
  day 30 yet. Pretending otherwise violates the realism
  constraint.
- **Multi-environment SLOs.** Single-machine runs only.
- **Community challenge** (strategic-plan §6 b). The
  challenge is the audience *for* the protocol, not its
  precursor.

Each of these will land as its own pre-registered design.

---

## 6. Reproducibility — minimal viable setup

```bash
# 1. Clone + deps.
git clone https://github.com/nuerainc/project-forkling
cd project-forkling
pip install pytest

# 2. Pull at least one model. Default per MODEL_DECISION.md.
ollama pull qwen2.5-coder:3b

# 3. Validate the frozen benchmark.
python bench/validate_bench.py

# 4. Optional: run an experiment.
python -m forkling experiment run \
    --bench bench/FORKLAND-BENCH-001.jsonl \
    --k 10 --model qwen2.5-coder:3b --seed 20261025 \
    --arms N,P,I,R \
    --out results/repro.json

# 5. Run the evolve loop.
python -m forkling evolve --max-attempts 50 --reflect-every 5
```

Expected wall time: §9 in `paper/hypothesis_v3.md` (warm).

---

## 7. Sign-off

This document is **provisional** and **honest about being so.**
The v1.0 spec will be cut once exp004's calibration data
exists (day-of-completion), and at least one family member
(Spoonica) has a 30-day reference run. Until then, treat
this doc as a starting point, not a contract.

---

## 8. v0.2 addendum (2026-09-26): protocol 2 + validity fix

**What's wrong with v0.1 (sections 1–7).** A post-exp003 audit
([`paper/exp003_results.md` "Validity caveat"](https://github.com/nuerainc/project-forkling/blob/main/paper/exp003_results.md))
found five real problems with protocol 1 (`forkling/experiment.py`):

1. The primary endpoint (pass@k) is blind to selection: it asks
   "did *any* of the K draws pass", which is the same
   measurement for arms N and P under protocol 1, so the
   primary comparison (I vs P) cannot detect a filter.
2. The in-loop prompt always shows the original `buggy.py`,
   not the running source; after the first accepted patch most
   patches no longer apply, so the in-loop arms under-parse
   (parse_ok drops from ~0.9 to ~0.3 after attempt 0).
3. The post-hoc re-ranker was implemented as boolean
   visible_pass, so partial fixes (visible 1/2, held-out 0)
   tied with full passes (visible 2/2, held-out 0) — there
   was no rank signal for partial fixes.
4. Sub-seeds used `hash((arm, task.id))`, which Python
   randomizes per process unless `PYTHONHASHSEED` is set, so
   exp001–003 arm R coin flips are not reproducible from
   the recorded seed.
5. The "paired Mann–Whitney U" test described in
   `hypothesis_v3.md` was implemented as an unpaired
   rank-sum; for arms run on the same tasks, a paired test
   is correct. Wilcoxon signed-rank is used in protocol 2.

**Protocol 2 (`forkling/experiment2.py`)** fixes these. It is
the harness used by `scripts/run_exp004.sh` and the
pre-registered `paper/hypothesis_v4r1.md`. Concretely:

- `python -m forkling experiment run --protocol 2 ...` selects
  protocol 2; protocol 1 is kept unchanged for reproducing
  exp001–003 (do not edit `experiment.py`).
- The primary endpoint is **returned_pass**: did the patch
  each arm actually returns pass the held-out tests? S=5
  replicates per (task, arm), so per-task scores are
  {0, 0.2, …, 1.0}.
- Selection ranks by the visible-test count (a number in
  [0, n_visible]); partial fixes rank above wrong-but-parseable
  fixes.
- In-loop prompts show the *current* source and a feedback
  block from the previous attempt (patch tried, kept?, visible
  failure output, truncated to 2,000 chars).
- Sub-seeds come from `zlib.crc32(seed, arm, task, replicate)`,
  and Ollama `options` carry `temperature=0.8` and the
  derived per-call `seed` — both recorded in `config`.
- Test is exact Wilcoxon signed-rank on per-task paired
  differences with a 10,000-resample bootstrap CI; alpha =
  0.05 for the primary.
- A rule-based fallback completion (Ollama down) is recorded
  as `infra` and counted toward the timeout-abort rule, **never
  counted as model output**.

**Harness self-test gate.** Before any exp004 run,
`tests/test_experiment_power.py` must pass at the commit that
produces the data. It runs protocol 2 against three scripted
fake LLMs (filter model, amplifier model, null model) and
requires the harness to detect each (filter, amplifier, no
effect). If the self-test cannot tell them apart, the harness
cannot answer the question and exp004 does not run.

**No silent fallback in experiment mode.** If Ollama errors,
the call is recorded as infra failure; if it ever exceeds the
20%-timeout abort rule, the experiment aborts and reports as
infra failure (v4r1 §8).

**Bench gating.** `bench/validate_bench.py --strict` now fails
any candidate whose `buggy.py` passes every held-out test (this
caught the 012-wrap-text gap in the v4r1 smoke test). All 12
FORKLAND-BENCH-002 candidates pass `--strict` at sign-off.

**Where to look first.**

- The pre-registration with the actual protocol-2 design:
  [`paper/hypothesis_v4r1.md`](../paper/hypothesis_v4r1.md).
- The post-exp003 audit it cited:
  [`paper/exp003_results.md` "Validity caveat"](https://github.com/nuerainc/project-forkling/blob/main/paper/exp003_results.md).
- The harness: `forkling/experiment2.py`.
- The end-to-end runner: `scripts/run_exp004.sh`.
- The harness self-test: `tests/test_experiment_power.py`.

The end-to-end recipe lives at v4r1 §9 and is what
`scripts/run_exp004.sh` runs. Do not run protocol 1 (the
un-fixed harness) and try to interpret the result; the audit
says it cannot answer the question.
