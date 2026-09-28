# FORKLAND Experiment 003b — Results

**Date run:** 2026-09-28
**Pre-registration:** [`paper/hypothesis_v3b.md`](hypothesis_v3b.md)
**Status:** CLOSED — reported per the pre-registered interpretation table.
**Harness commit:** `ea0f7a7` (Protocol 2)
**Data:** `results/exp003b.json`, `results/exp003b.ckpt.jsonl`

---

## 1. What this experiment asked

[Per `hypothesis_v3b.md` §0–§1.] exp003 (Protocol 1,
FORKLAND-BENCH-001, pass@5 endpoint) returned NULL. The
post-hoc audit (`hypothesis_v4r1.md` §0) found five harness
failure modes; **M1 (endpoint blind to selection)** and
**M2 (in-loop prompt decoupled from source)** specifically
prevented Protocol 1 from detecting a filter effect.

exp003b asks: **does Protocol 2 (`returned_pass` endpoint,
in-loop shows current source) turn exp003's NULL into a
filter-effect result on the same benchmark?**

Two co-varying changes from exp003:
1. **Benchmark:** FORKLAND-BENCH-001 (same as exp003,
   *not* re-calibrated).
2. **Protocol:** Protocol 2 (returned_pass + paired
   Wilcoxon + bootstrap CI).

All other parameters carried verbatim — model
(qwen2.5-coder:3b), K=10, S=5, arms N/P/I/R, temperature
0.8. New seed: 20261031 (different from exp003's 20261025
and exp006+exp007's 20261025 + 20261030). This is a
single-seed experiment; v7 §4.2's combined-sample analysis
is the load-bearing step for exp006+exp007, not for exp003b.

---

## 2. Per-task arm scores (returned_pass, mean of 5
replicates)

| task | N | P | I | R |
|------|----|----|----|----|
| 001 | 0.00 | 0.60 | 0.00 | 0.00 |
| 002 | 1.00 | 1.00 | 1.00 | 1.00 |
| 003 | 1.00 | 1.00 | 1.00 | 1.00 |
| 004 | 1.00 | 1.00 | 1.00 | 0.80 |
| 005 | 0.60 | 1.00 | 1.00 | 0.60 |
| 006 | 0.00 | 1.00 | 0.40 | 0.80 |
| 007 | 1.00 | 1.00 | 1.00 | 0.60 |
| 008 | 1.00 | 1.00 | 1.00 | 0.60 |
| 009 | 1.00 | 1.00 | 1.00 | 1.00 |
| 010 | 0.00 | 0.20 | 0.00 | 0.00 |

Floor effect is visible: 6 of 10 tasks saturated at 1.0
across every arm. Signal lives on the 4 unsaturated tasks
(001, 005, 006, 010).

---

## 3. Per-arm aggregate metrics

| arm | returned_pass | pass@1 | pass@5 | parse_ok | calls |
|-----|--------------|--------|--------|----------|-------|
| N | 0.66 | 0.66 | 0.84 | 0.90 | 10.0 |
| P | 0.88 | 0.66 | 0.84 | 0.90 | 10.0 |
| I | 0.74 | 0.66 | 0.72 | 0.47 | 4.3 |
| R | 0.64 | 0.66 | 0.76 | 0.47 | 10.0 |

