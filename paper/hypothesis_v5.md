# FORKLAND Experiment 005 — Pre-registered Hypothesis

**Author:** Jeremy Beebe
**Date written:** 2026-09-27
**Status:** ACTIVE — no exp005 data (calibration or main) has been
collected at sign-off. `results/` contains no `exp005*` files.
**Supersedes:** This is not a supersession. v4r1 (`hypothesis_v4r1.md`)
remains the operative pre-registration for exp004. exp004 was
**deferred** per v4r1 §6 (3/12 calibration survivors, below the
6-survivor floor); this document is the *next attempt*, not a
correction of v4r1.
**Predecessors:**
- [hypothesis.md](hypothesis.md) — exp001, NULL, [results](exp001_results.md)
- [hypothesis_v2.md](hypothesis_v2.md) — exp002, NULL, [results](exp002_results.md)
- [hypothesis_v3.md](hypothesis_v3.md) — exp003, NULL, [results](exp003_results.md)
- [hypothesis_v4r1.md](hypothesis_v4r1.md) — exp004, **DEFERRED** (3/12 survivors; not a null), [results](exp004_results.md)
- Path assessment that motivates this document: [exp005_paths.md](exp005_paths.md)

---

## 0. Why this attempt, and why these specific choices

exp004's calibration on the 12-candidate pool produced a bimodal
*p1* distribution: 9 candidates at `p1=0` (model cannot fix at all
with K=20), 3 at `p1 ∈ [0.20, 0.50]`, none above 0.50. The freeze rule
at `[0.10, 0.50]` found 3 survivors; the 6-survivor floor was not
met; exp004 main did not run. See
[`exp004_results.md`](exp004_results.md) for the full outcome.

The four candidate paths forward were assessed in
[`exp005_paths.md`](exp005_paths.md). Three were rejected:

- **Path A (relax band)** — rejected. The freeze rule did what it
  was built to do. Widening `[0.10, 0.50]` to fit the existing pool
  would be the polish-over-realism move exp004 was designed to
  prevent. The band stays.
- **Path C (escalate model to qwen2.5-coder:7b)** — deferred as
  primary. Hardware-blocked on 4 GB VRAM (per
  [`MODEL_DECISION.md`](MODEL_DECISION.md) the 7b variant
  partial-offloads and runs at 5–6 s/call instead of 0.7, which
  makes 4,400-call experiments impractical). Folded in as a
  pre-registered model-escalation fallback if Path B alone does
  not populate the band.
- **Path D (re-register the question)** — rejected. The mechanism
  question (filter vs amplifier, primary I vs P) is still open on
  no class-V evidence. Rewriting it doesn't help answer it.

**Path B (re-author the candidate pool) is the main lever.** The
exp004 calibration told us exactly what's missing: more candidates
in the algorithm-mid-difficulty band where task 006 / 008 / 011
landed. We author ~8–10 such candidates, keep a small proportion of
the existing parser-heavy ones as control contrast, and re-run
calibration. The discipline forbids tuning the pool to a target
*p1*; we author to the criteria below, calibrate, and let
`scripts/freeze_bench_002.py` apply the rule mechanically.

---

## 1. The question (unchanged from v4r1 and exp003)

**Is selection pressure on LLM-generated patches a *filter* (a
way to discard bad patches so the running state stays good) or
an *amplifier* (a way to make the LLM generate *better* patches
because the prompt context includes prior attempts)?**

Operationally, with an equal budget of K LLM calls per task:

- **Filter effect:** choosing among K independent draws by visible
  tests returns a better patch than taking one draw. Measured
  by **P vs N**.
- **Amplifier effect:** iterating (each attempt sees the current
  source and the last test feedback, keep-if-better) returns a
  better patch than K independent draws plus the same selector.
  Measured by **I vs P**. This is the **primary comparison**.

If I ≈ P, the evolve loop can be replaced by "draw K, re-rank".

