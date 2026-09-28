# FORKLAND Experiment 007 — Pre-registered Hypothesis (Seed-Replication)

**Author:** Jeremy Beebe
**Date written:** 2026-09-27
**Status:** ACTIVE — no exp007 data has been collected at
sign-off. `results/` contains no `exp007*` files.
**Supersedes:** None. v4r1, v5, v6 remain operative for
exp004, exp005, exp006 respectively. exp007 is
a *replication* of exp006, not a re-registration.
**Predecessors:**
- [hypothesis_v6.md](hypothesis_v6.md) — exp006, **MECHANISM RESULT — filter only**
- [exp006_results.md](exp006_results.md)
- [hypothesis_v4r1.md](hypothesis_v4r1.md) — exp004, DEFERRED
- [hypothesis_v5.md](hypothesis_v5.md) — exp005, DEFERRED

---

## 0. Why this attempt

exp006 reported that on a calibration-frozen benchmark
(6 tasks, p1 ∈ [0.10, 0.50], `qwen2.5-coder:3b`, K = 10,
S = 5 replicates), the pre-registered mechanism question
("is selection pressure on LLM-generated patches a filter
or an amplifier?") is answered as **"filter only."**

The headline numbers:
- P > N (filter): +0.467, 95% CI [+0.233, +0.733],
  **p = 0.0312** (significant at α = 0.05).
- I vs P (amplifier): −0.333, 95% CI [−0.533, −0.167],
  p = 0.0625 (marginal, n = 5, CI excludes 0).

The case that was open across exp001–005 is now closed on
the data we have. But the data are from **a single seed
(20261025), a single model (qwen2.5-coder:3b), a single
benchmark (FORKLAND-BENCH-002), six tasks.** Reviewers will
correctly ask "did you replicate?"

This document registers the replication. It is a
*pre-registered seed-replication* — same benchmark, same
model, same arms, same statistics, same primary, same
pre-registered interpretation rules — at a different seed.

### Why a seed-replication, not a benchmark-change or model-change

A benchmark-change replication (FORFLAND-BENCH-001 with
protocol 2, the `exp003b` slot in `scripts/run_exp004.sh`)
would conflate the "filter-only result" claim with "the
FORKLAND-BENCH-002 result transfers across to a different
benchmark." That's two questions at once. We'll get there
later; this study does not.

A model-change replication (qwen2.5-coder:7b, or another
coder) would test "is filter-only a property of this model?"
That's also a useful question, but it's contingent on
hardware: per `MODEL_DECISION.md`, qwen2.5-coder:7b
partial-offloads on 4 GB VRAM and runs at 5–6 s/call (vs
0.7 s for 3b). The pre-registered model-swap fallback in
hypothesis_v6 §6 sets the bar for invoking 7b at "≥16 GB VRAM
hardware available" — which we do not have. So model-change
is closed for the foreseeable 4 GB-VRAM future.

A seed-replication is the right next step. It tests "is
filter-only stochastically stable across seeds on this exact
artifact?" — the most natural kind of replication, with no
new confounds introduced. If filter-only holds at the new
seed, the claim is reinforced. If it doesn't, we learn
"filter-only was a seed-specific false confidence" and the
mechanism case reopens with a clear diagnosis.

---

## 1. The question (unchanged from v6)

**Is selection pressure on LLM-generated patches a *filter*
or an *amplifier*?**

**Primary comparison (unchanged): I vs P**. P vs N is the
secondary filter test. I vs R and I vs N are exploratory
secondaries.

---

## 2. The benchmark (unchanged from v6)

`bench/FORKLAND-BENCH-002.jsonl` — the SAME frozen manifest
written by `scripts/freeze_bench_002.py --calibration
results/exp006_calibration.json` during exp006. It is not
re-derived for exp007; the freeze was committed at
`a201e78` and the JSONL is stable.

6 tasks: 006 merge-intervals, 008 flatten, 011
insert-position, 012 wrap-text, 013 binary-search, 017
rotate-array. Each passes `bench/validate_bench.py
--strict`. No re-validation needed; the manifest is part of
the artifact family.

### Calibration — not re-run

Per v6 §2.4, the calibration step committed the manifest.
For v7 (a seed-replication of an already-frozen benchmark),
**calibration is intentionally not re-run**. The
discipline would be to re-run if the benchmark were not
frozen or if we were modifying the manifest. We are doing
neither.

This is consistent with v6 §2.3 ("calibration draws are
not reused in the main experiment") — the calibration is
for *manifest freezing*; it is not part of the mechanism
test.

---

## 3. The arms (unchanged from v6)

Four arms. K = 10 LLM calls per (task, arm, replicate).
All arms use the same `qwen2.5-coder:3b` model, sampling
settings, benchmark, visible tests, and held-out tests.

N, P, I, R descriptions carry over from v6 §3 verbatim.

---

## 4. The endpoint and statistics (unchanged from v6)

- **Primary endpoint:** `returned_pass` for each (task,
  arm, replicate). Mean of S = 5 replicates per task per
  arm.
- `pass@1/5/10` (any-draw) computed and reported for
  continuity.
- **Test:** exact two-sided Wilcoxon signed-rank on
  per-task paired differences. Alpha = 0.05.
- **Effect size:** mean per-task difference with
  10,000-resample bootstrap CI; resampling seed derived
  from `(seed, comparison_name)`.

### 4.1 The replication test

The replication test is **the same** Wilcoxon signed-rank
test as v6, on the same per-task paired differences:
- **Primary:** I vs P — does the filter-only finding
  replicate at seed 20261030?
- **Secondary:** P vs N — does the filter effect replicate
  at seed 20261030?

**Pre-registered interpretation of the replication test.**

If exp007's primary p < 0.05 in the same direction as
exp006 (P > N significant; I ≈ P or I < P at marginal α),
combined with exp006's results — **replication**.
Strengthens the paper's headline to "filter-only on
FORKLAND-BENCH-002 across two seeds."

If exp007's primary p ≥ 0.05 — **inconclusive** (n = 6
is small; power is bounded). Combined with exp006's
p = 0.031 for P vs N — the filter-effect replication is
inconclusive and exp006 remains the load-bearing
demonstration. **The headline claim is unchanged but
the strength is reduced** — "filter-only reproducible at
n = 6 with a single-seed demonstration; replication
study at additional seed is required for broader claims."

If exp007's primary p < 0.05 in the **opposite** direction
(P < N — filter effect *reverses* in this seed) — **failure
to replicate**. The headline claim becomes "exp006's
filter-effect finding is seed-sensitive; the seed at
which replication was attempted shows P < N." The
mechanism case re-opens. **Honest third-cycle**. The
discipline requires reporting this without re-registering
to fit.

### 4.2 Combined-sample analysis (registered secondary)

In addition to the per-seed tests, a **combined-sample**
analysis pools exp006 and exp007's per-task arm scores
(per-task means over S replicates within each seed,
treating seed as a paired block) and runs Wilcoxon on
the combined n=12 (6 tasks × 2 seeds) per-task paired
differences.

This registered secondary analysis is what the methods
paper's §4 will report. The pre-registered primary test
*remains* the per-seed test (§4.1). The combined-sample
analysis is a meta-step that does *not* invalidate the
per-seed tests.

---

## 5. Hypotheses (unchanged from v6)

**H1 (primary):** mean `returned_pass(I)` ≠ mean
`returned_pass(P)`, Wilcoxon signed-rank, p < 0.05. Expected
direction (not a one-sided test): I > P.

**H0:** no difference at alpha = 0.05.

**Secondary (exploratory):** P vs N, I vs R, I vs N.

### Interpretation rules

Same as v6:

| Primary (I vs P) | P vs N | Interpretation |
|---|---|---|
| I > P, p<0.05 | any | Amplifier |
| I ≈ P | P > N, p<0.05 | **Filter only** (the v6 row) |
| I ≈ P | P ≈ N | Neither |
| I < P, p<0.05 | any | The loop hurts |

---

## 6. Model decision (unchanged from v6)

`qwen2.5-coder:3b`. Warm ~0.7 s/call. No model-swap
fallback (the calibration-frozen benchmark is held; the
test is exactly *stochastic stability of the v6
result on the same artifact*, which does not require a
model swap to falsify).

Sampling: `temperature=0.8`; per-call Ollama seed
derived from `(seed, arm, task, replicate, attempt)` via
`zlib.crc32`; recorded in `config`. **The new seed
20261030 — different from exp006's seed 20261025** — is
the single point of difference from v6.

No silent fallback. Ollama errors record `infra`.

---

## 7. Harness (unchanged from v6)

`forkling/experiment2.py` (Protocol 2). All v4r1 §7 fixes
carry over without modification. **The harness self-test
gate must pass at the commit that produces exp007 data.**

`tests/test_experiment_power.py` 14/14 verified at v6
sign-off commit `de746a0`; re-verified before any
exp007 run.

---

## 8. Stopping rule

- No early stopping. Main run size: 6 tasks × 4 arms ×
  5 replicates × 10 calls = 1,200 calls (≤ 30 min on 3b).
- parse_ok < 0.5 in arm N or P → prompt/harness problem;
  report and do not interpret the primary.
- Timeouts + infra fallbacks > 20% of attempts in any arm
  → abort as infra failure.
- I's accepted patches never increase the visible count
  → "selection had nothing to select."

---

## 9. Reproducibility

```bash
# 0. Harness gate.
python -m pytest -q tests/test_experiment_power.py

# 1. Validate the frozen benchmark.
python bench/validate_bench.py --strict --bench bench/FORKLAND-BENCH-002.jsonl

# 2. Main run (seed 20261030 — different from v6's 20261025).
python -m forkling experiment run --protocol 2 \
  --bench bench/FORKLAND-BENCH-002.jsonl \
  --k 10 --replicates 5 --temperature 0.8 \
  --model qwen2.5-coder:3b --ollama-url http://127.0.0.1:11434 \
  --seed 20261030 --arms N,P,I,R \
  --checkpoint results/exp007.ckpt.jsonl \
  --out results/exp007.json
python scripts/summarize.py results/exp007.json
```

The calibration step is **deliberately absent**. Calibration
committed the manifest at `a201e78`; exp007 uses that
manifest as the artifact.

---

## 10. What changes from v6

| | v6 | this document (v7) |
|---|---|---|
| Question, arms, endpoint, statistics, harness gate | same | same |
| Calibration seed | 20261028 | **not run** |
| Calibration step | runs arm N at K=20 on the augmented pool | **deliberately omitted** — manifest already frozen |
| Main seed | 20261025 | **20261030** |
| Pool augmentation | densified to 33 candidates | **same** (no new candidates) |
| Combined-sample analysis | n/a | **registered as secondary** (pool exp006 + exp007) |

---

## 11. Reporting

`results/exp007.json` and `paper/exp007_results.md`:
- Per-seed Wilcoxon signed-rank results.
- Combined-sample analysis (n = 12) as a registered
  secondary.
- Per-seed interpretation per §4.1.
- **Replication outcome** — explicitly framed per §4.1
  (replicates / inconclusive / failure-to-replicate),
  not as a "the case closed further" overclaim.
- Whether the harness self-test passed at the data-
  producing commit.

---

## 12. What we are *not* doing

- **Not** running calibration. The manifest is frozen.
- **Not** authoring new candidate tasks. The pool is
  fixed.
- **Not** changing the question. The mechanism question
  is preserved.
- **Not** running a model change. Hardware constraint.
- **Not** tuning the seed to fit. The seed is
  pre-registered and called out as the only difference
  from v6.

---

## 13. Sign-off

**Sign-off:** 2026-09-27. Pre-registered before any pilot
data viewed under this design. The hypothesis is **a
clean seed-replication of exp006**; the test is the
same Wilcoxon signed-rank on the same per-task paired
differences, at a different seed.

The mechanism question is still "filter only" by v6's
data. v7 tests whether that result is stochastically
stable across seeds. Either way — replicates, fails to
replicate, or inconclusive — the discipline is the same:
committed pre-registration, four honest outcome
framings in §4.1, combined-sample test registered as
secondary, the test itself is the result.
