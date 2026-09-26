# FORKLAND Experiment 003 — Results

**Run date:** 2026-09-26
**Pre-registration:** [`paper/hypothesis_v3.md`](hypothesis_v3.md)
**Result JSON:** [`results/exp003.json`](../results/exp003.json)
**Model:** `qwen2.5-coder:3b` (per [`MODEL_DECISION.md`](MODEL_DECISION.md))
**Seed:** 20261025
**K (attempts per task per arm):** 10
**Arms:** N (no-iterate), P (post-hoc re-rank), I (in-loop select), R (in-loop random)

## TL;DR

**Result: NULL.** The pre-registered primary comparison (I vs P,
in-loop select vs post-hoc re-rank) does not separate:
`pass@5(I) = 0.80` vs `pass@5(P) = 0.90`, `U=45.00, p=0.7055`.
Direction is I < P (in-loop selection slightly *worse* than
post-hoc re-rank). Not significant.

The single most informative finding: **P == N (identical, U=50,
p=1.0)**. Re-ranking K independent draws on this benchmark gives
the *exact same* pass@5 as taking the first hit. The re-rank step
adds zero information. Either the model is so reliable at this
task that any K-shot is sufficient, or the re-rank signal
(visible-test score) is too coarse to discriminate among the
candidates.

This is the cleanest mechanistic result yet:
- The "evolve loop" paradigm (in-loop select) does not beat
  "draw N and re-rank" (post-hoc) at this scale on this
  benchmark.
- Re-ranking adds nothing over "just draw K" at this scale.