This question is independent of benchmark difficulty. exp004's
deferred outcome did not produce a class-V (validation) answer;
it produced a calibration failure. The question stands.

## 2. The benchmark: FORKLAND-BENCH-002 (re-calibrated)

### 2.1 Why the pool changes

The exp004 pool had a *bimodal* difficulty distribution. The
freeze band `[0.10, 0.50]` was designed to find tasks where arm N
sometimes-but-not-always wins — the regime where selection has
something to do. The pool had:

- 9/12 tasks at `p1=0` (impossible at K=20).
- 3/12 tasks in band (006 merge intervals, 008 flatten, 011
  search-insert).
- 0/12 tasks at `p1 ∈ (0.50, 1.0]` (model dominates; floor effect).

A re-tuned pool should populate the middle. The discipline here
is that the pool is *authored to criteria*, not tuned to a target
*p1*. We do not run the calibration, see which tasks land where,
and adjust. We write the criteria, then write the tasks.

### 2.2 Pool criteria (pre-registered)

The augmented pool is authored to the following pre-registered
distribution. These are *task-design proportions*, not predicted
outcomes. The freeze rule then decides which to keep.

| Difficulty band | Approx. share | Definition |
|---|---|---|
| Algorithm-heavy | ~50% (8-10 tasks) | Bug class: data-structure algorithm (sort, search, balanced tree, hash table, queue, stack, graph-traversal, recursion). Input size small enough that a 60-second pytest run is well within budget. Stdlib only; may not use `re` or `csv`. |
| Parser-heavy (retained) | ~25% (3-5 tasks) | Existing FORKLAND-BENCH-002 parser candidates retained (001, 002, 003 + 004 roman_to_int + 007 balanced_brackets + 012 wrap_text, of which the data showed 003 + 007 + 012 were hardest). These serve as control contrast — the calibration tells us if the new pool has the same parser-dominated bias or populates more uniformly. |
| Trivial control | ~10% (1-2 tasks) | Tasks the model should solve nearly every time (`p1` expected >> 0.50). Included so the calibration can sample the high end and confirm `p1 ≈ 0.7-1.0` is structurally possible on this hardware. If even these land at `p1 ≈ 0.50`, the calibration is being misread and *deferred* is the safe call. |
| Hard-impossible control | ~10% (1-2 tasks) | Tasks that should fail every draw (`p1` expected ≈ 0). These confirm the calibration correctly rejects tasks below `0.10`. |

**Total target:** 18-22 candidates. Strict lower bound:
`L ≥ 18`. If fewer candidates pass `validate_bench.py --strict`,
the experiment does not run.

**Per-task structure** (unchanged from v4r1 §6):
- `prompt.md` — natural-language description (visible to agent).
- `buggy.py` — buggy implementation (visible). Must **not** name
  or locate the bug in comments.
- `visible_tests.py` — ≥ 2 tests, at least one failing on
  `buggy.py`.
- `held_out_tests.py` — ≥ 3 tests, at least one not covered by
  visible tests, so "passes visible, fails held-out" is possible
  and a filter has something to filter.
- `expected.py` — canonical fix (grader-only).

`bench/validate_bench.py --strict` is the gate.

### 2.3 Calibration run

Same as v4r1 §6:

- Arm N only, K = 20 independent draws per candidate.
- Same model, sampling settings, prompt template as the main
  run, but seed `20261027` (main run uses 20261025; calibration
  uses 20261027 because 20261026 was used for exp004).
- Per-call seeds derived from `(seed, task, replicate, attempt)`.
- Calibration draws are **not** reused in the main experiment
  (different seed in main; calibration draws are pre-trial).

Per-task metrics: `p1`, `parse_ok_rate`, `vis_gap`.

### 2.4 Freeze criteria (unchanged from v4r1 §6)

`scripts/freeze_bench_002.py` is unchanged (the same script,
preserved between commits). It reads
`results/exp005_calibration.json` and writes
`bench/FORKLAND-BENCH-002.jsonl` (overwrites any prior version).

