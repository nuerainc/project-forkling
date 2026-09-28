# FORKLAND Experiment 006 — Pre-registered Hypothesis

**Author:** Jeremy Beebe
**Date written:** 2026-09-27
**Status:** ACTIVE — no exp006 data (calibration or main) has been
collected at sign-off. `results/` contains no `exp006*` files.
**Supersedes:** None. v4r1 and v5 remain the operative
pre-registrations for exp004 and exp005 respectively. Both
exp004 and exp005 were **deferred** per their freeze rules.
This document is the *next attempt* on FORKLAND-BENCH-002, not
a correction of either prior pre-registration.
**Predecessors:**
- [hypothesis.md](hypothesis.md) — exp001, NULL
- [hypothesis_v2.md](hypothesis_v2.md) — exp002, NULL
- [hypothesis_v3.md](hypothesis_v3.md) — exp003, NULL
- [hypothesis_v4r1.md](hypothesis_v4r1.md) — exp004, **DEFERRED** (3/12 in band), [results](exp004_results.md)
- [hypothesis_v5.md](hypothesis_v5.md) — exp005, **DEFERRED** (5/24 in band), [results](exp005_results.md)
- [exp005_paths.md](exp005_paths.md) — path assessment motivating v5 and v6

---

## 0. Why this attempt, and why these specific choices

exp005's calibration on the 24-candidate Path B pool produced
5 in-band survivors (006, 008, 011, 013, 017) — one short of
the 6-survivor floor. Per hypothesis_v5 §2.4, this is a
**second deferred outcome**, not a null on the mechanism
question.

The data direction is unambiguous: **algorithm-heavy tasks
populate the band; parser-heavy tasks do not.** Path B was
empirically validated. To clear the 6-floor, the natural next
move is to **densify the algorithm-heavy share** rather than
widen the band, narrow the floor, or relax the rule. This
document is that move.

Three rejected alternatives (carried forward from
[`exp005_paths.md`](exp005_paths.md), still rejected):

- **Widening the freeze band `[0.10, 0.50]`** — discipline-bad.
  The freeze rule doing what it was built to do is not a bug.
- **Lowering the survivor floor from 6** — equally
  discipline-bad. The floor exists for a reason: a single
  in-band result does not support a meaningful comparison.
- **Tightening the band to `[0.20, 0.40]`** — also
  discipline-bad. The exponential: e ≤ 5 survivors now would
  mean even fewer, given the surviving p1 distribution.

**What v6 actually changes from v5:**

