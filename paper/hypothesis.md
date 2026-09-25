# FORKLAND Experiment 001 — Pre-registered Hypothesis

**Author:** Jeremy Beebe
**Date written:** 2026-09-25 (pre-registration; freeze before any pilot data is viewed)
**Status:** ACTIVE — no pilot data has been inspected under this design

---

## 1. Research question

Does selection pressure on agent-proposed patches improve downstream
bug-fix performance on a held-out test suite, beyond what iteration
alone achieves?

Concretely: when a small local LLM (llama3.2:3b) is given a buggy
Python function and asked to produce a fix, does an *evolve* loop that
keeps the first patch passing the visible tests outperform a
random-accept evolve loop with the same compute budget, which in turn
outperforms a one-shot generation baseline?

This isolates *selection* as the causal variable. Iteration is held
constant across arms B and C; the only difference is whether passing
patches are kept (B) or accepted at random (C). Arm A is the
no-iteration control.

## 2. Hypothesis

### H1 (alternative)

After N=100 attempts per arm on FORKLAND-BENCH-001 (10 tasks, 10
attempts per task), Arm B (evolve + selection) achieves a higher
mean pass@5 than Arm A (baseline) **and** higher than Arm C (random
accept), with both differences reaching p<0.05 by paired Mann–Whitney
U on per-task pass@5.

### H0 (null)

There is no difference between any pair of arms at alpha=0.05.

### Pre-registered positive result

Arm B > Arm A AND Arm B > Arm C, both at p<0.05 (Bonferroni-corrected
across the two comparisons; corrected alpha = 0.025). Means reported
with 95% bootstrap confidence intervals.

### Pre-registered null / negative results

Any other outcome is reported as null. Specifically:

- B == A (selection adds nothing over one-shot) → null
- B == C (selection adds nothing over iteration) → null
- B > A but B == C (iteration explains the gain, not selection) → null
- B < A or B < C (selection hurts) → negative

We will **not** re-define the arms, the budget, or the metric after
viewing pilot data. If the harness is broken, we fix the harness and
re-register; we do not move the goalposts on what counts as evidence.

## 3. Arms

| Arm | Name | Description | Attempts/task |
|---|---|---|---|
| A | baseline | One-shot: for each task, draw K=10 independent patches from the LLM (temperature 0.4, no iteration). | 10 |
| B | evolve + selection | For each task, iterate up to K=10 attempts. After each attempt, run visible tests. If they pass, keep the patch. If they fail, revert and try again. | 10 |
| C | evolve + random accept | For each task, iterate up to K=10 attempts. After each attempt, accept the patch with probability 0.5 (regardless of test outcome). | 10 |

All arms use the **same model** (llama3.2:3b via Ollama), the **same
prompt template**, and the **same visible tests**. The only difference
is the accept/reject policy at the end of each attempt.

All arms receive the **same prompt** — task description + buggy source
+ visible tests + the instruction "produce a JSON patch." No arm gets
extra information. Arm B's diary records which patches were kept and
why; Arm C's diary records accept/reject outcomes per attempt.

## 4. Primary metric

`pass@k` per task: did at least one of the first k attempts produce a
patch that passes the **held-out** tests? Reported as the per-task
binary; aggregated as mean across the 10 tasks.

Primary endpoint: **mean pass@5** across the 10 tasks, per arm.

Secondary endpoints (reported but not gated on):
- `pass@1`, `pass@10`
- `commit_rate`: fraction of attempts that produced any patch at all
  (not noop)
- `selection_rate_arm_B`: fraction of Arm B attempts that passed
  visible tests (sanity check that selection has anything to select)
- `random_accept_rate_arm_C`: actual fraction accepted (should be ≈0.5)

## 5. Statistical test

Paired Mann–Whitney U on per-task pass@5, two comparisons (B vs A, B
vs C). Bonferroni-corrected alpha = 0.025 per comparison.

Why paired: the 10 tasks are the same across arms. The pairing is the
task; each task contributes one (0 or 1) data point per arm, and we
compare the per-task deltas.

Why Mann–Whitney U instead of paired t: pass@5 is a Bernoulli per
task; with N=10 tasks we cannot assume normality. U is exact for small
N and does not require it.

Why not paired permutation test: more powerful in principle, but
N=10 means we cannot reliably estimate the null distribution. U is
conservative and well-defined.

## 6. Stopping rule

Run each arm for K=10 attempts per task, 10 tasks = 100 attempts per
arm, 300 attempts total. **No early stopping.**

Pre-registered decision: if any arm fails to complete (e.g., the LLM
times out repeatedly), report the failure as a result, do not impute
or retry. If more than 20% of attempts in any arm fail to produce a
patch (LLM error, malformed JSON), the experiment is aborted and
reported as null with the failure mode documented.

## 7. The benchmark

**FORKLAND-BENCH-001** — 10 small Python bug-fix tasks. Each task is
self-contained:

```
bench/tasks/<task_id>/
  prompt.md           # natural-language description (visible)
  buggy.py            # the source the agent sees (visible)
  visible_tests.py    # pytest tests the agent runs for selection
  held_out_tests.py   # pytest tests the grader runs (NEVER visible)
  expected.py         # canonical fix (grader only; never visible)
```

The agent sees only `prompt.md`, `buggy.py`, and `visible_tests.py`.
The grader runs both test files against the agent's patch and reports
held-out pass/fail.

Bug types, balanced across the 10 tasks:
- off-by-one (2 tasks)
- wrong operator (`==` vs `is`, `<` vs `<=`) (2 tasks)
- missing edge case (empty / None) (2 tasks)
- wrong return value (2 tasks)
- typo / wrong variable name (2 tasks)

Each task is independently authored and frozen in the repository at
this commit. Tasks are not modified after pre-registration.

## 8. What this experiment does NOT test

- Whether *more capable* models do better (this is llama3.2:3b only).
- Whether the substrate's *self-improvement* loop produces better
  downstream tasks (we are testing bug-fix, not meta-evolution).
- Whether selection pressure scales with task difficulty.
- Long-horizon (months-scale) evolution.

These are out of scope by design. A positive result on this
experiment licenses the next one; it does not license claims beyond
it.

## 9. Reproducibility

- Model: `llama3.2:3b` via local Ollama at `127.0.0.1:11434`
- Seed: numpy + random seeded per attempt with `attempt_index * 7919`
- Code: pinned to the commit that introduced this file
- Run command: `python -m forkling experiment run --arms A,B,C --bench bench/FORKLAND-BENCH-001.jsonl --per-task 10 --out results/exp001.json`
- Compute budget: ~100 LLM calls per arm × 3 arms = 300 calls; on
  llama3.2:3b this is roughly 30–60 minutes wall time.

## 10. Reporting

A single result file `results/exp001.json` containing per-attempt
records, per-task pass@k, arm means, the U statistic, the p-value,
and the pre-registered interpretation. Written before any
post-hoc analysis is performed.

---

**Sign-off:** This document is frozen at the commit that introduced
it. Any change to arms, budget, metric, or stopping rule requires a
new commit and a re-registration note appended below.

(End of pre-registration.)