> **Addendum (2026-09-26, after the analysis below was signed off):**
> a harness audit found that this null does not bear on the
> filter-vs-amplifier question. See [Validity caveat](#validity-caveat).
> The pre-registered result stands as reported; its mechanism-level
> interpretation does not.

## Pre-registered endpoint

| Arm | pass@1 | pass@5 | pass@10 | parse_ok | commit |
|---|---|---|---|---|---|
| N (no-iterate) | 0.70 | 0.90 | 0.90 | 0.90 | 1.00 |
| P (post-hoc re-rank) | 0.60 | **0.90** | 1.00 | 0.88 | 0.10 |
| I (in-loop select) | 0.80 | 0.80 | 0.80 | 0.40 | 0.11 |
| R (in-loop random) | 0.70 | 0.80 | 0.80 | 0.36 | 0.19 |

Pre-registered test: paired Mann-Whitney U on per-task pass@5,
alpha = 0.05 (no Bonferroni because the question has one primary
comparison).

| Comparison | U | p (two-sided) |
|---|---|---|
| **I vs P** (primary) | 45.00 | 0.7055 |
| I vs N (secondary) | 45.00 | 0.7055 |
| I vs R (secondary) | 50.00 | 1.0000 |
| P vs N (secondary) | 50.00 | 1.0000 |

**Pre-registered interpretation rule:** I > P at p<0.05 → positive
(selection is an amplifier). Otherwise null.

We observe **I < P** with p=0.7055. Direction is wrong-signed,
not significant. Result is **NULL**.

## Per-task pass@5

| task | kind | N | P | I | R |
|---|---|---|---|---|---|
| 001 | off_by_one | 1 | 1 | 0 | 0 |
| 002 | off_by_one | 1 | 1 | 1 | 1 |
| 003 | wrong_operator | 1 | 1 | 1 | 1 |
| 004 | wrong_operator | 1 | 1 | 1 | 1 |
| 005 | missing_edge | 1 | 1 | 1 | 1 |
| 006 | missing_edge | 1 | 1 | 1 | 1 |
| 007 | wrong_return | 1 | 1 | 1 | 1 |
| 008 | wrong_return | 1 | 1 | 1 | 1 |
| 009 | typo | 1 | 1 | 1 | 1 |
| 010 | missing_edge | 0 | 0 | 0 | 0 |

Only task 001 differs across arms: N and P solve it, I and R do
not. Both N and P use independent draws (so they get K=10 chances
to hit task 001 fresh); I and R iterate (so once they fail on 001
they're working off the failed state). This is consistent with
**floor-effect saturation** — once one or two independent draws
hit, more attempts add nothing.

## Sanity checks

- **Arm N:** parse_ok 90/100 (90%). Each attempt is independent;
  every parseable candidate is "committed" by convention.
- **Arm P:** parse_ok 88/100 (88%), 10 commits (one per task).
  Post-hoc ranker picked exactly one patch per task whenever any
  parseable candidate existed.
- **Arm I selector works:** 40/100 parse_ok, 11 committed, 11/11
  passed visible tests. The selector is genuinely selecting on
  visible-test passage.
- **Arm R accept rate ≈ 0.5:** 36/100 parse_ok, 19 committed
  (rate 0.53). Coin-flip policy works as designed.

## The mechanism-level answer (pre-registered question)

The pre-registration asked: **is selection a filter or an
amplifier?** Three data points answer:

1. **I == R on pass@5** (0.80 vs 0.80, p=1.0). Selection with
   visible-test passage is indistinguishable from random accept.
   If selection were an amplifier (signal amplification), it
   would beat random-accept iteration.
2. **I < P** on pass@5 (0.80 vs 0.90, p=0.7, direction wrong).
   In-loop selection is slightly *worse* than re-ranking K
   independent draws. If selection were a useful filter, re-rank
   would be at least as good as in-loop.
3. **P == N** on pass@5 (0.90 vs 0.90, p=1.0). Re-ranking K
   independent draws gives identical pass@5 to drawing K and
   reporting the first hit. The re-rank step adds nothing.

Together: **selection is neither an amplifier nor a useful
filter at this scale.** Both forms of selection (in-loop and
post-hoc) match or underperform no-selection.

## Why this is consistent with the prior two nulls

exp001 (B == A on pass@5), exp002 (B == A on pass@5), exp003
(I == R, I < P, P == N): same conclusion from different angles.
Selection pressure on LLM-generated patches does not help on
FORKLAND-BENCH-001 with `qwen2.5-coder:3b` at K=10.

The floor effect (pass@5 = 0.90 in arm N, the strongest
non-iterate condition) is the most likely explanation. With
K=10 independent draws and a 90%-solvable benchmark, one-shot
generation hits the ceiling before iteration or re-ranking can
add anything. **The benchmark needs to be harder** for the
selection hypothesis to get a fair test.

## Recommended next step

Run the same three-arm comparison (N/P/I/R) on
**`bench/benchmark_002_proof/`** (currently 3 sample tasks).
FORKLAND-BENCH-002 is designed with the calibration target
`arm A pass@5 ∈ [0.2, 0.4]` — leaving real headroom for
selection or iteration to demonstrate an effect.

If exp004 (FORFLAND-BENCH-002) also returns NULL on the I vs P
comparison, the case is closed: selection pressure does not help
on bug-fix benchmarks at this scale, with this model. The result
is publishable.

If exp004 returns positive (I > P), then exp001/002/003 were
floor-effect false negatives, and the real contribution is the
harder benchmark + the I vs P mechanism.

## What this changes about the project

- **Three pre-registered nulls in a row.** All on the same
  benchmark. The hypothesis "selection pressure helps on
  FORKLAND-BENCH-001" is now empirically falsified.
- **The mechanism question is answered for this benchmark:**
  selection is not an amplifier AND not a useful filter.
- **Next experiment MUST be on a harder benchmark** to give the
  selection hypothesis a fair test. FORKLAND-BENCH-002 (in
  proof-of-concept stage) is the right next step.

## Validity caveat

*Added 2026-09-26 after a read-through of `forkling/experiment.py`
and the raw records in `results/exp003.json`. Nothing above was
changed except the two arm P cells marked "(recompute)", now filled
from the records by `scripts/summarize.py`.*

The pre-registered test was run as written and is null. But three
properties of the harness mean exp003 could not have detected
either a filter or an amplifier effect, so the mechanism-level
conclusions above ("selection is neither an amplifier nor a useful
filter") are **not supported** by this experiment. The same issues
apply to exp001 and exp002.

**1. The endpoint is blind to selection.** `pass_at_k`
(`forkling/experiment.py`) returns 1 if *any* of the first k
records passed held-out tests, regardless of `committed`. Arm P's
re-ranker only sets `committed`, so P's pass@k is the pass@k of K
independent draws: the same quantity as arm N, measured on a
different sample. "P == N" is true by construction, not a finding.
For the in-loop arms the selector likewise never affects pass@k
directly; it only changes the source that later patches apply to
(see 2).

**2. The in-loop arms never see their own state.** `build_prompt`
always shows the model the *original* `buggy.py`, while arms I and
R apply each patch to the *current* (evolved) source. Once a patch
is accepted, later patches usually quote an `old` string that no
longer exists and fail to apply, which is recorded as
`parse_fail`. parse_ok by attempt index, summed over the 10 tasks:

| Arm | attempt 0 | attempts 1-9 (mean) |
|---|---|---|
| N | 9 | 9.0 |
| P | 9 | 8.8 |
| I | 9 | 3.4 |
| R | 9 | 3.0 |

All four arms start identically; only the arms that iterate
collapse. The prompt also never includes previous attempts or test
output, so there is no channel through which an "amplifier" could
work. The I-vs-P comparison therefore contrasts a loop that mostly
cannot apply its own patches with an endpoint that ignores
re-ranking.

**3. Ceiling.** Arm N pass@5 = 0.90 leaves one task of headroom
out of ten. Even a correct harness would have had almost no power.
(`hypothesis_v4.md` addresses this one only.)

**Exploratory, not pre-registered:** the held-out pass rate of the
patch each arm would actually return (N: first attempt; P: the
re-ranker's winner; I/R: the last committed patch, else the
unfixed file) is N 0.70, P 0.70, I 0.70, R 0.50. This is the
quantity a filter-vs-amplifier question needs, and it does not
separate the arms either, but with 10 tasks near ceiling it has
little power.

**Also noted:** the `metrics` block in `results/exp003.json` is
keyed A/B/C. `compute_metrics` hardcodes those letters and the
N/I/R arm functions are aliases that label their records A/B/C, so
`metrics.A/B/C` are really N/I/R and P is absent. `per_task_pass_at_5`
and `stats` use the correct letters.

**Consequence for exp004:** a harder benchmark alone
(`hypothesis_v4.md`) would reproduce issues 1 and 2. exp004 is
re-registered in [`hypothesis_v4r1.md`](hypothesis_v4r1.md) with a
selection-sensitive endpoint, a loop that sees its own state and
feedback, and the calibrated benchmark.

## Reproducibility

```bash
python bench/validate_bench.py
python -m forkling experiment run \
    --bench bench/FORKLAND-BENCH-001.jsonl \
    --k 10 --model qwen2.5-coder:3b --seed 20261025 \
    --arms N,P,I,R \
    --checkpoint results/exp003.ckpt.jsonl \
    --out results/exp003.json
python scripts/summarize.py results/exp003.json
```

---

**Sign-off:** This document reports the pre-registered analysis of
the experiment run on 2026-09-26. The pre-registration is in
`paper/hypothesis_v3.md` and was authored before any pilot data
was viewed. The hypothesis was not modified after viewing the
result (only the model field, per the explicit pre-registered
fallback clause).
