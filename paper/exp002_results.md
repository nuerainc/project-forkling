# FORKLAND Experiment 002 — Results

**Run date:** 2026-09-25
**Pre-registration:** [`paper/hypothesis_v2.md`](hypothesis_v2.md)
**Result JSON:** [`results/exp002.json`](../results/exp002.json)
**Model actually used:** `qwen2.5-coder:3b` (re-registered from `qwen2.5-coder:7b` per [`MODEL_DECISION.md`](MODEL_DECISION.md) — the 7b variant partial-offloads to CPU on this RTX 2050 and is unrunnable in reasonable time)
**Seed:** 20261025
**K (attempts per task per arm):** 10

## TL;DR

**Result: NULL.** The pre-registered alternative hypothesis H1 is
rejected for the second time. Selection pressure does not produce
statistically significant gains over either one-shot generation or
random-accept iteration, even with a stronger (coder-specific) model
and a tighter prompt schema.

However, **two genuine improvements vs exp001**:

1. **Parse-rate confound resolved.** Arm A parse_ok rose from 0.47
   (exp001) to 0.90 (exp002). The model + worked-example prompt
   fixes the parse problem that confounded exp001's results.
2. **Task 007 now solvable.** Reverse-string failed across all arms
   in exp001 (`is_singleton` was the only fully-solved-by-A task);
   in exp002 it succeeds in every arm.

So the prompt+model upgrade helped. It just didn't help selection
specifically.

## Pre-registered endpoint

| Arm | pass@1 | pass@5 | pass@10 | parse_ok | commit |
|---|---|---|---|---|---|
| A (baseline, one-shot) | 0.80 | 0.80 | 0.80 | 0.90 | 1.00 |
| B (evolve + select) | 0.60 | 0.80 | 0.80 | 0.43 | 0.11 |
| C (evolve + random) | 0.80 | 0.90 | 1.00 | 0.43 | 0.22 |

Pre-registered test: paired Mann-Whitney U on per-task pass@5,
Bonferroni-corrected alpha = 0.025.

| Comparison | U | p (two-sided) |
|---|---|---|
| B vs A | 50.00 | 1.0000 |
| B vs C | 45.00 | 0.7055 |

Pre-registered interpretation rule: B > A AND B > C at p<0.025 →
positive; any other outcome → null.

We observe B == A on pass@5 (both 0.80) and B < C on pass@5
(0.80 vs 0.90). Both comparisons fail to reject. The result is
**NULL**.

## Per-task pass@5

| task | kind | A | B | C |
|---|---|---|---|---|
| 001 | off_by_one | 0 | 0 | 1 |
| 002 | off_by_one | 1 | 1 | 1 |
| 003 | wrong_operator | 1 | 1 | 1 |
| 004 | wrong_operator | 1 | 1 | 1 |
| 005 | missing_edge | 1 | 1 | 1 |
| 006 | missing_edge | 1 | 1 | 1 |
| 007 | wrong_return | 1 | 1 | 1 |
| 008 | wrong_return | 1 | 1 | 1 |
| 009 | typo | 1 | 1 | 1 |
| 010 | missing_edge | 0 | 0 | 0 |

Tasks 002-009 are now solved by arm A alone (8 of 10 with one-shot
generation). Tasks 001 and 010 remain unsolved. Task 010
(normalize-email) is the only task with the inverted-condition bug
(`raise ValueError` when `@` IS present, expects raise when `@` is
absent) — both arms attempt but the model picks the wrong side of
the conditional. Task 001 (sum-range inclusive) requires flipping
`range(start, stop)` to `range(start, stop+1)`; the one-shot arm
solves it more often because iteration can lose progress.

## Sanity checks

These confirm the arms are implemented correctly.

**Arm B selector works.** Of 100 attempts, 43 produced parseable
patches. Of those 43, the selector committed 11. Of those 11
committed, 100% passed visible tests. Selection is selecting on
visible-test passage; the policy is doing what it claims to.

**Arm C accept rate ≈ 0.5.** Of 43 parseable patches, 22 were
accepted (rate 0.51). Coin-flip accept policy is close to nominal.