Keep a candidate iff **`0.10 ≤ p1 ≤ 0.50`** and
**`parse_ok_rate ≥ 0.5`**.

- More than 10 survivors → keep the 10 with `p1` closest to
  0.30; tie-break by task id (alphabetical).
- Fewer than 6 survivors → `freeze_bench_002.py` exits 1
  without writing the JSONL. The experiment does not run. Report
  the calibration table per v4r1 §6 and treat as a *second*
  deferred outcome.
- Trivial control tasks land at `p1 ≈ 1.0` (above band): they
  are intentionally *not* kept, but their existence in the pool
  is structurally important (so we know the band is reachable).
  If they instead land in band, the band itself may be misplaced;
  the calibration writes that down but does not re-define the
  band.
- Hard-impossible tasks land at `p1 ≈ 0` (below band):
  correctly excluded.

### 2.5 Calibration target

The pre-registration predicts the augmented pool will produce
**8-12 survivors** (vs. 3 for the exp004 pool). This prediction is
*for reviewer reference*, not a target to hit. If the calibration
produces 0 survivors (impossible pool) or > 10 survivors (forced
down-selection by §2.4), the data is the data; we report it.

---

## 3. The arms (unchanged from v4r1)

Four arms. K = 10 LLM calls per (task, arm, replicate). All arms
use the same model, sampling settings, benchmark, visible tests,
and held-out tests. The protocol-2 prompts and feedback block are
unchanged.

| Arm | What the model sees | Selection | Returned patch |
|---|---|---|---|
| N | task prompt + original `buggy.py` + visible tests | none | attempt 0 (other K-1 draws run for `pass@k` continuity) |
| P | same as N, K independent draws | after all K: most visible tests passed; tie → lowest attempt index | the winner |
| I | task prompt + **current** source + visible tests + **feedback from the previous attempt** (the patch tried, whether it was kept, and the visible-test failure output, ≤ 2,000 chars) | after each attempt: keep iff strictly more visible tests pass; stop once all visible tests pass | final current source |
| R | same prompt and feedback as I | keep parsed patch with probability 0.5; no early stop | final current source |

R shares I's prompt and feedback so **I vs R** isolates the
selector inside the loop from iteration with feedback.

## 4. Endpoint and statistics (unchanged from v4r1)

- **Primary endpoint:** `returned_pass` for each (task, arm,
  replicate). Mean of S=5 replicates is the per-task score.
- `pass@1/5/10` (any-draw, exp001–003 style) is computed and
  reported for continuity, **not** used for any hypothesis test.
- **Test:** exact two-sided Wilcoxon signed-rank on per-task
  paired differences (tasks are the paired unit; zero differences
  dropped; ties in |difference| use mid-ranks; exact permutation
  null). Alpha = 0.05. **Primary comparison I vs P.** Test lives in
  `forkling/experiment2.py:wilcoxon_signed_rank_exact`.
- **Effect size:** mean per-task difference with a 10,000-resample
  bootstrap CI; resampling seed derived from `(seed, comparison)`.
  Report the CI whatever the p-value.

## 5. Hypotheses (unchanged from v4r1)

**H1 (primary):** mean `returned_pass(I)` ≠ mean
`returned_pass(P)`, Wilcoxon signed-rank, p < 0.05. Expected
direction (not a one-sided test): I > P.

**H0:** no difference at alpha = 0.05.

**Secondary (reported, not gated, no multiplicity correction;
labelled exploratory):** P vs N (filter), I vs R (selector
inside loop), I vs N.

### Interpretation rules

Same as v4r1:

| Primary (I vs P) | P vs N | Interpretation |
|---|---|---|
| I > P, p<0.05 | any | **Amplifier.** Iteration + feedback + selection beats draw-and-rerank at equal budget. |
| I ≈ P | P > N, p<0.05 | **Filter only.** Selection helps, but only as a filter; the loop reduces to draw-and-rerank. |
| I ≈ P | P ≈ N | **Neither shows an effect.** Report calibration + visible/held-out gap before drawing conclusions. |
| I < P, p<0.05 | any | **The loop hurts.** Per-task accept histories; likely mechanism is overfitting to visible tests. |

