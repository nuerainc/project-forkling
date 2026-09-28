# FORKLAND Experiment 010 — Cumulative Improvement (v10a) + Cross-Task-Class (v10b)

**Author:** Jeremy Beebe
**Date written:** 2026-09-28
**Status:** ACTIVE — no exp010 data has been collected at
sign-off. `results/` contains no `exp010*` files. No
v10a multi-round protocol code has been written; no v10b
candidate tasks have been authored. Both happen *after* this
document is committed.
**Supersedes:** None. v4r1, v5, v6, v7, v3b, v8, v9 remain
operative. v10 is a *new* registered experiment.
**Predecessors:**
- [paper/half_day_directions_assessment.md](half_day_directions_assessment.md) —
  the assessment memo this pre-registration is drawn from.
- [hypothesis_v6.md](hypothesis_v6.md) — exp006, mechanism
  result.
- [hypothesis_v7.md](hypothesis_v7.md) — exp007, seed-replication.
- [hypothesis_v8.md](hypothesis_v8.md) — exp008, model-change
  (closed as envelope-bounded).
- [exp003_results.md](exp003_results.md) Validity caveat — the
  Protocol-1 audit identifying M1, M2, M3, M4, M5.

---

## 0. Why this attempt

The mechanism question (filter-only on FORKLAND-BENCH-002 with
qwen2.5-coder:3b, P − N = +0.545, p = 0.0005, n = 12) is
closed. exp008 closed model-change as envelope-bounded.
exp003b closed benchmark-change as floor-effect. exp009
(third-seed + temperature sensitivity) is in progress as a
robustness check.

The two questions v10 addresses were identified in
[`paper/half_day_directions_assessment.md`](half_day_directions_assessment.md)
as the two most valuable half-day novel directions:

- **v10a (cumulative improvement):** does the filter effect
  *accumulate* over rounds, or is it one-shot? exp001–exp008
  test the one-shot mechanism; none test the temporal claim
  forkling's autonomy depends on.
- **v10b (cross-task-class):** does the filter effect
  generalize from algorithm-heavy tasks (FORKLAND-BENCH-002)
  to a different problem class?

These are different questions with different protocols and
different benchmarks. They share infrastructure (same model,
same qwen2.5-coder:3b, same test-harness style, same
statistics) and a common registration discipline. v10
pre-registers both as a single experiment with two
sub-studies, executed independently.

---

## Part I — v10a (Cumulative Improvement)

### v10a.1 Question

**Does running the in-loop selector for T rounds, where
each round accepts the best of K draws and applies the
winning patch before the next round, produce a higher
final-pass rate than the same total compute budget
applied as a single round of (T × K) draws with no
inter-round apply?**

This is the **temporal claim.** forkling's autonomy depends
on it: the loop is the engine of cumulative improvement,
and "filter-only" as found by exp006 + exp007 is a one-shot
finding. If multi-round doesn't improve over single-round at
the same compute budget, the loop is no better than a
re-ranker — forkling's loop architecture is decorative.

### v10a.2 Hypothesis

**H1a (primary):** mean `cumulative_pass` for in-loop
multi-round selection with T = 5 rounds and K = 10 draws
per round (call this arm **I-multi**) is greater than mean
`cumulative_pass` for in-loop single-round selection with
T = 1 round and K = 50 draws (call this arm **I-T1-K50**),
Wilcoxon signed-rank p < 0.05 on per-task paired differences.

**H0a:** no difference at α = 0.05.

**Pre-registered secondary:** I-multi vs P-K50 (50
independent draws, take best, no apply), same Wilcoxon
test. If I-multi > P-K50, the loop adds value beyond
post-hoc re-rank.

### v10a.3 Protocol extension (v10a-specific)

The existing Protocol 2 arms (N, P, I, R) treat each cell
as K independent or in-loop draws from a single starting
state. **v10a requires a multi-round mode** where the
state is updated between rounds. Concretely:

| arm | rounds T | draws/round K | total draws | between-round action | final selection |
|-----|---------|---------------|-------------|----------------------|-----------------|
| **I-multi** | **5** | **10** | **50** | apply best patch from round t to source before round t+1; prompt shows the new source | best of round T's K=10 |
| I-T1-K50 | 1 | 50 | 50 | none | best of K=50 |
| P-K50 | 1 | 50 | 50 | none | best of K=50 |
| N-K50 | 1 | 50 | 50 | none | first of K=50 |

