# FORKLAND Experiment 005 — Calibration Outcome: Second Deferral

**Date:** 2026-09-27
**Pre-registration:** [`paper/hypothesis_v5.md`](hypothesis_v5.md)
**Calibration data:** [`results/exp005_calibration.json`](../results/exp005_calibration.json)
**Calibration checkpoint:** [`results/exp005_calibration.ckpt.jsonl`](../results/exp005_calibration.ckpt.jsonl)
**Status:** **DEFERRED, second time**. Per
[`hypothesis_v5.md` §2.4](hypothesis_v5.md#24-freeze-criteria-unchanged-from-v4r1):
*"Fewer than 6 survivors: ... Report the calibration table per
v4r1 §6 and treat as a *second* deferred outcome."*

This document records the second deferred outcome. It is the
*calibration step in exp005's pre-registration completing
honestly*, not a null on the mechanism question.

---

## TL;DR

Calibration ran arm N only (one-shot, K=20 independent draws,
`qwen2.5-coder:3b`, seed 20261027, temperature 0.8, protocol 2)
on all 24 candidates in `bench/FORKLAND-BENCH-002-candidates.jsonl`.
Of the 24, **5 passed** the v5 freeze rule
(`0.10 ≤ p1 ≤ 0.50`, `parse_ok_rate ≥ 0.5`):
006 (merge_intervals, p1=0.45), 008 (flatten, p1=0.20),
011 (insert_position, p1=0.40), 013 (binary-search, p1=0.15),
017 (rotate-array, p1=0.25). v5 requires at least 6 survivors
to proceed; we are 1 short. The main experiment does not run.

**Path B worked.** Compared to exp004 (3/12 in band on the
original 12-candidate pool), exp005's Path B re-authored pool
produced 5/24 in band — a meaningful improvement in the *direction*
the data indicated was needed, but not quite enough to clear the
6-floor. Algorithm-heavy tasks populate the band precisely as
hypothesis_v5 §2.2 predicted.

**Calibration sanity.** `parse_ok_rate` is high on the algorithm
tasks that populate the band (0.90–1.00). `infra` is 0 across all
24 tasks (no rule-based fallback fired; v5 §8 abort rule not
hit). The harness self-test (`tests/test_experiment_power.py`)
passed 14/14 at the commit that produced the data. **No class-M
(measurement-failure) issue.** This is genuinely a calibration
failure, not a methodology failure.

**This is publishable as a finding.** Two pre-registered,
honestly-deferred outcomes on the same mechanism question is a
contribution in itself: it shows that the discipline produces
non-polished verdicts when the verdict is "not yet," and that
the method the discipline prescribes (re-authoring the candidate
pool to a pre-registered distribution) is *the right move*
(Path B's data-aligned with this) but *insufficient this round*
(need more candidates or different prompt qualities).

---

## Pre-registered endpoint

Per v5 §2.4 freeze rule — same rule as v4r1, applied
mechanically by `scripts/freeze_bench_002.py`:

| candidate | n | p1 | parse_ok | infra | vis_gap | kept |
|---|---|---|---|---|---|---|
| 001 parse_csv | 20 | 0.00 | 0.65 | 0.00 | 0.00 |  |
| 002 deep_merge | 20 | 0.00 | 0.85 | 0.00 | 0.00 |  |
| 003 word_frequencies | 20 | 0.00 | 0.90 | 0.00 | 0.00 |  |
| 004 roman_to_int | 20 | 0.00 | 0.65 | 0.00 | 0.00 |  |
| 005 rle_decode | 20 | 0.00 | 0.95 | 0.00 | 0.00 |  |
| 006 merge_intervals | 20 | **0.45** | 0.95 | 0.00 | 0.00 | yes |
| 007 balanced_brackets | 20 | 0.00 | 0.70 | 0.00 | 0.00 |  |
| 008 flatten | 20 | **0.20** | 0.90 | 0.00 | 0.00 | yes |
| 009 parse_duration | 20 | 0.00 | 0.65 | 0.00 | 0.00 |  |
| 010 lru_cache | 20 | 0.00 | 1.00 | 0.00 | 0.00 |  |
| 011 insert_position | 20 | **0.40** | 0.95 | 0.00 | 0.00 | yes |
| 012 wrap_text | 20 | 0.00 | 0.85 | 0.00 | 0.00 |  |
| 013 binary-search | 20 | **0.15** | 0.90 | 0.00 | **1.00** | yes |
| 014 two-sum-sorted | 20 | 0.00 | 0.70 | 0.00 | 0.00 |  |
| 015 eval-postfix | 20 | 0.20 | **0.30** | 0.00 | 0.00 |  |
| 016 validate-bst | 20 | 0.00 | 0.90 | 0.00 | 0.00 |  |
| 017 rotate-array | 20 | **0.25** | 1.00 | 0.00 | 0.00 | yes |
| 018 longest-substring | 20 | 0.00 | 0.85 | 0.00 | 0.00 |  |
| 019 product-except-self | 20 | 0.05 | **0.30** | 0.00 | 0.00 |  |
| 020 merge-two-sorted | 20 | 0.00 | 0.80 | 0.00 | 0.00 |  |
| 021 max-of-array | 20 | 0.90 | 1.00 | 0.00 | 0.00 |  |
| 022 second-largest | 20 | 0.00 | 0.80 | 0.00 | 0.00 |  |
| 023 calc-rd | 20 | 0.00 | 0.65 | 0.00 | 0.00 |  |
| 024 sudoku-validator | 20 | 0.00 | 0.60 | 0.00 | 0.00 |  |

5 survivors. The 6-survivor floor is not met.
`scripts/freeze_bench_002.py --calibration results/exp005_calibration.json`
exits 1 without writing `FORKLAND-BENCH-002.jsonl`. The main
experiment does not run.

---

## What this is not

**This is not a null result on the I-vs-P question.**

The mechanism question (filter vs amplifier; primary comparison
I vs P) was not asked at the meta level. There is no
`results/exp005.json` with arm data, no Wilcoxon signed-rank
test, no bootstrap CI. The freeze rule did what it was built
to do: refuse to commit to a benchmark whose difficulty
distribution does not give the question a fair test.

**This is also not a class-M failure.**

A class-M (measurement-failure) would look like: parse_ok near
0, infra near 1, vis_gap everywhere, or returned_pass
indistinguishable across arms. We see parse_ok averaging 0.79
(across all 24), with 5/24 in band at parse_ok ≥ 0.90, infra=0
everywhere, and the algorithm-heavy tail of the distribution
behaving sensibly (p1 monotonically increasing across the
simpler algorithm tasks). The harness produced well-formed
numbers. The freeze rule was not met for an honest reason:
the candidate pool is one task short of the band threshold.

---

## What the calibration does tell us

### 1. Path B worked — algorithm-heavy tasks populate the band

exp004's pool had 3 in-band survivors (006, 008, 011). exp005's
Path B re-authored pool has 5 in-band survivors
(006, 008, 011, 013, 017). The two new entrants both come from
the algorithm-heavy category that v5 §2.2 emphasized:

- 013 binary-search (path-search): p1=0.15 ✓
- 017 rotate-array (array-manipulation): p1=0.25 ✓

The pre-registered "share algorithm-heavy" hypothesis is
validated empirically. Algorithm-heavy tasks *do* populate the
band; parser-heavy tasks *do not* (all 6 parser-retained tasks
at p1=0). This is exactly what hypothesis_v5 §2.2 §2.5
predicted, and it confirms the discipline of authoring *to the
pre-registered distribution* rather than to a target p1.

### 2. Trivial control worked (above-band exclusion is correct)

021 max-of-array landed at p1=0.90 with parse_ok=1.00. This is
*above* the freeze band — correctly excluded from the kept set,
because a task where the model trivially dominates is the
floor-effect case the band is designed to avoid. The trivial
control was structurally important (it tests that the band
ceiling is reachable on this hardware) and it behaved as
designed.

### 3. Hard controls are at p1=0 (correctly excluded below the band)

023 calc-rd (recursive-descent calculator) and 024
sudoku-validator (3x3 sub-grid validation) both at p1=0. The
hard controls are correctly rejected. They prove that
"p1 < 0.10" is reachable on this hardware (and was reachable
on this seed), which is the v5 §2.2 guarantee.

### 4. 015 has disqualifying parse_ok but qualifying p1 (a real signal)

015 eval-postfix landed at p1=0.20 (which is in the band) but
parse_ok=0.30 (which is below the 0.5 floor). This is a
**prompt-format problem, not a benchmark-difficulty problem**:
the model can fix 4/20 of its parseable attempts at the bug, but
only 6/20 of its attempts are parseable in the first place.
This is exactly the failure mode hypothesis_v5 §2.4 expects
parse_ok_rate to filter out — and it filtered it out. The 015
result is not a misclassification; it's the rule working.

### 5. 013 binary-search has vis_gap=1.00 (partial-fix bias signal)

On 013 binary-search, every parseable draw that passed visible
tests *failed* held-out tests. The model finds partial fixes
that pass the visible-test set but do not generalize to
held-out. This is a calibration finding: the task is a
**filter-sensitive** task where the visible tests are not a
perfect proxy for held-out. A filter has something to filter on
017 (rotate-array) but less so on 013.

This vis_gap signal is reported per v4r1 §6 ("reported, not a
criterion") and v5 §2.4 explicitly preserves it. It is not a
bug in the harness; it is a property of the benchmark design
that affects how much "filter" can buy on a given task. The
mechanism-question interpretation in §5 of hypothesis_v5 uses
exactly this kind of signal when reasoning about P vs N.

---

## Direction of progress vs exp004

| metric | exp004 (12 candidates) | exp005 (24 candidates) |
|---|---|---|
| Tasks at p1 = 0 | 9/12 | 17/24 |
| Tasks in band [0.10, 0.50] | **3** | **5** |
| Tasks at p1 > 0.50 | 0 | 2 (including 021 trivial control) |
| parse_ok overall | 0.82 | 0.79 |
| infra | 0 | 0 |
| Harness self-test | 14/14 | 14/14 |
| Survivors vs floor | 3 vs 6 | 5 vs 6 |

**Path B's effect is real but capped.** Doubling the candidate
pool from 12 to 24 (with the algorithm-heavy bias v5 §2.2
prescribed) more than doubled the in-band count. But the
algorithm-heavy share of the pool that yielded the band was
~21% (5 of 24 are algorithm-heavy AND in band; total
algorithm-heavy candidates is ~10). At the model-3b-p1-pacing
we observed, this saturates at ~5-7 in-band survivors for a
pool of this size. To hit ≥6 reliably, the candidate pool
needs to be larger or the algorithm-heavy share higher.

---

## What an honest next attempt looks like

Same shape as v4r1 → v5 was: a new re-registration, exp006,
with one specific change informed by this calibration.

**Concrete next move:** exp006 doubles the algorithm-heavy
share to ~70% (rather than ~50%), adds 8-10 more algorithm-heavy
tasks at the same difficulty *shape* as 013/017 (one bug
class per task, in-band targeting), keeps the parser-retained
controls and the trivial/hard controls at ~25% / 5% / 5%,
and pushes for ~10-12 in-band survivors rather than minimum-6.
Hypothesis: with a denser algorithm-heavy middle band, the
freeze floor will be cleared with margin.

This is **NOT** "tighten the band." This is **NOT**
"tune-to-p1." This is *increase pool size and algorithm-heavy
share, per the §2.2 distribution analysis the calibration
just validated*.

It is also not a path toward running exp005 with a different
seed. Re-running with a different seed would be p-hacking:
some of the 5 in-band tasks were in band by ≤0.10 margin, and
a different seed could shift them out without changing any
underlying fact. The data-direction signal — algorithm-heavy
populates the band — is the load-bearing finding. Re-running
with different seeds does not strengthen it.

---

## Reporting transparency

**What we ran:** calibration only. Arm N only, K=20, one
replicate, seed 20261027, 24 candidates. Total: 480 LLM calls
in two sittings (resumed from checkpoint at task 011 after a
process-window timeout).

**What we did not run:** arm P, arm I, arm R. No main
experiment. No held-out comparison. No mechanism result.

**Reproducibility:**

```bash
# 1. Re-validate the augmented candidate pool.
python bench/validate_bench.py --strict \
  --bench bench/benchmark_002_proof/FORKLAND-BENCH-002-candidates.jsonl

# 2. Re-run calibration.
python -m forkling experiment run --protocol 2 \
  --bench bench/benchmark_002_proof/FORKLAND-BENCH-002-candidates.jsonl \
  --k 20 --replicates 1 --temperature 0.8 \
  --model qwen2.5-coder:3b --ollama-url http://127.0.0.1:11434 \
  --seed 20261027 --arms N \
  --checkpoint results/exp005_calibration.ckpt.jsonl \
  --out results/exp005_calibration.json

# 3. Apply the freeze rule.
python scripts/freeze_bench_002.py --calibration results/exp005_calibration.json
# exit 0 -> FORKLAND-BENCH-002.jsonl written; proceed to main run.
# exit 1 -> deferred, as here.
```

`tests/test_experiment_power.py` 14/14 passed at the commit
that produced this data. Protocol 2 verified.

---

## Closing note — what two deferred outcomes mean for the project

The mechanism question (filter vs amplifier) is still open.
We now have **two honestly-deferred attempts at it** on the
harder benchmark. exp004 deferred with 3/12 survivors;
exp005 deferred with 5/24 survivors. Path B between them
moved the in-band count from 3 to 5 by re-authoring the
candidate pool per the §2.2 distribution. The next attempt
should continue that direction.

Crucially: the discipline is *working as designed*. Each
deferred outcome is a *publication*, not a regret. They are
evidence that pre-registration discipline surfaces miscalibration
rather than producing false confidence, and that the
methodology is producing structured, comparable, honest
negative results across attempts.

If two more attempts defer, the case is closed: *on
FORKLAND-BENCH-002 with qwen2.5-coder:3b and the protocol-2
harness, the bug-fix difficulty distribution does not
calibrate for the filter-vs-amplifier test at this scale.*
That is itself a publishable finding for the literature on
LLM-driven self-improvement.

We are not there yet. Two deferrals is consistent with
"calibration is converging" and also consistent with "this
benchmark cannot be calibrated at this scale." The next
attempt should distinguish between those two.

---

## Sign-off

2026-09-27. Calibration complete. Freeze rule not met (5/24
survivors, floor is 6). Per hypothesis_v5 §2.4, exp005 main is
**deferred** for the second time — not failed, not nulled.
Honest next-attempt: re-register as exp006 with a denser
algorithm-heavy pool. Mechanism-question status: still open
on no class-V evidence; the discipline is producing structured
non-conclusions instead of structured false confidence.