## 6. Model decision — pre-registered as a function of calibration

The model is chosen by the pre-registered rule below. The rule
makes the choice a *function of observable data*, not a
free parameter we can adjust post-hoc.

- **Primary model:** `qwen2.5-coder:3b`. Warm ~0.7 s/call,
  fits fully in 4 GB VRAM (per `MODEL_DECISION.md`).
- **Model-escalation fallback:** if the augmented pool produces
  **fewer than 6 survivors** on `qwen2.5-coder:3b`, the
  experiment *defers unless hardware meeting ≥ 16 GB VRAM is
  available* — at which point the main run uses
  `qwen2.5-coder:7b`. This applies the same model-swap clause as
  exp002's `qwen2.5-coder:7b → qwen2.5-coder:3b` switch (the
  hypothesis text and primary metric are unchanged; only the
  model field). The hardware constraint is recorded up front.
- **Sampling:** `temperature=0.8` (Ollama default, stated
  explicitly), per-call Ollama seed derived from
  `(seed, arm, task, replicate, attempt)` via
  `zlib.crc32`, recorded in `config`. Reproducibility requires
  `PYTHONHASHSEED` (since hashes are involved) and the derived
  Ollama seed (since the model is stochastic).
- **No silent fallback.** Ollama errors record `infra: ...`
  and count toward the 20%-timeout abort rule. Rule-based
  completions (in `forkling/planner.py`) are **never** returned
  as model output in experiment mode.

## 7. Harness changes (v4r1 §7, all carried over)

All v4r1 §7 changes are required for exp005 and live in
`forkling/experiment2.py`:

1. Each (task, arm, replicate) stores `returned_pass`.
2. In-loop prompts show current source + feedback block.
3. Selection ranks on `visible_passed` count.
4. Deterministic sub-seeds via `zlib.crc32`.
5. Pinned sampling (temperature + per-call Ollama seed in
   `options`).
6. S=5 replicates (configurable per `--replicates`).
7. Paired Wilcoxon signed-rank with exact null + 10,000-resample
   bootstrap CI.
8. No rule-based fallback in experiment mode.

### Harness self-test gate (re-stated)

`tests/test_experiment_power.py` must pass at the commit that
produces exp005 data. Three scripted fake LLMs (filter,
amplifier, null). If the self-test cannot tell them apart, the
harness cannot answer the question and exp005 does not run.

A previous run of this file on 2026-09-26 (commit `f1420a1`)
passed 14/14. Re-verifying at sign-off of the run that produces
exp005 data is required.

## 8. Stopping rule

- No early stopping. Calibration: 18-22 candidates × K=20 = 360-440
  calls. Main run: ≤ 22 tasks × 4 arms × 5 replicates × 10 calls ≤
  4,400 calls.
- parse_ok < 0.5 in arm N or P → prompt/harness problem; report
  and do not interpret the primary.
- Timeouts + infra fallbacks > 20% of attempts in any arm → abort
  as infra failure.
- I's accepted patches never increase the visible count (commit
  rate ≈ 0) → report "selection had nothing to select."

## 9. Reproducibility