The pre-registered primary test is **I-multi vs I-T1-K50**
(multi-round vs single-round at the same total compute
budget). The pre-registered secondary test is **I-multi vs
P-K50** (loop-with-apply vs re-rank-without-apply at the
same budget).

**Why these controls matter.** The two confounds are
(a) does any selection help (controlled by P-K50 vs N-K50),
and (b) does applying between rounds help (controlled by
I-multi vs I-T1-K50 at the same compute). v10a is designed
to disentangle them.

### v10a.4 M2 (in-loop prompt decoupling) — explicit handling

The exp003 audit identified M2 (in-loop arms prompt with
original `buggy.py` while patches apply to evolved source)
as a real failure mode. v10a's I-multi arm **must** use
the *current* source (post-apply) as the prompt for each
round — that's the protocol-2 fix carried forward. The
v10a implementation will fail the harness self-test if the
prompt source is decoupled from the running state.

If a round's accepted patch produces source that breaks the
next round's prompt (e.g., the patch deletes the function
being edited), v10a's implementation falls back to the
last-good-state for the next round's prompt and records
the patch as `applied: false`. This is registered as part
of v10a's protocol and is tested by the v10a harness
self-test.

### v10a.5 Endpoint

**Primary:** `cumulative_pass` — for each (task, arm,
replicate), whether the final patch (after all rounds) of
the final round satisfies the held-out tests. Boolean.

**Secondary per-round trajectory:** `returned_pass` per
(round, task, arm, replicate). Reported for the trajectory
analysis only; not used for any hypothesis test.

**Statistics:** exact two-sided Wilcoxon signed-rank on
per-task paired differences in `cumulative_pass`. Per-task
mean over S = 5 replicates. α = 0.05.

### v10a.6 Stopping rule

- No early stopping. v10a main run: 6 tasks × 4 arms
  (I-multi, I-T1-K50, P-K50, N-K50) × 5 replicates ×
  50 calls = 6,000 LLM calls. ~2.5 hours on qwen2.5-coder:3b
  at temperature 0.8.
- parse_ok < 0.5 in arm N-K50 or P-K50 → report, do not
  interpret the primary for v10a.
- Timeouts + infra fallbacks > 20% of attempts in any arm
  → abort v10a as infra failure.

### v10a.7 Reproducibility (sketch)

```bash
# 0. Harness gate (extended with v10a multi-round self-test).
python -m pytest -q tests/test_experiment_power.py

# 1. Validate the frozen benchmark.
python bench/validate_bench.py --strict --bench bench/FORKLAND-BENCH-002.jsonl

# 2. v10a main run.
python -m forkling experiment run --protocol 2 \
  --bench bench/FORKLAND-BENCH-002.jsonl \
  --multi-round 5 --k-per-round 10 --k-single-round 50 \
  --replicates 5 --temperature 0.8 \
  --model qwen2.5-coder:3b --ollama-url http://127.0.0.1:11434 \
  --seed 20261107 --arms I-multi,I-T1-K50,P-K50,N-K50 \
  --checkpoint results/exp010a.ckpt.jsonl \
  --resume-from results/exp010a.ckpt.jsonl \
  --out results/exp010a.json
```

The `--multi-round 5 --k-per-round 10 --k-single-round 50`
flags and the I-multi arm name are placeholders for the
v10a harness extension. The pre-registered implementation
matches the v10a.3 / v10a.4 specification; deviations
require a new pre-registration.

---

## Part II — v10b (Cross-Task-Class Replication)

### v10b.1 Question

**Does the filter effect (P > N on `returned_pass`)
generalize from algorithm-heavy tasks
(FORKLAND-BENCH-002) to a different problem class?**

Algorithm-heavy tasks (merge-intervals, flatten,
insert-position, wrap-text, binary-search, rotate-array)
have structured solutions and well-defined patches.
The filter effect might depend on this structure. A
different class — **string manipulation** — has different
patch-space properties: patches are typically simpler
(one-line edits to string operations), the visible-test
surface is small (3 tests), and the LLM is more likely
to produce correct patches on first try. The filter
might be unnecessary in this regime (floor effect) or
might still help.

