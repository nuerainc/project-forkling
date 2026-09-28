# FORKLAND Experiment 003b — Protocol-2 Re-run of exp003 (Benchmark-Change)

**Author:** Jeremy Beebe
**Date written:** 2026-09-27
**Status:** ACTIVE — no exp003b data has been collected at
sign-off. `results/` contains no `exp003b*` files.
**Supersedes:** None. The original `hypothesis_v3.md` remains
the operative pre-registration for exp003. exp003b is a
**registered replication** that switches benchmark
(FORKLAND-BENCH-001 instead of FORKLAND-BENCH-002) **and
protocol (Protocol 2 instead of Protocol 1)** relative to
exp003 — two specific points of difference; no others.
**Predecessors:**
- [hypothesis_v3.md](hypothesis_v3.md) — exp003, NULL on
  Protocol 1 + FORKLAND-BENCH-001; *audit later said this
  was uninformative*
- [exp003_results.md](exp003_results.md) — exp003 writeup
  including the "Validity caveat" audit
- [hypothesis_v4r1.md](hypothesis_v4r1.md) — Protocol 2
  spec
- [hypothesis_v7.md](hypothesis_v7.md) — combined-sample
  analysis registered as load-bearing step

---

## 0. Why this attempt

exp003 returned NULL under Protocol 1 on
FORKLAND-BENCH-001. A post-hoc audit
([`paper/hypothesis_v4r1.md` §0](../paper/hypothesis_v4r1.md))
found five real measurement-failure modes in Protocol 1.
Two of those modes apply specifically to Protocol 1's
inability to detect a selection effect:

- **M1 — endpoint blind to selection**: `pass@k` returns
  1 if *any* draw passes, identically under arms N and P.
  The primary I vs P **could not detect a filter**.
- **M2 — in-loop prompt decoupled from running source**:
  arm I prompted with the original `buggy.py` while
  patches applied to the running source.

Both modes are *fixed* in Protocol 2 (`returned_pass`
endpoint; in-loop shows the current source).

**exp003b is the pre-registered test of whether the audit's
fixes convert the exp003 NULL into a positive result on
the same benchmark.** If Protocol 2 turns exp003's NULL
into a filter-only, that's evidence the audit did real
work. If Protocol 2 *also* returns NULL on the same
benchmark, that's evidence the benchmark has a floor
effect at this scale (and v6's exp006 on FORKLAND-BENCH-002
becomes the load-bearing result instead).

**Two specific points of difference from exp003:**

1. **Benchmark:** FORKLAND-BENCH-001 (the original 10
   one-liner Python bug-fix tasks) instead of
   FORKLAND-BENCH-002. **Same tasks as exp003.**
2. **Protocol:** Protocol 2 (`forkling/experiment2.py`)
   instead of Protocol 1.

**Everything else carries over from exp003 verbatim** —
same question, same `qwen2.5-coder:3b` model, same K=10
attempts per (task, arm, replicate), same arm structure,
same stopping rule. **No new parameters are introduced.**

---

## 1. The question (carried over from exp003 / v3)

**Is selection pressure on LLM-generated patches a *filter*
or an *amplifier*?**

Primary comparison: **I vs P**. Secondary: P vs N, I vs R,
I vs N.

---

## 2. The benchmark

**FORKLAND-BENCH-001** — the original 10-task one-liner
benchmark. Tasks are listed in
[`bench/FORKLAND-BENCH-001.jsonl`](../../bench/FORKLAND-BENCH-001.jsonl).
Each task has the standard `buggy.py`, `visible_tests.py`,
`held_out_tests.py`, `expected.py`, `prompt.md`.

**No re-calibration.** The benchmark is not the protocol-2
freeze rule's territory (FORKLAND-BENCH-002 was). We use
the original exp003 benchmark unchanged. This is deliberate:
the hypothesis is whether Protocol 2 fixes exp003 on the
same data; if it does, the audit's fix is validated.

The benchmark is at the floor-effect regime exp006's
follow-up calibration confirmed (arm N pass@5 = 0.90 on
FORKLAND-BENCH-001). That's why exp003b's expected outcome
is either "Protocol 2 still NULL on this benchmark because
of floor effect" or "Protocol 2 turns it positive (filter
detected at the correct endpoint)."

---

## 3. The arms, the endpoint, statistics (Protocol 2 spec)

Carried verbatim from `hypothesis_v4r1.md` §3, §4:

- K = 10 LLM calls per (task, arm, replicate).
- S = 5 replicates per (task, arm).
- **Primary endpoint:** `returned_pass` for each (task,
  arm, replicate). Mean of 5 replicates is the per-task
  arm score.
- `pass@1/5/10` (any-draw) computed and reported for
  continuity, not used for any hypothesis test.
- Arms and prompts: protocol 2 verbatim. N (no-iterate, K
  independent draws), P (post-hoc re-rank), I (in-loop
  select with current source + feedback), R (in-loop
  random).
- **Test:** exact two-sided Wilcoxon signed-rank on
  per-task paired differences. Alpha = 0.05.
- **Effect size:** mean per-task difference with
  10,000-resample bootstrap CI.

---

## 4. Hypotheses

**H1 (primary):** mean `returned_pass(I)` ≠ mean
`returned_pass(P)`, p < 0.05. Expected direction: I > P.

**H0:** no difference at alpha = 0.05.

**Secondary:** P vs N (filter test), I vs R, I vs N.

### Interpretation rules