- Larger candidate pool (~32 candidates vs v5's 24).
- Higher algorithm-heavy share (~70% vs v5's ~50%).
- Same parser-retained controls (~15%, down from v5's ~25%).
- Same trivial control share (~5%).
- Same hard-impossible control share (~5%).

Everything else — question, arms, endpoint, statistical test,
freeze rule, model decision tree, harness self-test gate —
carries over verbatim from v5. This is a **path-B amplifier**,
not a parameter rewriting.

---

## 1. The question (unchanged from v5 / v4r1 / exp003)

**Is selection pressure on LLM-generated patches a *filter*
(a way to discard bad patches so the running state stays
good) or an *amplifier* (a way to make the LLM generate
*better* patches because the prompt context includes prior
attempts)?**

Operationally, with an equal budget of K LLM calls per task:

- **Filter effect:** choosing among K independent draws by
  visible tests returns a better patch than taking one draw.
  Measured by **P vs N**.
- **Amplifier effect:** iterating (each attempt sees the
  current source and the last test feedback, keep-if-better)
  returns a better patch than K independent draws plus the
  same selector. Measured by **I vs P**. **Primary.**

If I ≈ P, the evolve loop can be replaced by "draw K, re-rank".

This question has been open on no class-V evidence through
exp001/002/003 (protocol 1, three nulls) and exp004/005
(protocol 2, two deferrals). v6 is the next pre-registered
attempt.

## 2. The benchmark: FORKLAND-BENCH-002 (re-calibrated, denser)

### 2.1 Why the pool changes (again)

exp005's pool difficulty distribution (24 candidates):

| band | count | fraction |
|---|---|---|
| p1 = 0 (impossible) | 17 | 71% |
| 0.05–0.09 (just below band) | 2 | 8% |
| 0.10–0.50 (band) | 5 | 21% |
| 0.51–0.99 (above band but not trivial) | 1 | 4% |
| p1 > 0.50 trivially above band | 1 | 4% |

Of the 5 in-band survivors, **all 5 are algorithm-heavy**
(006 merge-intervals, 008 flatten, 011 search-insert, 013
binary-search, 017 rotate-array). Of the 9 algorithm-heavy
candidates in v5's pool, 5 (56%) landed in band. Of the 13
parser/retained/rec candidates, 0 (0%) landed in band.

**Projected v6 distribution** at 70% algorithm-heavy share
plus 8 new algorithm-heavy candidates (modeling per-task
band-hit probability at v5's observed 56%):

| band | count (projected) | fraction |
|---|---|---|
| p1 = 0 | 6-8 | 19-25% |
| 0.05–0.09 | 1-2 | 3-6% |
| 0.10–0.50 (band) | **10-13** | 31-41% |
| 0.51–0.99 (above band) | 1-2 | 3-6% |
| p1 > 0.50 trivially above band | 1-2 | 3-6% |

(Projected range reflects calibration noise — the model
isn't deterministic across seeds, so a 56%-band-hit rate
on algorithm-heavy tasks at K=20 should give us a ~5/9 ±3
distribution on a pool of the same size. With ~22
algorithm-heavy candidates at v6's density, we expect
10-14 in-band.)

This is a projection, not a target. The discipline forbids
tuning the pool to hit 10. We author to the §2.2
distribution; the freeze rule decides what to keep. If the
projection is wrong, the report is honest-failure.

### 2.2 Pool criteria (pre-registered)

The augmented pool is authored to the following distribution:

| Difficulty band | Approx. share | Definition |
|---|---|---|
| Algorithm-heavy | ~70% (target 22-23 tasks) | Bug class: data-structure algorithm (sort, search, balanced tree, hash table, queue, stack, graph-traversal, recursion, sliding window, two-pointer, divide-and-conquer, dynamic-programming, greedy, prefix-sum, monotonic stack, bit manipulation). Input size small enough that a 60-second pytest run is well within budget. Stdlib only; may not use `re` or `csv`. |
| Parser-retained (control contrast) | ~15% (target 4-5 tasks) | Existing FORKLAND-BENCH-002 parser candidates retained for control contrast. Specifically: 002 deep_merge, 003 word_frequencies, 004 roman_to_int, 005 rle_decode, 009 parse_duration. (001 csv, 007 brackets, 010 lru, 012 wrap-text dropped — they cluster at p1=0 with the parser class.) |
| Trivial control | ~5% (1-2 tasks) | 021 max-of-array (already at p1=0.90); add 1 new trivial task at p1 > 0.50 likely. |
| Hard-impossible control | ~5% (1-2 tasks) | 023 calc-rd, 024 sudoku-validator (already at p1=0); these are sufficient. |

**Total target:** ~32 candidates. Strict lower bound: `L ≥ 18`
(same as v5 — this is the structural floor; relaxing it would
be path-A-style discipline violation). Strict upper bound:
`L ≤ 40` (more than ~40 candidates makes the calibration
clock unforgiving).

**Per-task structure** (unchanged from v5):

- `prompt.md` — natural-language description (visible to
  agent). **No bug-name or bug-location hints.**
- `buggy.py` — buggy implementation (visible). Comments must
  not name or locate the bug.
- `visible_tests.py` — ≥ 2 tests, at least one failing on
  `buggy.py`.
- `held_out_tests.py` — ≥ 3 tests, at least one not covered
  by visible.
- `expected.py` — canonical fix (grader-only).

`bench/validate_bench.py --strict` is the gate.

### 2.3 Calibration run

Identical to v5 §2.3:

- Arm N only, K = 20 independent draws per candidate.
- Same model, sampling settings, prompt template as the main
  run, but seed `20261028` (main run uses 20261025;
  20261026, 20261027 used by exp004/exp005 calibrations
  respectively).
- Per-call seeds derived from `(seed, task, replicate, attempt)`
  via `zlib.crc32`.
- Calibration draws are **not** reused in the main experiment.

### 2.4 Freeze criteria (unchanged from v5 / v4r1)

`scripts/freeze_bench_002.py` is unchanged. It reads
`results/exp006_calibration.json` and writes
`bench/FORKLAND-BENCH-002.jsonl` (overwriting any prior
version).

Keep a candidate iff **`0.10 ≤ p1 ≤ 0.50`** and
**`parse_ok_rate ≥ 0.5`**.

- More than 10 survivors → keep the 10 with `p1` closest to
  0.30; ties broken by task id.
- Fewer than 6 survivors → exit 1 without writing the JSONL.
  The experiment does not run. Report per v5 §2.4 (third
  deferral). At that point, **the case is closed**:
  *FORKLAND-BENCH-002 with qwen2.5-coder:3b and the
  protocol-2 harness does not calibrate for the
  filter-vs-amplifier test at this scale.* That is a
  publishable finding.
- Trivial controls above band: excluded by design. Hard
  controls below band: excluded by design.

### 2.5 Calibration projection — recorded for context, not as a target

Hypothesis: at v6's pool density, the calibration will
produce 10-13 in-band survivors, comfortably above the
6-survivor floor. **This is not a target.** The freeze rule
decides whatever it decides. If the calibration produces 5
or fewer, we report the third deferral; if it produces
unexpectedly many (15+), the rule caps at 10.

---

## 3. The arms (unchanged from v5 / v4r1)

Four arms. K = 10 LLM calls per (task, arm, replicate). All
arms use the same model, sampling settings, benchmark,
visible tests, and held-out tests. Protocol-2 prompts and
feedback block are unchanged.

| Arm | What the model sees | Selection | Returned patch |
|---|---|---|---|
| N | task prompt + original `buggy.py` + visible tests | none | attempt 0 (other K-1 draws run for `pass@k` continuity) |
| P | same as N, K independent draws | after all K: most visible tests passed; tie → lowest attempt index | the winner |
| I | task prompt + **current** source + visible tests + **feedback from the previous attempt** (patch tried, kept?, visible failure output, ≤ 2,000 chars) | after each attempt: keep iff strictly more visible tests pass; stop once all visible tests pass | final current source |
| R | same prompt and feedback as I | keep parsed patch with probability 0.5; no early stop | final current source |

R shares I's prompt and feedback so **I vs R** isolates
the selector inside the loop from iteration with feedback.

## 4. Endpoint and statistics (unchanged from v5)

- **Primary endpoint:** `returned_pass` for each (task,
  arm, replicate). Mean of S=5 replicates is the per-task
  score.
- `pass@1/5/10` (any-draw) computed and reported for
  continuity, **not** used for any hypothesis test.
- **Test:** exact two-sided Wilcoxon signed-rank on
  per-task paired differences. Alpha = 0.05. **Primary
  comparison: I vs P.**
- **Effect size:** mean per-task difference with
  10,000-resample bootstrap CI; resampling seed derived
  from `(seed, comparison)`.

## 5. Hypotheses (unchanged from v5)

**H1 (primary):** mean `returned_pass(I)` ≠ mean
`returned_pass(P)`, Wilcoxon signed-rank, p < 0.05. Expected
direction: I > P.

**H0:** no difference at alpha = 0.05.

**Secondary (exploratory):** P vs N, I vs R, I vs N.

### Interpretation rules

Same as v5:

| Primary (I vs P) | P vs N | Interpretation |
|---|---|---|
| I > P, p<0.05 | any | **Amplifier.** Iteration + feedback + selection beats draw-and-rerank at equal budget. |
| I ≈ P | P > N, p<0.05 | **Filter only.** Selection helps, but only as a filter; the loop reduces to draw-and-rerank. |
| I ≈ P | P ≈ N | **Neither shows an effect.** Report calibration + visible/held-out gap before drawing conclusions. |
| I < P, p<0.05 | any | **The loop hurts.** Per-task accept histories; likely mechanism is overfitting to visible tests. |

## 6. Model decision (unchanged from v5, refined)

- **Primary model:** `qwen2.5-coder:3b`. Warm ~0.7 s/call,
  fits fully in 4 GB VRAM.
- **Model-escalation fallback:** if v6's calibration
  produces **fewer than 6 survivors** on
  `qwen2.5-coder:3b` AND ≥ 16 GB VRAM hardware is
  available, the main run uses `qwen2.5-coder:7b`
  (pre-registered per v5 §6 — same model-swap clause).
- **Sampling:** `temperature=0.8`; per-call Ollama seed
  derived from `(seed, arm, task, replicate, attempt)` via
  `zlib.crc32`; recorded in `config`. Reproducibility
  requires `PYTHONHASHSEED` and the derived Ollama seed.
- **No silent fallback.** Ollama errors record `infra`.
  Rule-based completions never returned as model output in
  experiment mode.

## 7. Harness (unchanged from v5 / v4r1)

`forkling/experiment2.py` is unchanged. All v4r1 §7 fixes
carry over:
1. Each (task, arm, replicate) stores `returned_pass`.
2. In-loop prompts show current source + feedback block.
3. Selection ranks on `visible_passed` count.
4. Deterministic sub-seeds via `zlib.crc32`.
5. Pinned sampling (temperature + per-call Ollama seed).
6. S=5 replicates.
7. Paired Wilcoxon signed-rank with exact null + bootstrap CI.
8. No rule-based fallback in experiment mode.

### Harness self-test gate

`tests/test_experiment_power.py` must pass at the commit
that produces exp006 data. 14/14 at the time of v5 sign-off
(sha `01e5d370ad4e3dcbfc2df5c6ebdcc7c806aa6cf2`). Re-run at
the commit that produces exp006 data; refused to run main
without it.

## 8. Stopping rule

- No early stopping. Calibration: 32 candidates × K=20 =
  640 calls (≤ 16 min at 3b). Main run: ≤ 10 tasks × 4
  arms × 5 replicates × 10 calls = 2,000 calls (≤ 30 min
  at 3b).
- parse_ok < 0.5 in arm N or P → prompt/harness problem.
- Timeouts + infra fallbacks > 20% of attempts in any arm
  → abort as infra failure.
- I's accepted patches never increase visible count
  (commit rate ≈ 0) → "selection had nothing to select."

## 9. Reproducibility

```bash
# 0. Harness gate.
python -m pytest -q tests/test_experiment_power.py

# 1. Validate the augmented candidate pool.
python bench/validate_bench.py --strict \
  --bench bench/benchmark_002_proof/FORKLAND-BENCH-002-candidates.jsonl

# 2. Calibration: arm N, K=20, seed 20261028.
python -m forkling experiment run --protocol 2 \
  --bench bench/benchmark_002_proof/FORKLAND-BENCH-002-candidates.jsonl \
  --k 20 --replicates 1 --temperature 0.8 \
  --model qwen2.5-coder:3b --ollama-url http://127.0.0.1:11434 \
  --seed 20261028 --arms N \
  --checkpoint results/exp006_calibration.ckpt.jsonl \
  --out results/exp006_calibration.json

# 3. Freeze.
python scripts/freeze_bench_002.py \
  --calibration results/exp006_calibration.json
python bench/validate_bench.py --strict \
  --bench bench/FORKLAND-BENCH-002.jsonl
# exit 0 -> continue. exit 1 -> third deferral.

# 4. Main run (3b on this hardware).
python -m forkling experiment run --protocol 2 \
  --bench bench/FORKLAND-BENCH-002.jsonl \
  --k 10 --replicates 5 --temperature 0.8 \
  --model qwen2.5-coder:3b --ollama-url http://127.0.0.1:11434 \
  --seed 20261025 --arms N,P,I,R \
  --checkpoint results/exp006.ckpt.jsonl \
  --out results/exp006.json
python scripts/summarize.py results/exp006.json
```

## 10. What changes from v5

| | v5 | this document (v6) |
|---|---|---|
| Question, arms, endpoint, statistics, harness gate | same | same |
| Calibration target | per-task `p1 ∈ [0.10, 0.50]` | **same — discipline preserved** |
| Calibration seed | 20261027 | **20261028** |
| Pool size | 24 | **~32** |
| Algorithm-heavy share | ~50% | **~70%** |
| Parser-retained | ~25% | **~15%** |
| Trivial controls | 1 task (021 max-of-array) | 1-2 tasks |
| Hard-impossible controls | 2 tasks (023, 024) | 2 tasks (023, 024) |
| Path-decision | n/a | Authoring *density*, not band relaxation |

## 11. Reporting

`results/exp006.json` and `paper/exp006_results.md`:
- Pool size and distribution (algorithm / parser / trivial
  / hard proportions).
- Calibration outcome (per-task `p1`, `parse_ok`, `vis_gap`).
- If freeze succeeds: primary test + effect size;
  secondaries labelled exploratory; interpretation per §5;
  whether the harness self-test passed at the commit that
  produced the data.
- If freeze fails: **third deferred outcome.** Explicit: per
  v4r1 §6 language ("Fewer than 6 survivors: stop. Report
  benchmark calibration failed; primary question deferred.
  Do not report this as a null.") At the third deferral, the
  case is closed. **The closed-case finding is itself
  publishable.**

## 12. What we are *not* doing

- **Not** widening the freeze band. Path A rejected.
- **Not** lowering the survivor floor. Discipline-bad.
- **Not** changing the mechanism question. Path D rejected.
- **Not** running any pilot on the augmented pool until this
  document is **committed** and the augmented candidates
  are authored and validated. Discipline matters more than
  cycle speed.
- **Not** authoring candidate tasks tuned to a target `p1`.
  Tasks written to the §2.2 distribution; freeze rule decides.
- **Not** citing the v5 in-band count (5/24) as a constraint
  on what v6 must produce. The discipline is v6 documents
  what it does *based on the §2.2 distribution*, not on the
  v5 result.

---

## 13. Sign-off

**Sign-off:** 2026-09-27. Pre-registered before any pilot
data viewed under this design. The hypothesis is
**falsifiable, mechanism-driven, and publishable in either
direction** — "I ≈ P" and "I > P" are both load-bearing
outcomes. The discipline carries forward from exp001–exp005:
honest reporting of calibration outcomes, deferred runs,
and mechanism nulls, in that order.

Authored in continuity with v5's protocol-2 + Path-B
re-authoring. Frozen at sign-off; changes need a new
re-registration.
