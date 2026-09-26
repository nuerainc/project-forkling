# FORKLAND Experiment 001 — Results

**Run date:** 2026-09-25
**Pre-registration:** `paper/hypothesis.md` (commit at hypothesis authoring)
**Hypothesis:** `paper/hypothesis.md`
**Result JSON:** `results/exp001.json`

## TL;DR

**Result: NULL.** Pre-registered alternative hypothesis H1 is rejected.
Selection pressure does not produce statistically significant gains over
either one-shot generation or random-accept iteration at the planned
budget (K=10 attempts per task per arm, 10 tasks, 300 LLM calls,
llama3.2:3b).

We report this honestly because that is what the pre-registration
requires. The arms DID behave as designed (sanity checks pass) — they
just did not separate.

## Pre-registered endpoint

| Arm | pass@1 | pass@5 | pass@10 | parse_ok | commit |
|---|---|---|---|---|---|
| A (baseline, one-shot) | 0.20 | 0.70 | 0.80 | 0.47 | 1.00 |
| B (evolve + select) | 0.30 | 0.70 | 0.80 | 0.21 | 0.08 |
| C (evolve + random) | 0.40 | 0.40 | 0.50 | 0.18 | 0.10 |

Pre-registered test: paired Mann-Whitney U on per-task pass@5,
Bonferroni-corrected alpha = 0.025.

| Comparison | U | p (two-sided) |
|---|---|---|
| B vs A | 50.00 | 1.0000 |
| B vs C | 35.00 | 0.2568 |

Pre-registered interpretation rule:
- B > A AND B > C at p<0.025 → positive
- any other outcome → null

We observe B == A on pass@5 (both 0.70) and B > C on pass@5 (0.70 vs
0.40) but p=0.26, which is not significant under the pre-registered
alpha. The result is **NULL**.

## Per-task pass@5

| task | kind | A | B | C |
|---|---|---|---|---|
| 001 | off_by_one | 1 | 0 | 0 |
| 002 | off_by_one | 1 | 1 | 1 |
| 003 | wrong_operator | 1 | 1 | 1 |
| 004 | wrong_operator | 1 | 1 | 0 |
| 005 | missing_edge | 1 | 1 | 1 |
| 006 | missing_edge | 0 | 1 | 0 |
| 007 | wrong_return | 0 | 0 | 0 |
| 008 | wrong_return | 1 | 1 | 0 |
| 009 | typo | 1 | 1 | 1 |
| 010 | missing_edge | 0 | 0 | 0 |

Two tasks failed across all arms: 007 (reverse-string) and 010
(normalize-email). Three tasks passed across all arms: 002, 003,
005, 009. The interesting rows are 001, 004, 006, 008 — they
disagree across arms in ways that hint at noise rather than signal
(task 001 is solved by A but not B/C; task 008 is solved by A and B
but not C).

## Sanity checks

These confirm the arms were implemented correctly:

**Arm B selector works.** Of 100 attempts, 21 produced parseable
patches. Of those 21, the selector committed 8. Of those 8 committed,
100% passed visible tests. The selector is selecting on visible-test
passage — the policy is doing what it claims to.

**Arm C accept rate ≈ 0.5.** Of 18 parseable patches, 10 were
accepted (0.56). Coin-flip accept policy is close to nominal.

**Arm A is independent one-shot draws.** Each of the 10 attempts
sees the original buggy.py (not the cumulative state). Verified by
inspection of `experiment.py:arm_A_baseline`.

So the arms are doing what they say. They just don't separate at this
sample size, with this model, on this benchmark.

## Why null is plausible

Several features of the run could explain the null result:

1. **Floor effect.** pass@5 in arm A is already 0.70. With 7/10
   tasks solved by 5 independent one-shot draws, there is little room
   for selection or iteration to improve.

2. **Parse-rate confound.** Only 47/100 attempts in arm A produced
   parseable JSON; 21/100 in arm B; 18/100 in arm C. Arms B and C
   "iterate," but with parse-ok rates below 25%, most iterations
   don't actually produce a candidate. The effective attempt count
   for arms B and C is closer to 21 and 18 than to 100.

3. **Small n.** 10 tasks is the pre-registered budget, but the
   exact permutation test is conservative at this n. The
   directionally-positive B-vs-C result (p=0.26) is consistent with
   either "no effect" or "effect exists but is small relative to
   n=10 noise."

4. **Model capability ceiling.** llama3.2:3b may not be capable
   enough to generate patches that *would* benefit from selection
   pressure. A 7B or 70B model might produce a wider distribution of
   patch qualities, making selection meaningful.

5. **Tasks too easy.** Tasks where one-shot is already solving 7/10
   leave only 3 tasks where any method can differentiate. Not much
   room for separation.

## What this changes about the project

The pre-registration said: "any other outcome is reported as null.
Specifically … B == A (selection adds nothing over one-shot) → null."
We got B == A on the pre-registered metric. So the project now has:

- **A reproducible experiment harness.** The infrastructure survives
  the result, so future experiments (different model, harder
  benchmark, longer budget) can run on the same code.
- **A frozen benchmark.** `bench/FORKLAND-BENCH-001` remains useful
  for future arms or future models, even if this specific result was
  null.
- **A honest null.** This is a publishable result if the rest of the
  paper is solid. Null results on pre-registered hypotheses are
  exactly what the scientific process is supposed to produce.

## What to try next (NOT pre-registered, future work)

These would be follow-up experiments, each requiring its own
pre-registration:

- **Harder benchmark.** FORKLAND-BENCH-001 may be too easy. A
  harder benchmark (e.g., SWE-bench-Lite subset) with pass@5 floor
  closer to 0.2 in arm A would give more room for arms to separate.
- **Stronger model.** qwen2.5-coder:7b is currently 500-erroring on
  this machine; once that's diagnosed, re-running with it would test
  whether the null is a function of model weakness.
- **Longer budget.** K=20 or K=50 attempts per arm would give more
  room for selection to compound.
- **Tighter parse prompt.** A prompt that produces parseable JSON
  90%+ of the time would remove the parse-rate confound.
- **Quality-ranked selection.** Instead of pass/fail on visible
  tests, rank patches by held-out-test-likelihood proxy. More
  expressive selection than a binary accept/reject.

## Reproducibility

```bash
python bench/validate_bench.py
python -m forkling experiment run \
    --bench bench/FORKLAND-BENCH-001.jsonl \
    --k 10 --model llama3.2:3b --seed 20260925 \
    --out results/exp001.json
python scripts/summarize.py results/exp001.json
```

The result JSON contains per-attempt records (raw LLM response,
parse_ok, visible_pass, held_out_pass, committed), arm-level metrics,
and the Mann-Whitney U statistics.

---

**Sign-off:** This document reports the pre-registered analysis of
the experiment run on 2026-09-25. The pre-registration is in
`paper/hypothesis.md` and was authored before any pilot data was
viewed under this design. The hypothesis was not modified after
viewing the result.