### v10b.2 Hypothesis

**H1b (primary):** mean `returned_pass(P)` > mean
`returned_pass(N)` on the string-manipulation
mini-benchmark, Wilcoxon signed-rank p < 0.05.

**H0b:** no difference at α = 0.05.

**Pre-registered secondary:** comparison of the
mini-benchmark's effect size to FORKLAND-BENCH-002's
combined-sample effect size. If the new effect is
directionally consistent (positive) but smaller (because
of a higher N-baseline floor), the mechanism is task-class-
invariant but task-difficulty-dependent.

### v10b.3 Benchmark design — string manipulation

v10b authors a 4-6 task mini-benchmark in the **string
manipulation** class. Each task has the standard
`buggy.py`, `expected.py`, `visible_tests.py`,
`held_out_tests.py`, `prompt.md` structure. Tasks are
authored **after** this document is committed but
**before** calibration runs. Pre-registered task-class
requirements:

- Each task is a single-file Python bug-fix where the
  fix is a 1-3 line edit to a string operation.
- Each task has 3 visible tests and 3 held-out tests,
  all using the standard `assert` framework.
- Bug complexity: similar to FORKLAND-BENCH-002 (off-by-one
  in slicing, missing edge case, wrong operator in a
  string method, etc.).
- No task uses regex, external libraries, or unicode
  edge cases that the 3b model is unlikely to handle.

Pre-registered candidate tasks (the actual list is
finalized by the author at authorship time, before
calibration; the candidate list below is illustrative,
not committed):

1. `reverse-words` — reverse word order in a sentence.
2. `is-palindrome` — check if a string is a palindrome.
3. `anagram-check` — check if two strings are anagrams.
4. `compress-string` — basic run-length encoding.
5. `longest-substring-no-repeat` — longest substring
   without repeating characters.
6. `valid-parentheses` — check balanced parentheses.

**Pre-registered task-set selection rule:** the author
authors 6 candidates; calibration runs all 6; the
calibration manifest freezes the subset that lands
`p1 ∈ [0.10, 0.50]` in arm N. If fewer than 4 tasks
land in band, the calibration is **deferred** (v10b
does not run; honest deferral is the registered outcome).

### v10b.4 Calibration and freeze

Per the v6 §2.4 / exp005 Path B discipline: arm N at
K = 20, S = 1, on the 6 candidate tasks. Compute
per-task pass@5. Tasks with pass@5 outside
[0.10, 0.50] are excluded. If ≥ 4 tasks remain, freeze
the manifest. If < 4 tasks remain, v10b defers.

### v10b.5 Main run

Same Protocol 2 as v6/v7/v9. Same arms (N, P, I, R).
Same K = 10, S = 5, temperature 0.8, model
qwen2.5-coder:3b. New seed: 20261108.

6 tasks × 4 arms × 5 replicates × 10 calls = 1,200
LLM calls. ~30 min.

### v10b.6 Endpoint and statistics

- Primary endpoint: `returned_pass`.
- Test: exact two-sided Wilcoxon signed-rank on per-task
  paired differences (P vs N).
- Effect size: mean per-task difference with bootstrap CI.
- α = 0.05.

### v10b.7 Stopping rule

- v10b calibration: 6 tasks × 1 arm × K=20 × S=1 = 120 calls.
- v10b main run: 1,200 calls. parse_ok < 0.5 in N or P →
  report, do not interpret the primary. Timeouts + infra
  fallbacks > 20% of attempts in any arm → abort v10b.

---

## Part III — Shared elements

### Models

Both v10a and v10b use **qwen2.5-coder:3b** only. Model-
change replication is closed as envelope-bounded (exp008).
The mechanism finding is preserved on this model.

### Seeds

- v10a seed: 20261107.
- v10b seed: 20261108.
- Both unique relative to all prior seeds (20261025, 20261030,
  20261031, 20261101, 20261102, 20261103, 20261104,
  20261105, 20261106). PYTHONHASHSEED is set to match.

### Harness