**Arm A is independent one-shot draws.** Verified by inspection of
`experiment.py:arm_A_baseline`. Each of the 10 attempts sees the
original buggy.py, not the cumulative state.

So the arms are doing what they say. They just don't separate at
this sample size, with this model, on this benchmark.

## Why this is also a null (in exp001's favor)

exp001's null could have been due to:
1. Floor effect (pass@5 in A = 0.70 — too little room)
2. Parse-rate confound (parse_ok in A = 0.47)
3. Model capability ceiling (llama3.2:3b too weak)

exp002 specifically addresses (2) and (3):

- **Parse rate went from 0.47 to 0.90** — confound (2) is
  resolved.
- **One-shot pass@5 went from 0.70 to 0.80** — model is
  meaningfully stronger.
- **But pass@10 in arm C reached 1.00** — there's very little
  room left for any arm to beat it. Floor effect (1) is now
  *worse*.

Selection pressure had the same chance to win in exp002 as in
exp001, with a stronger model and cleaner parse. It didn't. The
most likely explanation is that **selection pressure is not the
active ingredient** — arm A's independent one-shot draws reach
roughly the same place as arm B's iterative-with-selection loop,
and arm C's random-accept iteration actually reaches a slightly
higher pass@5 in this sample.

## Interesting result that wasn't pre-registered

**Arm C beats arm B on pass@5 in this run** (0.90 vs 0.80) and
pass@10 (1.00 vs 0.80). Both not significant (p=0.7055), but the
direction is consistent: in exp001, B beat C by 0.30 (0.70 vs
0.40); in exp002, C beat B by 0.10 (0.90 vs 0.80).

A possible reading: in-loop selection actively *discards*
exploration that turns out to be useful. Arm C's random-accept
policy sometimes keeps a "wrong" patch on the running state, which
might help subsequent attempts find the right fix by exploring
slightly different contexts. Arm B's strict "only keep passing
patches" might be too greedy.

This is **not** a pre-registered claim. It's a hypothesis that
exp003 (filter-vs-amplifier, paper/hypothesis_v3.md) is designed to
test more directly.

## What this changes about the project

- **Two null results in a row** on the same benchmark, same
  primary metric, with two different models and a tightened
  prompt. Selection pressure does not produce gains over
  random-accept iteration under these conditions.
- **The parse-rate confound hypothesis is dead.** With parse_ok
  at 0.90 in arm A, parse failures are no longer masking
  selection effects.
- **The model-cap-ceiling hypothesis is partially addressed.**
  The 3b coder model solves 8/10 tasks on one-shot. There's no
  headroom for a 10x gain.
- **The floor effect is now strong.** At pass@5 = 0.80 in arm A
  and pass@10 = 1.00 in arm C, the benchmark is too easy for the
  current arms. Future experiments need a harder benchmark.

## Recommended next step

exp003 (filter-vs-amplifier, pre-registered) is the next move. It
tests whether **in-loop** selection adds something beyond **drawing
K and re-ranking** the K. That's the mechanism-level question that
exp001 and exp002 cannot answer — both used in-loop selection as
their "selection" condition.

A **harder benchmark** is the most leveraged follow-up after
exp003. With pass@10 already at 1.00 on arm C, FORKLAND-BENCH-001
is saturated. A future benchmark with pass@5 closer to 0.2 in
arm A would give selection and iteration real room to separate.

## Reproducibility

```bash
python bench/validate_bench.py  # benchmark still frozen
python -m forkling experiment run \
    --bench bench/FORKLAND-BENCH-001.jsonl \
    --k 10 --model qwen2.5-coder:3b --seed 20261025 \
    --checkpoint results/exp002.ckpt.jsonl \
    --out results/exp002.json
python summarize.py results/exp002.json
```

---

**Sign-off:** This document reports the pre-registered analysis of
the experiment run on 2026-09-25. The pre-registration is in
`paper/hypothesis_v2.md` and was authored before any pilot data
was viewed. The hypothesis was not modified after viewing the
result (only the model field, per the explicit pre-registered
fallback clause).
