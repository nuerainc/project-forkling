# FORKLAND Experiment 009 — Third-Seed Replication + Combined-Sample Update

**Date:** 2026-09-28
**Pre-registration:** [`paper/hypothesis_v9.md`](hypothesis_v9.md)
**Result JSON:** [`results/exp009_seed20261104_temp0.8.json`](../results/exp009_seed20261104_temp0.8.json)
**Combined-sample output:** [`results/exp009_combined_sample.json`](../results/exp009_combined_sample.json)
**Combined-sample script:** [`scripts/combined_sample_analysis.py`](../scripts/combined_sample_analysis.py)

---

## TL;DR

**exp009a** ran the third seed (20261104) of the FORKLAND-BENCH-002
mechanism experiment at temp = 0.8 (matching exp006 / exp007). It
clean-exited (`rc = 0`) with no infra failures across any arm.

**Per-seed result (n = 6 tasks):**

| comparison | exp009a mean [CI] | p |
|---|---|---|
| **P vs N (filter)** | +0.500 [+0.333, +0.667] | **0.0312** |
| I vs P (loop vs pick-and-rerank) | −0.200 [−0.367, −0.067] | 0.1250 |
| I vs R | +0.300 [+0.100, +0.533] | 0.1250 |
| I vs N | +0.300 [+0.100, +0.533] | 0.1250 |

**P > N** is significant on this seed alone. **I vs P** matches the
direction of exp006/exp007 (I < P, loop is worse than pick-and-rerank)
but is not significant alone — underpowered at n = 4 non-zero pairs.

---

## Combined-sample analysis: exp006 + exp007 + exp009a (n = 18 per-task pairs)

Per `scripts/combined_sample_analysis.py` with `--sign-test --out
results/exp009_combined_sample.json`:

| comparison | combined_n | n_nz | W+ | mean(non-zero) | 95% CI | **p** | Δ vs n=12 |
|---|---|---|---|---|---|---|---|
| **P vs N (filter)** | 18 | 17 | 153.0 | **+0.529** | [+0.412, +0.647] | **0.0003** | was 0.0005 (n=12) — **stronger** |
| **I vs P (loop vs rerank)** | 18 | 12 | 0.0 | **−0.383** | [−0.500, −0.283] | **0.0249** | was 0.0547 (n=12) — **now significant** |
| I vs R | 18 | 14 | 96.0 | +0.371 | [+0.200, +0.557] | 0.0002 | was 0.0029 (n=12) — **stronger** |
| I vs N | 18 | 10 | 55.0 | +0.440 | [+0.320, +0.560] | 0.0010 | was 0.0156 (n=12) — **stronger** |

**Sign test across the three seed-cells** (per-cell mean P − N):
3 / 3 positive. Exact binomial two-sided p = 0.25 (n = 3 is too
small to be load-bearing; the per-task Wilcoxon above is the
registered primary).

---

## Interpretation (per v9 §5 + v6/v7 §5 rule)

The pre-registered v6/v7 §5 rule was:

> "I ≈ P at p ≥ 0.05" **AND** "P > N at p < 0.05" → "Filter only.
> Selection helps, but only as a filter; the loop reduces to
> draw-and-rerank."

**After exp009a (n = 18):**

- **P > N is now p = 0.0003** — overwhelmingly significant. The
  filter effect is confirmed on three independent seeds.
- **I vs P is now p = 0.0249** — significant, with **W+ = 0.0**
  (every non-zero paired difference was negative). The loop's
  iterative variant is **worse** than pick-and-rerank at the same
  compute budget, not merely equivalent.

The combined-sample evidence now supports a **stronger** version of
the v6/v7 interpretation:

> **Filter only — and the loop's iteration actively hurts.**
> Selection helps as a filter (P > N at p = 0.0003). But the
> in-loop iterative refinement (I arm) is worse than a flat
> draw-and-rerank at the same draw budget (I − P = −0.383,
> p = 0.0249). The loop reduces to "draw many, pick best" — the
> iteration inside the loop costs parses without adding
> selection value.

This is the load-bearing empirical conclusion of the methods
paper, now triple-seed-confirmed.

---

## Why the loop hurts (mechanism, post-hoc)

exp009a arm-I terminates early on average (`calls = 6.5` vs arm-P
`calls = 10.0`); the loop's stop-condition fires before consuming
the full draw budget. The early answer is sometimes right
(`parse_ok = 0.70`, `returned_pass = 0.53`), but **arm-P's full-budget
re-rank finds more** (`parse_ok = 0.92`, `returned_pass = 0.73`).
So the loop is essentially performing pick-and-rerank at step 1
*some of the time*, and stopping there — leaving signal on the
table for the cases where a later draw would have been better.

