# FORKLAND Experiment 004 — Re-registration (r1)

**Author:** Jeremy Beebe (draft prepared with Claude Code)
**Date written:** 2026-09-26
**Status:** DRAFT. Becomes binding when a maintainer signs off below
and commits. No exp004 data (calibration or main) has been collected;
`results/` contains no `exp004*` files at the time of writing.
**Supersedes:** [hypothesis_v4.md](hypothesis_v4.md), before any data
was collected under it. `hypothesis_v4.md` is left unedited as the
record of what was originally registered.
**Predecessors:**
- [hypothesis.md](hypothesis.md) — exp001, NULL, [results](exp001_results.md)
- [hypothesis_v2.md](hypothesis_v2.md) — exp002, NULL, [results](exp002_results.md)
- [hypothesis_v3.md](hypothesis_v3.md) — exp003, NULL, [results](exp003_results.md), [validity caveat](exp003_results.md#validity-caveat)

---

## 0. Why re-register

`hypothesis_v4.md` explains the exp003 null as either "selection
doesn't help" (A) or "floor effect" (B), and fixes B by moving to a
harder benchmark. An audit of the harness after exp003 (see the
[validity caveat](exp003_results.md#validity-caveat)) found a third
explanation that a harder benchmark does not fix:

1. **The endpoint is blind to selection.** pass@k is 1 if any of
   the first k draws passes held-out tests, whether or not the arm
   selected it. `hypothesis_v4.md` §7 keeps this definition and
   says so explicitly ("the post-processing only affects commit").
   Under it, arm P is the same measurement as arm N, and the primary
   comparison I vs P cannot detect a filter.
2. **The in-loop arms cannot iterate.** The prompt always shows the
   original `buggy.py` while patches are applied to the evolved
   source, so after the first accepted patch most patches no longer
   apply (exp003 in-loop parse_ok: 0.9 at attempt 0, about 0.3
   afterwards; N and P stay at 0.9). The prompt also never shows
   earlier attempts or test output, so there is no channel for
   amplification.
3. **The re-ranker was inverted.** exp003's arm P committed the
   *lowest*-scoring candidate whenever one failed the visible tests
   (see the caveat, point 4); v4 reuses it unchanged.
4. **The v4 freeze rule is not computable as written.** §3 step 4
   targets "`arm N pass@5 ∈ [0.2, 0.4]` per task", but per-task
   pass@5 is 0 or 1.

`hypothesis_v4.md` says "If the harness is broken, we fix the harness
and re-register; we do not move goalposts." This document does that.
The question, arms, model, seed and benchmark strategy carry over.
The endpoint, the in-loop prompt, the statistics and the calibration
rule change, and a harness self-test is added as a gate.

## 1. The question (unchanged)

**Is selection pressure on LLM-generated patches a *filter* or an
*amplifier*?**

Operationally, with an equal budget of K LLM calls per task:

- **Filter effect:** choosing among K independent draws by visible
  tests returns a better patch than taking one draw.
  Measured by **P vs N**.
- **Amplifier effect:** iterating (each attempt sees the current
  source and the last test feedback, keep-if-better) returns a better
  patch than K independent draws plus the same selector.
  Measured by **I vs P**. This is the primary comparison, as in
  exp003 and v4.

If I ≈ P, the evolve loop can be replaced by "draw K, re-rank".

## 2. Arms

Budget K = 10 LLM calls per (task, arm, replicate). All arms use the
same model, sampling settings, benchmark, visible tests and held-out
tests.

| Arm | Name | What the model sees | Selection | Returned patch |
|---|---|---|---|---|
| N | one-shot | task prompt + original `buggy.py` + visible tests | none | attempt 0 (the other K−1 draws are still run for pass@k continuity) |
| P | post-hoc re-rank | same as N, K independent draws | after all K: most visible tests passed; tie → lowest attempt index | the winner |
| I | in-loop select | task prompt + **current** source + visible tests + **feedback from the previous attempt** (the patch tried, whether it was kept, and the visible-test failure output, truncated to 2,000 characters) | after each attempt: keep iff it passes **strictly more** visible tests than the current source; stop early once all visible tests pass | final current source |
| R | in-loop random | identical prompt and feedback to I | after each attempt: keep with probability 0.5, regardless of tests; no early stop | final current source |

"Visible tests passed" is a count of passing test functions, not the
boolean `visible_pass`, so P and I can rank partial fixes. A patch
that fails to parse or apply counts as "not kept" and uses one call.
The unfixed `buggy.py` is the starting point for I and R and is what
they return if nothing is kept.

R shares I's prompt and feedback, so **I vs R** isolates the selector
inside the loop from iteration with feedback.

## 3. Endpoint

**Primary endpoint: returned-patch pass rate.** For each (task, arm,
replicate), `returned_pass` = 1 if the returned patch passes all
held-out tests. The per-task score for an arm is the mean over S
replicates.

pass@1/5/10 (any-draw, as in exp001–003) is still computed and
reported for continuity, but it is **not** used for any hypothesis
test.

## 4. Replicates and statistics

- **S = 5 replicates** per (task, arm), each with its own derived
  seed, so every per-task score takes values in {0, 0.2, …, 1.0}.
  This addresses the 0/1 per-task scores that gave exp001–003 almost
  no power.
- **Test:** exact two-sided Wilcoxon signed-rank test on per-task
  paired differences (tasks are the paired unit; zero differences
  are dropped; ties in |difference| use mid-ranks and an exact
  permutation null). Alpha = 0.05 for the primary comparison. (The
  v3/v4 test was described as "paired Mann–Whitney U", but
  `mann_whitney_u` is an unpaired rank-sum test; with every arm run
  on the same tasks, a paired test is the correct one.)
- **Effect size:** the mean per-task difference with a 95% bootstrap
  CI (10,000 resamples over tasks, seed 20261025). Report it
  whatever the p-value.

With n = 10 tasks, the smallest attainable two-sided p is 0.002, so
a consistent effect is detectable. If fewer than 6 tasks have a
non-zero I−P difference, report the primary result as "insufficient
separation" rather than as a null.

## 5. Hypotheses

**H1 (primary):** mean returned_pass(I) ≠ mean returned_pass(P),
Wilcoxon signed-rank, p < 0.05. The expected direction (not a
one-sided test) is I > P.

**H0:** no difference at alpha = 0.05.

**Secondary (reported, not gated, no multiplicity correction; label
them as exploratory):** P vs N (filter), I vs R (selector inside the
loop), I vs N.

### Interpretation rules

| Primary (I vs P) | P vs N | Interpretation |
|---|---|---|
| I > P, p < 0.05 | any | **Amplifier.** Iteration with feedback and selection beats draw-and-rerank at equal budget. |
| I ≈ P | P > N, p < 0.05 | **Filter only.** Selection helps, but only as a filter; the loop reduces to draw-and-rerank. |
| I ≈ P | P ≈ N | **Neither shows an effect on this benchmark.** Report calibration numbers and the visible/held-out gap (§6) before drawing conclusions. |
| I < P, p < 0.05 | any | **The loop hurts.** Report per-task accept histories; a likely mechanism is overfitting to visible tests. |

## 6. Benchmark: FORKLAND-BENCH-002

Strategy from `hypothesis_v4.md` §2–3 is kept (harder multi-line
tasks, candidate pool, calibration on arm N, then freeze), with
these changes.

### Candidate pool

- N ≥ 10 candidates, authored and passing `bench/validate_bench.py`
  **before** calibration runs. The three proof-of-concept tasks in
  `bench/benchmark_002_proof/` count toward the pool.
- Each candidate has `prompt.md`, `buggy.py`, `visible_tests.py`
  (≥ 2 tests, at least one failing on `buggy.py`), `held_out_tests.py`
  (≥ 3 tests) and `expected.py`. (The proof tasks keep their prompt in
  a sibling `NNN-name.md`; move it to `prompt.md` so
  `forkling.bench` can load them.)
- **`buggy.py` must not describe the bug.** The proof tasks contain
  comments such as `# BUG: drops the last field if text doesn't end
  with newline`, which hands the model the answer. Remove comments
  that name or locate the bug.
- At least one visible test in each candidate must fail on
  `buggy.py`. Held-out tests must include at least one case that
  the visible tests do not cover, so that "passes visible, fails
  held-out" is possible and a filter has something to filter.

### Calibration run

Arm N only, K = 20 independent draws per candidate, same model,
sampling settings and seed as the main run. Calibration draws are
**not** reused in the main experiment. For each candidate, record:

- `p1` = fraction of the 20 draws that pass held-out tests
- `parse_ok_rate`
- `vis_gap` = fraction of visible-passing draws that fail held-out
  (reported, not a filter criterion)

### Freeze criteria (replaces v4 §3 step 4)

Keep a candidate iff **0.10 ≤ p1 ≤ 0.50** and **parse_ok_rate ≥ 0.5**.

- More than 10 survivors: keep the 10 with p1 closest to 0.30;
  break ties by task id.
- Fewer than 6 survivors: stop. Report "benchmark calibration
  failed; primary question deferred" with the calibration table.
  Do not report this as a null.

The freeze is a script (`scripts/freeze_bench_002.py`) committed
before calibration runs. It reads
`results/exp004_calibration.json` and writes
`bench/FORKLAND-BENCH-002.jsonl`; no human judgment is involved.

## 7. Harness changes (must land before calibration)

Each change comes with a unit test that runs without Ollama. All of
them are implemented in `forkling/experiment2.py` (`--protocol 2`),
with protocol 1 left unchanged for reproducing exp001–003. Items 1
and 2 are satisfied by the new module rather than by editing
`compute_metrics`.

1. **Arm labels.** Records carry the arm letter that was requested
   (today the N/I/R aliases label records A/B/C), and
   `compute_metrics` iterates over the arms that were actually run
   (today it hardcodes A/B/C, so exp003's P has no metrics).
2. **Returned patch.** Each (task, arm, replicate) stores the
   returned source's held-out result as `returned_pass`, and the
   primary stats use it.
3. **In-loop prompt.** I and R build the prompt from the current
   source plus the feedback block defined in §2; N and P keep the
   exp003 prompt.
4. **Visible-test count.** `bench.grade` reports passed/total for
   visible tests; P ranks and I accepts on it.
5. **Deterministic sub-seeds** (and common random numbers: the
   per-call seed depends on seed, task, replicate and attempt, not on
   the arm, so arms with identical prompts get identical samples and
   their difference has lower variance). Protocol 1's `run_experiment`
   derives per-arm seeds with `hash((arm, task.id))`, and Python randomizes `str`
   hashes per process unless `PYTHONHASHSEED` is set, so arm R's
   coin flips in exp001–003 are not reproducible from the recorded
   seed. Use a stable hash (e.g. `zlib.crc32`) of
   `(seed, arm, task, replicate)`.
6. **Pinned sampling.** Pass `temperature` (0.8, Ollama's default,
   stated explicitly) and the derived per-call `seed` in the Ollama
   `options`, and record both in `config`.
7. **Replicates and the paired test.** Add `--replicates S`, a
   Wilcoxon signed-rank implementation with an exact null, and the
   bootstrap CI.
8. **No silent fallback.** `LLM.complete` falls back to the
   rule-based planner when Ollama errors. In experiment mode, record
   such calls as `infra` failures and count them toward the timeout
   abort rule (§8), never as model output.

### Harness self-test (gate)

`tests/test_experiment_power.py` runs the full harness against
scripted fake LLMs and must pass in CI before any exp004 run:

- **Filter model:** each draw is independently correct (passes
  visible and held-out) with probability 0.3, otherwise wrong
  (fails visible). Expect returned_pass(P) > returned_pass(N) at
  p < 0.05 over the fake benchmark.
- **Amplifier model:** correct only when the prompt contains
  feedback from a failed attempt. Expect returned_pass(I) >
  returned_pass(P).
- **Null model:** always wrong. Expect every arm at 0 and no
  significant comparison.
- **Loop-state check:** after an accepted patch, the next I-arm
  prompt contains the accepted source, not the original.

If the self-test cannot tell these models apart, the harness cannot
answer the question and exp004 does not run.

## 8. Stopping rule and failure modes

- No early stopping of the experiment. Main-run size:
  10 tasks × 4 arms × 5 replicates × up to 10 calls ≤ 2,000 calls,
  plus 20 calls × candidates for calibration.
- parse_ok < 0.5 in arm N or P → prompt/harness problem. Report the
  parse_ok breakdown; do not interpret the primary.
- Timeouts plus fallback calls > 20% of attempts in any arm → abort
  and report as infra failure.
- I's accepted patches never increase the visible count (commit rate
  ≈ 0) → report "selection had nothing to select".

## 9. Reproducibility

```bash
# 0. Harness gate.
python -m pytest -q tests/test_experiment_power.py

# 1. Validate the candidate pool.
python bench/validate_bench.py \
    --bench bench/benchmark_002_proof/FORKLAND-BENCH-002-candidates.jsonl

# 2. Calibration: arm N, K=20, one replicate.
python -m forkling experiment run --protocol 2 \
    --bench bench/benchmark_002_proof/FORKLAND-BENCH-002-candidates.jsonl \
    --k 20 --replicates 1 --temperature 0.8 \
    --model qwen2.5-coder:3b --seed 20261025 --arms N \
    --out results/exp004_calibration.json

# 3. Freeze (committed before step 2 runs).
python scripts/freeze_bench_002.py
python bench/validate_bench.py --bench bench/FORKLAND-BENCH-002.jsonl

# 4. Main run.
python -m forkling experiment run --protocol 2 \
    --bench bench/FORKLAND-BENCH-002.jsonl \
    --k 10 --replicates 5 --temperature 0.8 \
    --model qwen2.5-coder:3b --seed 20261025 \
    --arms N,P,I,R \
    --checkpoint results/exp004.ckpt.jsonl \
    --out results/exp004.json
python scripts/summarize.py results/exp004.json
```

## 10. What changes from v4

| | hypothesis_v4.md | this document |
|---|---|---|
| Question, arms, model, seed | exp003's | same |
| Primary endpoint | per-task pass@5 (any draw) | returned-patch held-out pass, mean of 5 replicates |
| In-loop prompt | original `buggy.py`, no feedback | current source + last attempt's feedback |
| Selector signal | visible pass/fail | visible tests passed (count) |
| Test | "paired Mann–Whitney U" (implemented unpaired) | exact Wilcoxon signed-rank, paired by task, + bootstrap CI |
| Replicates | 1 | 5 |
| Calibration target | per-task pass@5 ∈ [0.2, 0.4] (not computable) | per-task p1 ∈ [0.10, 0.50] |
| Bug-revealing comments | present | removed |
| Harness gate | none | scripted-LLM self-test must pass |

## 11. Reporting

`results/exp004.json` and `paper/exp004_results.md`, structured like
`exp003_results.md`, stating: the calibration outcome, the primary
test and effect size, the secondaries labelled exploratory, the
interpretation per §5, and whether the harness self-test passed at
the commit that produced the data.

---

**Sign-off:** _pending._ To make this binding, a maintainer replaces
this line with their name and date and commits. After that commit
the document is frozen; changes need a new re-registration.