```bash
# 0. Harness gate.
python -m pytest -q tests/test_experiment_power.py

# 1. Validate the augmented candidate pool.
python bench/validate_bench.py --strict \
  --bench bench/benchmark_002_proof/FORKLAND-BENCH-002-candidates.jsonl

# 2. Calibration: arm N, K=20, seed 20261027.
python -m forkling experiment run --protocol 2 \
  --bench bench/benchmark_002_proof/FORKLAND-BENCH-002-candidates.jsonl \
  --k 20 --replicates 1 --temperature 0.8 \
  --model qwen2.5-coder:3b --ollama-url http://127.0.0.1:11434 \
  --seed 20261027 --arms N \
  --checkpoint results/exp005_calibration.ckpt.jsonl \
  --out results/exp005_calibration.json

# 3. Freeze.
python scripts/freeze_bench_002.py
python bench/validate_bench.py --strict \
  --bench bench/FORKLAND-BENCH-002.jsonl
# exit 0 -> continue. exit 1 -> deferred, write exp005_results.md as
# 'second deferred outcome'.

# 4. Main run (3b on this hardware).
python -m forkling experiment run --protocol 2 \
  --bench bench/FORKLAND-BENCH-002.jsonl \
  --k 10 --replicates 5 --temperature 0.8 \
  --model qwen2.5-coder:3b --ollama-url http://127.0.0.1:11434 \
  --seed 20261025 --arms N,P,I,R \
  --checkpoint results/exp005.ckpt.jsonl \
  --out results/exp005.json
python scripts/summarize.py results/exp005.json
```

`scripts/run_exp004.sh` does steps 0-4 for exp004; a parallel
`scripts/run_exp005.sh` should be created before the run. (Not
done at sign-off — that script is a runner, not a design doc.)

## 10. What changes from v4r1

| | hypothesis_v4r1.md | this document |
|---|---|---|
| Question, arms, model, statistics, endpoint | exp004's | same |
| Calibration target | per-task p1 ∈ [0.10, 0.50] | same (Path A explicitly rejected) |
| Calibration seed | 20261026 | **20261027** (different from main; same role) |
| Candidate pool | 12 candidates, bimodal difficulty (9 at p1=0, 3 in band, 0 above) | **18-22 candidates authored to §2.2 criteria** |
| Model-swap clause | single swap 7b → 3b mid-run (exp002-style, applied retroactively) | **Pre-registered conditional swap** as a function of calibration outcome (Path C as fallback only) |
| Trivial + hard-impossible controls | none | **Yes — ~10% each** (so the calibration's high and low edges are structurally tested) |
| Path-decision | n/a | All four paths assessed in `exp005_paths.md`; A and D rejected; B main; C fallback |

## 11. Reporting

`results/exp005.json` and `paper/exp005_results.md`, structured
like exp003_results.md / exp004_results.md, stating:

- The pool authored under this design (proportion of
  algorithm-heavy / parser-retained / trivial control / hard
  control).
- The calibration outcome (per-task `p1`, `parse_ok`, `vis_gap`,
  freeze decision).
- The primary test and effect size (I vs P).
- The secondaries labelled exploratory.
- The interpretation per §5.
- Whether the harness self-test passed at the commit that
  produced the data.
- If the calibration produced <6 survivors and we cannot
  escalate to 7b (no ≥16 GB VRAM hardware), report as a
  *second deferred outcome* per the v4r1 §6 language. Do not
  report as a null.

---

## 12. What we are *not* doing in this pre-registration

- **Not** widening the freeze band. Path A rejected.
- **Not** changing the mechanism question. Path D rejected.
- **Not** running any pilot on the augmented pool until this
  document is **committed** and the augmented candidates
  are authored and validated. Discipline matters more than
  cycle speed.
- **Not** re-running exp004's calibration. exp004 is closed.
- **Not** authoring any candidate task whose difficulty is
  tuned to a target `p1`. Tasks are written to the §2.2
  criteria; the freeze rule decides what to keep.

---

## 13. Sign-off

**Sign-off:** 2026-09-27. Pre-registered before any pilot data
viewed under this design. The hypothesis is **falsifiable,
mechanism-driven, and publishable in either direction** —
"I ≈ P" and "I > P" are both load-bearing outcomes. The
discipline carries forward from exp001–003: honest reporting
of calibration outcomes, deferred runs, and mechanism nulls,
in that order.

Authored in continuity with v4r1's protocol-2 fixes.
Frozen at sign-off; changes need a new re-registration.
