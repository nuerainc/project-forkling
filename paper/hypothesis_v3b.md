# FORKLAND Experiment 003b — Pre-registered Rerun of exp003 on a Fixed Harness

**Author:** Jeremy Beebe (draft prepared with Claude Code)
**Date written:** 2026-09-26
**Status:** DRAFT. Becomes binding when a maintainer signs off below
and commits. No exp003b data has been collected.
**Relation to exp003:** exp003 ([pre-registration](hypothesis_v3.md),
[results](exp003_results.md)) stands as run and reported. exp003b asks
the same question on the same benchmark with the harness defects
fixed (see the [validity caveat](exp003_results.md#validity-caveat)).
It is a new experiment, not a re-analysis, and it does not replace
exp003's record.

---

## 1. Question (unchanged from exp003)

**Is selection pressure on LLM-generated patches a *filter* or an
*amplifier*?** Operationalized as in
[hypothesis_v4r1.md §1](hypothesis_v4r1.md):

- filter effect: **P vs N** (re-ranking K independent draws on visible
  tests vs taking one draw);
- amplifier effect: **I vs P** (iterating with feedback and keep-if-better
  vs K independent draws plus the same selector), the primary
  comparison as in exp003.

## 2. Disclosure: what we already know

This is not a blind test. Before writing it we saw all of exp003's
data and computed these exploratory (not pre-registered) numbers from
its records:

- Returned-patch held-out pass under the exp003 harness: N 0.70,
  P 0.70, I 0.70, R 0.50. P's figure is wrong: exp003's re-ranker
  selected the *lowest*-scoring candidate (see the
  [validity caveat](exp003_results.md#validity-caveat), point 4).
- Re-ranking exp003's own P draws correctly (most visible tests
  passed, earliest wins) returns a passing patch on **10/10** tasks,
  against N's 7/10.
- On FORKLAND-BENCH-001, **0 of 127** visible-passing draws (arms N
  and P) failed held-out tests: the visible tests are a perfect proxy
  here.

What this predicts for exp003b:

- N and P use the same prompt as in exp003, so we expect N ≈ 0.7 and
  P ≈ 1.0. **P vs N will very likely favor P**; that is a replication
  of a pattern already seen, not a fresh test.
- I and R get a different prompt (current source plus feedback), so
  exp003 does not predict their scores.
- With P expected at ceiling, the primary **I vs P will very likely be
  uninformative** on this benchmark (see the ceiling rule in §4).

So exp003b's value is (a) running the corrected harness on real model
output end to end, (b) replicating the filter pattern under a correct
endpoint with replicates, and (c) a first look at in-loop behavior
with feedback. The amplifier question belongs to exp004.
Maintainers may reasonably decide to skip exp003b and go straight to
exp004; if it is run, it is run and reported as registered here.

## 3. Design

| | exp003 | exp003b |
|---|---|---|
| Benchmark | FORKLAND-BENCH-001 (frozen) | same, unchanged |
| Model | `qwen2.5-coder:3b` | same |
| Seed | 20261025 | same |
| Arms | N, P, I, R | same names; protocol-2 definitions ([v4r1 §2](hypothesis_v4r1.md)) |
| K (LLM calls per task/arm) | 10 | 10 (I may stop early once all visible tests pass) |
| Replicates | 1 | 5 |
| Harness | protocol 1 | protocol 2, `forkling/experiment2.py` |
| Primary endpoint | pass@5 over draws | returned-patch held-out pass, mean over replicates |
| Test | Mann–Whitney U (unpaired) | exact Wilcoxon signed-rank, paired by task, plus bootstrap CI |
| Sampling | Ollama defaults, unseeded | temperature 0.8, per-call seed derived from (seed, task, replicate, attempt) |

Arm definitions, the feedback block, tie-breaking, the selector signal
(visible tests passed, as a count) and the infra rules are exactly as
in [hypothesis_v4r1.md §2–4 and §7](hypothesis_v4r1.md), as
implemented in `forkling/experiment2.py`.

Budget: 10 tasks × 4 arms × 5 replicates × ≤ 10 calls ≤ 2,000 calls.

## 4. Hypotheses and interpretation

**H1 (primary):** mean returned_pass(I) ≠ mean returned_pass(P), exact
two-sided Wilcoxon signed-rank over the 10 tasks, p < 0.05. Expected
direction I > P.

**Secondary (exploratory, no correction):** P vs N, I vs R, I vs N.

Interpretation uses the table in
[hypothesis_v4r1.md §5](hypothesis_v4r1.md#interpretation-rules), with
one addition: if P's mean returned_pass ≥ 0.95, report I vs P as
"ceiling: not informative on this benchmark" whatever its p-value, and
defer the amplifier question to exp004.

If fewer than 6 tasks have a non-zero I − P difference, report the
primary as "insufficient separation", not as a null.

## 5. Gate, stopping rule, failure modes

- **Gate:** `python -m pytest -q tests/test_experiment_power.py` must
  pass at the commit that produces `results/exp003b.json`, and that
  commit is recorded in `config.harness_commit`.
- No early stopping of the experiment.
- parse_ok < 0.5 in arm N or P → report the breakdown; do not
  interpret the primary.
- infra_rate > 0.20 in any arm (the CLI warns) → abort; report as an
  infra failure.
- I keeps no patch in any run → report "selection had nothing to
  select".

## 6. Reproducibility

```bash
python -m pytest -q tests/test_experiment_power.py
python bench/validate_bench.py
python -m forkling experiment run --protocol 2 \
    --bench bench/FORKLAND-BENCH-001.jsonl \
    --k 10 --replicates 5 --temperature 0.8 \
    --model qwen2.5-coder:3b --seed 20261025 \
    --arms N,P,I,R \
    --checkpoint results/exp003b.ckpt.jsonl \
    --out results/exp003b.json
python scripts/summarize.py results/exp003b.json
```

If the run is interrupted, rerun the same command with
`--resume-from results/exp003b.ckpt.jsonl`.

## 7. Reporting

`results/exp003b.json` and `paper/exp003b_results.md`: primary and
secondary tests with effect sizes and CIs, per-task table, parse_ok and
infra rates per arm, the interpretation under §4, and a short
comparison with exp003 that says which exp003 statements it supports
or contradicts.

---

**Sign-off:** _pending._ To make this binding, a maintainer replaces
this line with their name and date and commits. After that commit the
document is frozen.