This is a hypothesis about *why* I < P, not a pre-registered
secondary. It should not be reported as a finding; it should
appear only in the discussion section of the methods paper as
a plausible mechanism that future work should test.

---

## Per-task breakdown (3 seeds × 6 tasks = 18 paired obs)

```
exp006 (seed 20261025):
  006: P-N=+0.20, I-P=-0.20, I-R=+0.40, I-N=+0.00
  008: P-N=+0.40, I-P=-0.40, I-R=+0.00, I-N=+0.00
  011: P-N=+0.80, I-P=-0.80, I-R=+0.20, I-N=+0.00
  012: P-N=+0.20, I-P=+0.00, I-R=+0.60, I-N=+0.20
  013: P-N=+0.20, I-P=-0.20, I-R=+0.00, I-N=+0.00
  017: P-N=+1.00, I-P=-0.40, I-R=+0.20, I-N=+0.60

exp007 (seed 20261030):
  006: P-N=+0.80, I-P=-0.40, I-R=+0.20, I-N=+0.40
  008: P-N=+0.60, I-P=-0.60, I-R=-0.20, I-N=+0.00
  011: P-N=+0.60, I-P=+0.00, I-R=+1.00, I-N=+0.60
  012: P-N=+0.60, I-P=-0.40, I-R=+0.40, I-N=+0.20
  013: P-N=+0.00, I-P=+0.00, I-R=-0.20, I-N=+0.00
  017: P-N=+0.60, I-P=+0.00, I-R=+0.80, I-N=+0.60

exp009a (seed 20261104, temp 0.8):
  006: P-N=+0.60, I-P=-0.20, I-R=+0.40, I-N=+0.40
  008: P-N=+0.60, I-P=-0.60, I-R=+0.00, I-N=+0.00
  011: P-N=+0.60, I-P=-0.20, I-R=+0.40, I-N=+0.40
  012: P-N=+0.20, I-P=+0.00, I-R=+0.20, I-N=+0.20
  013: P-N=+0.20, I-P=-0.20, I-R=+0.00, I-N=+0.00
  017: P-N=+0.80, I-P=+0.00, I-R=+0.80, I-N=+0.80
```

**Every task in every seed has P − N ≥ 0** (17 of 18 positive, one
zero). **Every task with a non-zero I − P** is negative (12 of 12).
The direction is **uniform** across seeds and tasks.

---

## Reproducing these numbers

```bash
python scripts/combined_sample_analysis.py \
    --sign-test \
    --out results/exp009_combined_sample.json \
    results/exp006.json \
    results/exp007.json \
    results/exp009_seed20261104_temp0.8.json
```

To re-run exp009a alone (on the same seed + temperature, ~90 min on
the 4 GB VRAM box):

```bash
python scripts/run_smart_detached.py \
    --heartbeat results/exp009a.heartbeat \
    --pid       results/exp009a.pid \
    --log       results/exp009a.log \
    --ckpt      results/exp009_seed20261104_temp0.8.ckpt.jsonl \
    --marker    results/exp009_seed20261104_temp0.8.json \
    --interval  10 \
    --ollama-url http://127.0.0.1:11434 \
    -- PYTHONHASHSEED=20261104 \
       python -m forkling experiment run --protocol 2 ...
```

(Full CLI flags per `scripts/run_smart_detached.py --help` and the
exp009 launch command captured in `results/exp009a.log`.)

---

## What's next

Per the v9 pre-reg §6 stopping rule (n ≥ 12 + ≥ 1 confirmation),
exp009a satisfies the closure conditions for the third-seed
replication. The methods paper §1.5 / §3 / §9 should now cite the
n = 18 combined-sample result as the headline empirical claim:

> Across three independent seeds (20261025, 20261030, 20261104),
> the FORKLAND-BENCH-002 protocol shows selection helps as a
> filter (P − N = +0.529, p = 0.0003) but the in-loop iterative
> variant underperforms flat draw-and-rerank (I − P = −0.383,
> p = 0.0249). The loop reduces to "draw many, pick best"; the
> iteration inside the loop is wasted compute.

`exp009b-lowT` (seed 20261105, temp = 0.5) and `exp009b-highT`
(seed 20261106, temp = 1.0) are queued under hypothesis_v9 to
test temperature sensitivity of the filter effect.