Protocol 2 (`forkling/experiment2.py`) plus a v10a-specific
extension for multi-round mode. The v10a extension is
written *after* this document is committed and ships with
its own harness self-test case in `tests/test_experiment_power.py`.

### Cross-sub-study analysis

The two sub-studies v10a and v10b do **not** share a
combined-sample analysis — they answer different questions
with different endpoints. v10a's combined analysis is
within the multi-round study (I-multi vs controls);
v10b's combined analysis is within the new mini-benchmark.
A meta-analysis across v10a and v10b is not pre-registered.

### Validity

- Harness self-test (`tests/test_experiment_power.py`) must
  pass at the data-producing commit, including the v10a
  multi-round self-test case.
- The frozen FORKLAND-BENCH-002 manifest (v10a) and the new
  string-manipulation manifest (v10b) must each pass
  `bench/validate_bench.py --strict`.

---

## Part IV — Interpretation

### v10a interpretation (per §v10a.2)

| I-multi vs I-T1-K50 | I-multi vs P-K50 | interpretation |
|---|---|---|
| I-multi > I-T1-K50, p<0.05 | any | **Loop adds value beyond re-rank** (cumulative claim supported) |
| I-multi ≈ I-T1-K50 | I-multi > P-K50, p<0.05 | Loop is a re-ranker; multi-round doesn't compound |
| I-multi ≈ I-T1-K50 | I-multi ≈ P-K50 | Filter is one-shot; loop has no benefit |
| I-multi < I-T1-K50, p<0.05 | any | Loop actively hurts at multi-round; loop architecture fails |

### v10b interpretation (per §v10b.2)

| P vs N within new bench | direction vs exp006+exp007 | interpretation |
|---|---|---|
| P > N, p<0.05 | positive | **Task-class-invariant**; filter generalizes |
| P ≈ N | positive (numerically) | **Power-bounded**; same direction, n=4-6 too small |
| P ≈ N | null | **Task-class-specific**; filter is algorithm-heavy-only |
| P < N, p<0.05 | negative | **Reversed**; surprise; requires investigation |

### Combined-study interpretation

The two sub-studies do not produce a single combined
interpretation table. Each sub-study is reported
independently per its own §interpretation.

---

## Part V — What v10 changes from v6 / v7 / v9

| | v6 / v7 | v9 | v10 |
|---|---|---|---|
| Mechanism question | closed | n/a | n/a (independent) |
| Q1 third-seed | n/a | yes | n/a (independent) |
| Q2 temperature | n/a | yes | n/a (independent) |
| v10a: cumulative-improvement | not tested | not tested | **new** (multi-round protocol) |
| v10b: cross-task-class | not tested | not tested | **new** (string-manipulation mini-benchmark) |
| Endpoint | returned_pass | returned_pass | v10a: cumulative_pass + per-round returned_pass; v10b: returned_pass |
| Statistics | Wilcoxon | Wilcoxon | Wilcoxon |

---

## Part VI — What we are *not* doing

- **Not** running model-change. Closed as envelope-bounded
  (exp008).
- **Not** running benchmark-change on FORKLAND-BENCH-001.
  Closed as floor-effect (exp003b).
- **Not** re-running exp006 + exp007 + exp009.
- **Not** re-deriving FORKLAND-BENCH-002.
- **Not** tuning seeds, temperatures, or round counts to
  fit. All are pre-registered.
- **Not** pooling v10a and v10b into a single combined-sample
  test. They answer different questions.
- **Not** authoring v10b tasks before calibration. Tasks are
  authored *after* this document is committed; calibration
  filters them.

---

## Part VII — Sign-off

**Sign-off:** 2026-09-28. Pre-registered before any exp010
data viewed.

- v10a hypothesis: multi-round in-loop selection (T=5,
  K=10) accumulates improvement over single-round
  selection (T=1, K=50) at the same total compute budget.
- v10b hypothesis: filter effect (P > N) replicates on a
  string-manipulation mini-benchmark with the same
  Protocol 2 as v6/v7.

The discipline is the same as v6/v7/v8/v9: committed
pre-registration, harness self-test at the data-producing
commit, honest reporting per the §interpretation tables,
honest null acceptance.