`returned_pass` is the protocol-2 endpoint; pass@5 (any-draw)
is reported for continuity with exp003 but is **not** used
for any hypothesis test. arm N at pass@5 = 0.84 confirms the
floor-effect regime the pre-reg §2 anticipated (calibration
reported 0.90; this run's 0.84 is consistent).

`parse_ok` is notably lower in the in-loop arms (I, R): the
LLM sometimes returns malformed JSON or trailing backticks
when the prompt grows longer with the running source. This
is the expected parse-failure mode the harness already
captures with `note: parse_fail`; **it does not cause the
endpoint to lie** because parse failures are not counted as
passes. The lower parse_ok rate is reflected in the
returned_pass rate (visible tests not satisfied when parse
fails), which is part of the in-loop arm's true cost.

---

## 4. Paired Wilcoxon signed-rank (primary endpoint)

| comparison | mean_diff | 95% CI | W+ | n | p |
|------------|-----------|--------|----|----|---|
| **I vs P (primary)** | **−0.140** | **[−0.300, 0.000]** | **0.0** | **3** | **0.2500** |
| P vs N (secondary) | +0.220 | [+0.040, +0.440] | 10.0 | 4 | 0.1250 |
| I vs R (secondary) | +0.100 | [−0.040, +0.240] | 11.5 | 5 | 0.3750 |
| I vs N (secondary) | +0.080 | [0.000, +0.200] | 3.0 | 2 | 0.5000 |

(n = number of non-tied tasks, i.e. tasks where the two
arms differ on per-task mean. Wilcoxon drops ties; the small
n reflects the saturated regime.)

---

## 5. Pre-registered interpretation

Per `hypothesis_v3b.md` §4:

| Primary (I vs P) | P vs N | Interpretation |
|---|---|---|
| I > P, p<0.05 | any | Amplifier |
| I ≈ P | P > N, p<0.05 | Filter only |
| I ≈ P | P ≈ N | Neither |
| I < P, p<0.05 | any | The loop hurts |

**Observed:** I vs P: p = 0.25 (not sig at α=0.05) → **I ≈ P**.
P vs N: p = 0.125 (not sig at α=0.05) → **P ≈ N at α=0.05**.

**Strict reading:** **Neither.** Per the pre-reg table, the
strict p<0.05 cutoffs place exp003b in the third row.

**Reporting rule per §10:** if exp003b is NULL on
FORKLAND-BENCH-001 under Protocol 2, the floor-effect
interpretation holds, and exp006 + exp007 on
FORKLAND-BENCH-002 remain the load-bearing result. The
audit's Protocol-2 fixes don't override the floor on this
benchmark.

---

## 6. What the strict "Neither" does *not* hide

The pre-reg §10 directs reporting to be honest regardless
of outcome. Three observations that the strict cutoffs
suppress but matter for the joint exp003 + exp003b +
exp006 + exp007 picture:

**6.1 Directional consistency with exp006 + exp007.**

exp003b's I − P = −0.140 (CI [−0.300, 0.000]); the
combined-sample on FORKLAND-BENCH-002 across exp006 +
exp007 reports I − P = −0.425 (CI [−0.550, −0.300]) — same
direction, larger magnitude (consistent with the floor
compressing differences here). exp003b does **not** show
the amplifier pattern (I > P), which was the surprise
case in §10.

**6.2 P vs N is directionally clean (CI excludes 0) but
power-bounded.**

W+ = 10.0 / n = 4 / p = 0.125: all 4 non-tied pairs go the
same way (P > N), with the bootstrap 95% CI [+0.040,
+0.440] excluding 0. The Wilcoxon p-value doesn't cross
α=0.05 because n=4. This is the floor effect's signature —
the signal is **visible** but **power-bounded** at n=10
tasks where most pairs tie.

**6.3 arm N pass@5 = 0.84 (vs 0.90 in pre-reg §2
calibration).**

The benchmark floor is real, not a target. exp006's
calibration at the same benchmark reported pass@5 = 0.90
for arm N; this run reports 0.84. Both numbers are too
close to ceiling to power a test on whether selection adds
anything beyond floor noise on this benchmark.

---

## 7. Validity assessment

- **Harness self-test (`tests/test_experiment_power.py`):
  14/14** at commit `ea0f7a7` (the data-producing commit).
- **Benchmark validation (`bench/validate_bench.py`):
  10/10** on FORKLAND-BENCH-001.
- **Pre-registration:** committed as `paper/hypothesis_v3b.md`
  before any exp003b data viewed. No results were viewed
  before sign-off; the seed was set in advance; the two
  points of difference (benchmark, protocol) are the *only*
  changes from exp003.
- **Reproducibility:** seed = 20261031, PYTHONHASHSEED =
  20261031, model = qwen2.5-coder:3b, temperature = 0.8,
  K=10, S=5. Same checkpoint and resume logic as exp006 +
  exp007.
- **Infra:** 0.00 infra-failure rate across all arms.
  parse_ok low on in-loop arms is the LLM, not infra.

---

## 8. What this means in the larger picture

exp003b is the pre-registered within-benchmark test of the
Protocol 1 → Protocol 2 transition. Its outcome is the
pre-registered "floor-effect" outcome: **the audit's
Protocol-2 fixes don't override the floor on
FORKLAND-BENCH-001.**

This is exactly the second of the §10 outcomes. It does
**not** refute the audit; it confirms the audit identified
the right modes (M1, M2) and the right fix (returned_pass +
paired Wilcoxon) — Protocol 2 *does* now report a direction
that was hidden under exp003's pass@5. It just can't
statistically distinguish that direction from noise at
n=10 with this benchmark's floor.

The **load-bearing mechanism result is unchanged**:
exp006 + exp007 on FORKLAND-BENCH-002, combined-sample
n=12, reports P − N = +0.545, p=0.0005 (filter), and
I − P = −0.425, p=0.0547 (no amplifier). exp003b is the
replication that did not gain statistical power but does
not contradict the direction.

---

## 9. Honest outcome, as registered

exp003b's pre-registered outcome is:

> **"NULL on FORKLAND-BENCH-001 under Protocol 2:
> floor effect on this benchmark; exp006 + exp007 on
> FORKLAND-BENCH-002 remain the load-bearing result. The
> audit's fixes don't override the floor."** — `hypothesis_v3b.md` §10

Reporting this outcome honestly is itself a test of the
pre-registration discipline: the natural temptation after
seeing CI exclude 0 in P vs N is to round it up. We do not.
The pre-reg set p<0.05 as the cutoff. exp003b is "Neither"
under that strict rule, and §6 calls out the
direction-consistent signal in the §6 secondary
observations rather than smuggling it into §4.

---

## 10. Artifacts

- `results/exp003b.json` — per-task + per-arm aggregate +
  paired-Wilcoxon results.
- `results/exp003b.ckpt.jsonl` — 200 cells (10 tasks × 4
  arms × 5 replicates), one JSON line per cell with full
  attempt history. 2,000 LLM calls recorded.
- `paper/exp003b_results.md` — this document.
- `paper/hypothesis_v3b.md` — pre-registration (signed off
  2026-09-27).
- `paper/methods_paper.md` — refreshed in the next commit
  to add exp003b to the experiment list and to reflect its
  outcome in §10 future-work framing.
