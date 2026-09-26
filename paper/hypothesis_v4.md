# FORKLAND Experiment 004 — Pre-registered Hypothesis

**Author:** Jeremy Beebe
**Date written:** 2026-09-26
**Status:** ACTIVE — no pilot data has been inspected under this design
**Predecessors:**
- [hypothesis.md](hypothesis.md) — exp001, NULL, [results](exp001_results.md)
- [hypothesis_v2.md](hypothesis_v2.md) — exp002, NULL, [results](exp002_results.md)
- [hypothesis_v3.md](hypothesis_v3.md) — exp003, NULL, [results](exp003_results.md)

---

## 1. The question (identical to exp003)

**Is selection pressure on LLM-generated patches a *filter* (a way to
discard bad patches so the running state stays good) or an *amplifier*
(a way to make the LLM generate *better* patches because the prompt
context includes prior attempts)?**

This question is unchanged from exp003. The mechanism question is
independent of benchmark difficulty. exp003 ran on FORKLAND-BENCH-001
(a 10-task one-liner benchmark) and produced three converging nulls.
**The exp003 null is consistent with two competing explanations:**

- **Explanation A (selection really doesn't help):** selection is a
  filter, post-hoc re-rank is sufficient, the in-loop loop is
  bookkeeping. Three priors already favor this.
- **Explanation B (FORFLAND-BENCH-001 was too easy — floor effect):**
  with `arm N pass@5 = 0.90` on the easier benchmark, there is no
  headroom for selection or iteration to demonstrate an effect. The
  benchmark needs to be harder for the question to get a fair test.

exp004 is a head-to-head test of explanations A and B. If exp004
replicates the exp003 null on a harder benchmark, A wins. If exp004
breaks the null, B wins — and the harder benchmark + the I-vs-P
mechanism become the contribution.

## 2. The benchmark: FORKLAND-BENCH-002

### Why a harder benchmark

FORKLAND-BENCH-001 reached `arm N pass@5 = 0.90` (exp003). At that
ceiling, no amount of selection or iteration can move the needle.
The calibration target for FORKLAND-BENCH-002 is **`arm N pass@5 ∈
[0.2, 0.4]`**, leaving real headroom for selection or iteration to
demonstrate an effect.

### What "harder" means

| Dimension | FORKLAND-BENCH-001 | FORKLAND-BENCH-002 (target) |
|---|---|---|
| Function scope | one-liner (~5 LOC) | multi-line (~30–60 LOC) |
| Bug class | off-by-one, wrong op, missing edge, wrong return, typo | state-machine bugs, recursive merging, parser bugs, character-class parsing |
| Stdlib banned | n/a | `re`, `csv` banned (forces hand-rolled parsing, where the bugs live) |
| Visible test coverage | happy path | happy path + 1–2 edge cases |
| Held-out tests | 2–4 specific cases | 3–4 specific cases targeting the bug class |
| Reasoning required | local fix | sometimes cross-function state, multi-branch logic |

### Candidate task pool (proof-of-concept stage)

Three candidate tasks already exist at
[`bench/benchmark_002_proof/`](../../bench/benchmark_002_proof/):

- `001-parse-csv` — hand-rolled CSV parser, drops last field on no-trailing-newline
- `002-deep-merge` — recursive dict merge, overwrites nested dicts
- `003-word-frequencies` — word counting, drops last word on no-trailing-separator

The calibration procedure below will determine which of these (and
how many additional candidate tasks) survive into the frozen
benchmark. **Additional candidate tasks will be authored *before*
calibration runs but their content will not be viewed under
calibration until after the freeze criteria below are written.**

## 3. Pre-registered calibration procedure

The benchmark is not frozen at the time of writing. The
freezing procedure is part of the pre-registration.

### Candidate pool

A pool of N ≥ 10 candidate tasks will be authored before calibration
runs. Each candidate task has:

- `prompt.md` — natural-language description (visible to agent)
- `buggy.py` — buggy implementation
- `visible_tests.py` — at least 2 tests, including the bug case
- `held_out_tests.py` — at least 3 tests, including bug-adjacent cases
- `expected.py` — canonical fix (used by `bench/validate_bench.py`)

Each candidate task passes `bench/validate_bench.py` BEFORE calibration
runs. Tasks that fail validation are excluded; this is a structural
check, not a hypothesis check.

### Calibration run

Run **arm N only** (no-iterate, K=20 independent draws) on every
candidate task using `qwen2.5-coder:3b` and seed `20261025`. This
is one pre-registered calibration experiment, not a hypothesis test.

Compute per task:

- `pass@1` (fraction of 20 draws that pass held-out tests)
- `pass@5` (1 if any of the first 5 draws passed, else 0)
- `parse_ok_rate`

### Freeze criteria

After calibration, the frozen benchmark is constructed by:

1. **Excluding tasks with `pass@1 ≥ 0.7`** (too easy for any
   selection signal to be detectable).
2. **Excluding tasks with `pass@1 ≤ 0.05`** (impossible — no
   LLM can fix it, so no benchmark).
3. **Excluding tasks with `parse_ok_rate < 0.5`** (the prompt
   fix didn't take; selection comparisons would be confounded).
4. **From the survivors, target `arm N pass@5 ∈ [0.2, 0.4]` per
   task.** If more than 10 survivors land in range, keep the
   first 10 by task id (alphabetical). If fewer than 6 survivors
   land in range, the calibration target was wrong; report the
   calibration data and stop.

### Freeze point

Once the calibration data is committed to
`results/exp004_calibration.json`, the benchmark is frozen by
writing `bench/FORKLAND-BENCH-002.jsonl` (one line per surviving
task) and committing both files. **The frozen benchmark is
fixed at the moment of commit; no further edits allowed without
explicit re-registration.**

If `arm N pass@5` does not land in `[0.2, 0.4]` for any candidate
task (calibration was too hard), the experiment does not run;
exp005 will use a re-tuned calibration target and a re-authored
candidate pool. exp004 will be reported as **"benchmark
calibration failed; primary question deferred"**, not as a
null result on a miscalibrated benchmark.

## 4. The arms (identical to exp003)

Four arms. All use the same model, prompt, task list, visible
tests, and held-out tests. The only difference is **when** and
how selection operates.

| Arm | Name | K | Selection timing | Selection policy |
|---|---|---|---|---|
| N | no-iterate | 10 | n/a (each attempt is independent) | n/a — report first held-out pass |
| P | post-hoc re-rank | 10 | after all K draws | pick the patch with the most visible tests passing |
| I | in-loop select | 10 | after each attempt | keep patch iff visible tests pass |
| R | in-loop random | 10 | after each attempt | accept patch with probability 0.5 |

**Primary comparison: I vs P** (in-loop select vs post-hoc re-rank).

Secondary comparisons (reported, not gated): I vs N, I vs R, P vs N.

## 5. Hypothesis

### H1 (alternative, primary)

After N=10 attempts per task per arm on the calibration-frozen
FORKLAND-BENCH-002 (target 6–10 tasks × 10 attempts × 4 arms = 240–
400 LLM calls), Arm I (in-loop select) achieves a higher mean
pass@5 than Arm P (post-hoc re-rank) at p<0.05 by paired
Mann–Whitney U on per-task pass@5.

Pre-registered direction: pass@5(I) > pass@5(P).

### H0 (null, primary)

There is no difference between I and P at alpha=0.05 — pass@5(I)
≤ pass@5(P).

### Pre-registered interpretation rules

| Outcome | Interpretation |
|---|---|
| I > P at p<0.05 | **Positive.** Selection is an amplifier. exp003's three nulls were floor-effect false negatives; FORKLAND-BENCH-002 + the I-vs-P mechanism are the contribution. |
| I ≈ P at p≥0.05 | **Null replicated on harder benchmark.** Selection is a filter. The exp003 null generalizes. The case is closed: selection pressure does not help on bug-fix benchmarks at this scale, with this model. Publishable. |
| I < P | **Surprising.** In-loop iteration actively hurts vs post-hoc re-ranking. Hypothesis of "amplification" is not just weak, it's wrong-signed; candidate explanation is overfitting on visible-test quirks during in-loop iteration. Report as null with a discussion. |

### Why this is one primary hypothesis, not many

The question is one question: is selection a filter or an
amplifier? Bundling "I > P AND I > R" would test amplification AND
"is the selector better than random" — two questions requiring
different evidence. The second is a sanity check (addressed by Arm
R's role), not a primary. exp003 had one primary; exp004 has one
primary.

## 6. What's different from exp003

| Variable | exp003 | exp004 |
|---|---|---|
| Hypothesis | Is selection a filter or amplifier? | (same) |
| Primary comparison | I vs P | (same) |
| Benchmark | FORKLAND-BENCH-001 (frozen) | FORKLAND-BENCH-002 (calibration-frozen by this pre-registration) |
| Calibration procedure | n/a | pre-registered: arm N at K=20, freeze criteria above |
| Number of LLM calls | 400 | 240–400 main + 200+ calibration |
| Pre-registered direction | I > P | (same) |
| Model | `qwen2.5-coder:3b` | (same — see MODEL_DECISION.md) |

Everything else is held constant: same arms, same prompt template,
same statistical test, same alpha, same seed.

## 7. Statistical test (identical to exp003)

Paired Mann-Whitney U on per-task pass@5. One primary comparison:
I vs P. Alpha = 0.05 (no Bonferroni because there is exactly one
primary comparison).

Per-task pass@5 definition: 1 if any of the first 5 attempts
produced a patch that passed held-out tests. For Arm P, "any of
the first 5 attempts" means first 5 of the K independent draws;
the post-hoc re-ranking is applied to whichever of the K the agent
"chooses to return" but pass@5 is just about whether *any* attempt
worked — the post-processing only affects commit and what gets
recorded as the "final patch."

Use the exact permutation distribution for N≤10, implemented in
`forkling/experiment.py:mann_whitney_u`. No correction needed.

## 8. Stopping rule

K=10 attempts per task per arm = 40 attempts per task = 240–400
LLM calls total (depends on calibrated benchmark size). **No
early stopping.**

Pre-registered failure modes:

- If parse_ok in any arm is < 0.50, the prompt fix didn't help
  and selection comparisons are confounded. Report as null with
  the parse_ok breakdown.
- If Arm R and Arm I have very similar commit_rates (e.g., the
  selector behaves like random), report as null and explicitly
  state "selection had nothing to select."
- If model timeouts affect > 20% of attempts in any arm, abort
  and report as null.
- If calibration produces fewer than 6 surviving tasks, report
  as "benchmark calibration failed; primary question deferred"
  and stop without running the main experiment.

## 9. Reproducibility

```bash
# 1. Generate candidate pool (this is the FIRST pre-registered
#    action; happens after this doc is committed).
python bench/validate_bench.py --bench bench/benchmark_002_proof/

# 2. Run calibration: arm N at K=20 on every candidate task.
python -m forkling experiment run \
    --bench bench/benchmark_002_proof/FORKLAND-BENCH-002-candidates.jsonl \
    --k 20 --model qwen2.5-coder:3b --seed 20261025 \
    --arms N \
    --out results/exp004_calibration.json

# 3. Apply freeze criteria (script frozen by commit, no LLM
#    judgment). Writes bench/FORKLAND-BENCH-002.jsonl.
python scripts/freeze_bench_002.py

# 4. Validate frozen benchmark.
python bench/validate_bench.py --bench bench/

# 5. Run main experiment.
python -m forkling experiment run \
    --bench bench/FORKLAND-BENCH-002.jsonl \
    --k 10 --model qwen2.5-coder:3b --seed 20261025 \
    --arms N,P,I,R \
    --checkpoint results/exp004.ckpt.jsonl \
    --out results/exp004.json
```

Wall time on qwen2.5-coder:3b (warm): ~8s cold + ~0.7s × ~600
calls ≈ 7 min. Tractable.

## 10. What I expect (NOT a hypothesis)

My calibrated guess, with the caveat that this is prior not
posterior:

- **If exp003 was a floor effect (explanation B):** exp004 will
  break the null. I expect pass@5(I) > pass@5(P) by ~0.1–0.2
  (modest) on the harder benchmark, where selection has room to
  help.
- **If exp003's null was real (explanation A):** exp004 will
  replicate the null. I expect pass@5(I) ≈ pass@5(P) on the
  harder benchmark too — selection's role is filtering, not
  amplifying, regardless of difficulty.

Either outcome is publishable. The first validates the
harder-benchmark methodology. The second closes the case on the
mechanism question.

## 11. Reporting

Single result file `results/exp004.json`. Companion writeup
`paper/exp004_results.md` with the same structure as
`exp003_results.md`, explicitly stating:

- Whether exp004 replicates or breaks the exp003 null.
- The calibration outcome (which tasks survived the freeze
  criteria, what `arm N pass@5` was on each).
- Whether pass@5(I) > pass@5(P) per the pre-registered test.
- The interpretation per the rules in §5.
- Discussion of how exp004 settles the A-vs-B question from §1.

---

**Sign-off:** This document is frozen at the commit that introduced
it. The hypothesis is **falsifiable, mechanism-driven, and
publishable in either direction**. We did not write it to confirm
selection; we wrote it to find out whether the exp003 null was a
floor effect or a real result.
