# FORKLAND Experiment Design

**Status:** Pre-registered. See `paper/hypothesis.md` for the binding
frozen text (the canonical source of truth).

This document is the *readable* writeup. It expands the pre-registration
for humans who want to understand the design without reading a 200-line
frozen spec.

## Why this exists

Forkling can patch itself. It has a diary, a graveyard, a kernel guard,
and an evolve loop. What it does **not** have is a way to *measure*
whether all of that machinery helps.

We've run plenty of evolve sessions and observed that the agent mostly
proposes noops (no patch) or has its patches correctly rolled back by
the kernel guard. Those observations are interesting but do not answer
the question we'd need to answer to call this research:

> **Does selection pressure on agent-proposed patches improve
> downstream bug-fix performance beyond what iteration alone
> achieves?**

That question is now pre-registered. This document describes how we
intend to answer it.

## The benchmark: FORKLAND-BENCH-001

10 small Python bug-fix tasks. Each task is self-contained:

```
bench/tasks/<task-id>/
  prompt.md           # natural-language description (visible to agent)
  buggy.py            # the source the agent sees (visible)
  visible_tests.py    # tests the agent runs for selection (visible)
  held_out_tests.py   # tests the GRADER runs (NEVER visible to agent)
  expected.py         # canonical fix (grader-only)
```

Bug categories, balanced across the 10 tasks:

| Category | Tasks | Description |
|---|---|---|
| off_by_one | 001, 002 | Loop bound or slice endpoint wrong. |
| wrong_operator | 003, 004 | `is` vs `==`, `<` vs `<=`, etc. |
| missing_edge | 005, 006, 010 | Empty / None input crashes; raises on valid input. |
| wrong_return | 007, 008 | Function returns input unchanged or with the bug baked in. |
| typo | 009 | Reference to undefined name (`wrd` instead of `word`). |

The benchmark is **frozen** at this commit. `bench/validate_bench.py`
re-validates structural completeness and that every `expected.py`
passes both visible and held-out tests. CI runs this on every push.

## The arms

Three arms. All arms use the **same model**, the **same prompt
template**, the **same visible tests**, and the **same task list**.
The only difference is the policy that decides which patches become
the new state.

| Arm | Name | Policy | Iterates? |
|---|---|---|---|
| A | baseline | One-shot. K independent draws per task. | No |
| B | evolve + select | Iterate. Keep a patch iff visible tests pass. | Yes |
| C | evolve + random | Iterate. Accept each patch with probability 0.5 (regardless of test outcome). | Yes |

Arms B and C are matched on compute budget. Both perform K attempts
per task; arm B only *keeps* attempts that pass visible tests, while
arm C accepts at random. Arms A and B are matched on compute budget;
arm A draws K independent patches, arm B iterates K times.

This isolates the causal variable we care about: **selection**.

- If B > A AND B > C: **selection** helps. Iteration alone (C) is no
  better than one-shot (A). Positive result.
- If B == A: selection adds nothing over one-shot generation. Null.
- If B > A but B == C: iteration explains any gain, not selection. Null.
- If B == C: selection is indistinguishable from coin flips. Null.
- If B < A or B < C: selection hurts. Negative.

## The metric

**Primary:** `mean pass@5` across the 10 tasks. For each task and
arm, pass@5 is 1 if any of the first 5 attempts produced a patch that
passes the **held-out** tests, else 0.

**Secondary** (reported, not gated):
- `pass@1`, `pass@10`
- `commit_rate`: fraction of attempts that produced any patch at all
- `parse_ok_rate`: fraction of attempts whose JSON parsed cleanly
- per-arm sanity: arm B's `selection_rate` (must be > 0 for B to be
  selecting anything), arm C's `random_accept_rate` (must be ≈ 0.5)

## The statistical test

Paired Mann-Whitney U on per-task pass@5, two comparisons:
- B vs A: does selection beat one-shot?
- B vs C: does selection beat random-accept iteration?

Bonferroni-corrected alpha = 0.025 per comparison.

For N=10 tasks, we use the **exact** permutation distribution (no
normal approximation), implemented in `forkling/experiment.py`.

## Stopping rule

K=10 attempts per task per arm = 100 attempts per arm = 300 total
attempts at the planned budget. **No early stopping.**

If any arm fails to produce parseable JSON in more than 20% of its
attempts, the experiment is aborted and reported as null with the
failure mode documented.

## Reproducing

```bash
# 1. Validate the benchmark is frozen.
python bench/validate_bench.py

# 2. Run the experiment.
python -m forkling experiment run \
    --bench bench/FORKLAND-BENCH-001.jsonl \
    --k 10 \
    --model llama3.2:3b \
    --out results/exp001.json

# 3. Inspect results.
cat results/exp001.json | python -m json.tool | head -50
```

Wall time on llama3.2:3b at the planned budget: roughly 30–60
minutes (300 attempts × ~5–12s per call).

## What this experiment does NOT test

- **Model scaling.** This is llama3.2:3b only. A positive result
  does not imply a 7B or 70B model would benefit from selection the
  same way.
- **Self-improvement.** The fork's own self-improve loop is not in
  scope here. We are testing whether selection helps on a frozen
  bug-fix benchmark, not whether the fork gets better at patching
  itself.
- **Long-horizon evolution.** This is short-horizon (10 attempts per
  task). The day-30, day-60, day-90 evolve loops are separate.
- **Hard benchmarks.** FORKLAND-BENCH-001 is small enough for a 3B
  model to plausibly solve. SWE-bench, HumanEval+, etc., would need
  a more capable model and a different experiment.

A positive result on this experiment licenses the next one. It does
not license claims beyond it.

## Related docs

- `paper/hypothesis.md` — the binding pre-registration (frozen).
- `bench/FORKLAND-BENCH-001.jsonl` — the benchmark manifest.
- `bench/validate_bench.py` — the structural validator.
- `forkling/bench.py` — the loader and grader.
- `forkling/experiment.py` — the three-arm driver and the
  Mann-Whitney U implementation.
- `tests/test_bench.py` — the unit tests for the harness.