| Primary (I vs P) | P vs N | Interpretation |
|---|---|---|
| I > P, p<0.05 | any | Amplifier |
| I ≈ P | P > N, p<0.05 | Filter only |
| I ≈ P | P ≈ N | Neither |
| I < P, p<0.05 | any | The loop hurts |

---

## 5. Model — same as exp003

`qwen2.5-coder:3b`, temperature 0.8, per-call Ollama
seed derived from `(seed, arm, task, replicate, attempt)`
via `zlib.crc32`. Reproducibility requires
`PYTHONHASHSEED`. **Seed:** `20261031` (different from
exp003's 20261025; different from exp006's 20261025 and
exp007's 20261030). This is a single-seed experiment;
Protocol 2's combined-sample analysis (v7 §4.2) is the
load-bearing step for exp006+exp007, not for exp003b.

---

## 6. Harness and self-test

Protocol 2 (`forkling/experiment2.py`) — already shipped.
`tests/test_experiment_power.py` 14/14 must pass at the
data-producing commit. Re-verified before the run.

---

## 7. Stopping rule

- No early stopping. Main run: 10 tasks × 4 arms × 5
  replicates × 10 calls = 2,000 calls (~ 50 min on 3b).
- parse_ok < 0.5 in N or P → prompt/harness problem.
- Timeouts + infra fallbacks > 20% of attempts in any arm
  → abort as infra failure.

---

## 8. Reproducibility

```bash
# 0. Harness gate.
python -m pytest -q tests/test_experiment_power.py

# 1. Validate the frozen benchmark.
python bench/validate_bench.py
# (FORKLAND-BENCH-001 is structurally validated at forkling
# startup; --strict is the v4r1+ addition for FORKLAND-BENCH-002.)

# 2. Run exp003b.
python -m forkling experiment run --protocol 2 \
  --bench bench/FORKLAND-BENCH-001.jsonl \
  --k 10 --replicates 5 --temperature 0.8 \
  --model qwen2.5-coder:3b --ollama-url http://127.0.0.1:11434 \
  --seed 20261031 --arms N,P,I,R \
  --checkpoint results/exp003b.ckpt.jsonl \
  --out results/exp003b.json
python scripts/summarize.py results/exp003b.json
```

A variant of `scripts/run_exp004.sh` exists for FORKLAND-BENCH-001
with Protocol 2; the v3b run can be added to that script's
`--exp003b` branch.

---

## 9. What changes from exp003 and exp006

| | exp003 | exp003b (this doc) | exp006/exp007 |
|---|---|---|---|
| Hypothesis | I vs P | **same** | same |
| Benchmark | FORKLAND-BENCH-001 (10 tasks) | **same as exp003** | FORKLAND-BENCH-002 (6 tasks) |
| Endpoint | pass@5 | **returned_pass** | returned_pass |
| Protocol | 1 | **2** | 2 |
| Statistics | "Mann-Whitney U" (unpaired) | **Wilcoxon signed-rank + bootstrap CI** | same |
| K, S | K=10, S=1 | **K=10, S=5** | K=10, S=5 |
| Seed | 20261025 | **20261031** | 20261025 + 20261030 |
| Model | qwen2.5-coder:3b | **same** | same |

The two co-varying changes from exp003 are deliberate:
Protocol 2 changes are isolated to the harness. If
exp003b produces a different result from exp003, the
attribution is unambiguous — it's the audit's fixes
that moved the outcome.

---

## 10. Reporting

`results/exp003b.json` and `paper/exp003b_results.md`:
- Per-task arm scores (mean of 5 replicates), per
  comparison.
- Wilcoxon signed-rank results.
- Per-seed interpretation per §4.
- **The comparison the report centers on**: does
  Protocol 2 turn exp003's NULL into a positive
  filter-effect result on the same benchmark?

If exp003b is **filter-only** on FORKLAND-BENCH-001
under Protocol 2: the audit validated the fix. exp003
was uninformative because the endpoint was wrong; the
same underlying selection mechanism still holds.

If exp003b is **NULL on FORKLAND-BENCH-001** under
Protocol 2: floor effect on this benchmark; exp006 +
exp007 on FORKLAND-BENCH-002 remain the load-bearing
result. The audit's fixes don't override the floor.

If exp003b is **I > P on FORKLAND-BENCH-001**: surprise.
Mechanism result reverses. This would be publishable, but
the pre-registration does not assume it. Report honestly.

---

## 11. What we are *not* doing

- **Not** modifying `forkling/experiment.py` (Protocol 1).
  exp003's results are preserved.
- **Not** re-running calibration — FORKLAND-BENCH-001 is
  not the protocol-2 freeze rule's territory.
- **Not** comparing FORKLAND-BENCH-001 results with
  FORKLAND-BENCH-002 directly. They are different
  benchmarks at different calibration regimes.
  exp003b is a within-benchmark test of the Protocol 1
  → Protocol 2 transition, *not* a cross-benchmark
  comparison.
- **Not** re-registering exp003. exp003 is preserved as
  the protocol-1 record.

---

## 12. Sign-off

**Sign-off:** 2026-09-27. Pre-registered before any
exp003b data viewed. Two specific points of difference
from exp003 — **benchmark** (unchanged, FORKLAND-BENCH-001)
and **protocol** (Protocol 1 → Protocol 2). All other
parameters carried over.

The question is whether Protocol 2 turns exp003's NULL
into a filter-effect result. Reporting will be honest
regardless of outcome.
