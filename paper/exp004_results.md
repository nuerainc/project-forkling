# FORKLAND Experiment 004 — Calibration Outcome: Deferred

**Date:** 2026-09-27
**Pre-registration:** [`paper/hypothesis_v4r1.md`](hypothesis_v4r1.md)
**Calibration data:** [`results/exp004_calibration.json`](../results/exp004_calibration.json)
**Calibration checkpoint:** [`results/exp004_calibration.ckpt.jsonl`](../results/exp004_calibration.ckpt.jsonl)
**Status:** **DEFERRED**, not a null result. Per
[`hypothesis_v4r1.md` §6](hypothesis_v4r1.md#6-benchmark-forkland-bench-002):
*"Fewer than 6 survivors: stop. Report 'benchmark calibration failed;
primary question deferred' with the calibration table. Do not report
this as a null."*

This document records the calibration outcome, what it says about the
benchmark's difficulty gradient, and what an honest next attempt would
look like. It is *not* a result on the I-vs-P mechanism question — the
mechanism question was not asked, because the freeze was not met.

---

## TL;DR

Calibration ran arm N only (one-shot, K=20 independent draws,
`qwen2.5-coder:3b`, seed 20261026, temperature 0.8, protocol 2) on all
12 candidates in `bench/FORKLAND-BENCH-002-candidates.jsonl`. Of the
12, **3 passed** the v4r1 freeze rule (`0.10 ≤ p1 ≤ 0.50`,
`parse_ok_rate ≥ 0.5`): task 006 (`p1=0.50`), task 008 (`p1=0.20`),
task 011 (`p1=0.30`). v4r1 requires at least 6 survivors to proceed;
we are 3 short, so exp004's main experiment does not run.

**Calibration sanity.** `parse_ok_rate = 0.82` overall, `infra = 0`.
The protocol-2 harness is working: it parses 82% of model output and
never falls back to the rule-based planner. There is **no class-M
(measurement-failure) issue here.** The deferred outcome is a
calibration failure, not a measurement failure — the experiment was
not asked, so nothing was uninterpretable.

**What the data does tell us.** The candidate pool's difficulty
gradient is steeper than v4r1's freeze band expected: 9 of 12
candidates have `p1 = 0` (model cannot solve them one-shot, even with
20 independent draws), and 3 have `p1 ∈ [0.20, 0.50]`. The model
**can solve some hard benchmark tasks** (merge intervals at 50%,
flatten at 20%, search-insert at 30%) but the pool's tails pull
harder than the band.

---

## Pre-registered endpoint

Per v4r1 §6 freeze rule:

| candidate | n | p1 | parse_ok | infra | vis_gap | kept |
|---|---|---|---|---|---|---|
| 001 parse_csv | 20 | 0.00 | 0.75 | 0.00 | 0.00 |  |
| 002 deep_merge | 20 | 0.00 | 0.95 | 0.00 | 0.00 |  |
| 003 word_frequencies | 20 | 0.00 | 0.95 | 0.00 | 0.00 |  |
| 004 roman_to_int | 20 | 0.00 | 0.35 | 0.00 | 0.00 |  |
| 005 rle_decode | 20 | 0.00 | 0.95 | 0.00 | 0.00 |  |
| 006 merge_intervals | 20 | **0.50** | 0.85 | 0.00 | 0.00 | yes |
| 007 balanced_brackets | 20 | 0.00 | 0.60 | 0.00 | 0.00 |  |
| 008 flatten | 20 | **0.20** | 0.95 | 0.00 | 0.00 | yes |
| 009 parse_duration | 20 | 0.00 | 0.80 | 0.00 | 0.00 |  |
| 010 lru_cache | 20 | 0.00 | 0.85 | 0.00 | 0.00 |  |
| 011 insert_position | 20 | **0.30** | 1.00 | 0.00 | 0.00 | yes |
| 012 wrap_text | 20 | 0.00 | 0.90 | 0.00 | 0.00 |  |

p1 = fraction of 20 arm-N draws that pass held-out tests.
parse_ok = fraction producing a parseable JSON patch (v4r1 §6 also
requires `parse_ok ≥ 0.5`; all 12 candidates clear this).
infra = fraction of LLM calls that fell back to rule-based (v4r1 §8
aborts if any arm exceeds 0.20; all are 0).
vis_gap = fraction of visible-passing draws that fail held-out;
reported but not a freeze criterion. **All 0** here — there is no
gap to filter on (we never *had* visible-passing draws to gap
against).

3 survivors. The 6-survivor floor is not met. `scripts/freeze_bench_002.py`
exits 1 without writing `FORKLAND-BENCH-002.jsonl`. The main experiment
does not run.

---

## What this is not

**This is not a null result on the I-vs-P question.**

exp001/002/003 each reported a null on the mechanism question. This
document does not. The mechanism question was not asked at arm I vs P
on this benchmark, because there is no benchmark: the calibration rule
that defines what *would count as* a fair test of the question did not
pass. Reporting "I ≈ P on FORKLAND-BENCH-002" would require the
benchmark to exist, and it does not.

If you are looking for the headline mechanism result, this experiment
does not provide one. exp005 (or whatever the next calibration attempt
is called) is the appropriate place to look, after the candidate pool
or freeze band is re-tuned per the recommendations below.

**This is also not a class-M failure.**

A class-M (measurement) failure would look like: parse_ok near 0,
infra near 1, or returned_pass indistinguishable across arms. We see
parse_ok = 0.82, infra = 0, and parse_ok has good spread (0.35–1.0).
The harness is reporting sensible numbers. The freeze rule was not
met for an honest reason: the candidate pool is too hard for the
model, on this hardware, at the chosen freeze band.

---

## What the calibration does tell us

Three things, separated:

### 1. Protocol 2 works.

Per v4r1 §7, the harness must detect a filter effect, an amplifier
effect, and null effects on scripted fake LLMs. The self-test passed
(`tests/test_experiment_power.py` 14/14) before calibration ran.
Calibration then ran 240 real LLM calls against a real model on a real
benchmark, and the harness returned well-formed JSON for every
attempt (parse_ok = 0.82; failures are model output malformation, not
harness bugs). This is the kind of measurement the exp001–003 harness
*could not* produce (v4r1 §0 validity caveat), and it is the
prerequisite for any future answer to the mechanism question.

### 2. The candidate pool's difficulty gradient is steep.

Of 12 candidates, 9 have `p1 = 0` and 3 have `p1 ∈ [0.20, 0.50]`.
No candidate has `p1 ∈ (0.50, 1.0]`. The distribution is bimodal:
*impossible at K=20* vs *plausibly hard at K=20*. There is no
candidate the model finds easy. There is also no candidate the model
*dominates* (passes 80%+ of the time). The "hard enough for selection
to matter, easy enough for arm N to solve sometimes" regime, which the
freeze rule was designed to find, is not populated.

Three tasks reached the band:

- **006 merge_intervals** (`p1=0.50`). Geometry bug class.
- **008 flatten** (`p1=0.20`). Recursive flattening bug.
- **011 insert_position** (`p1=0.30`). Binary-search bug class.

These are all "I know the data structure, here is the algorithm" tasks.
The tasks that failed (parser bugs, state machines, regex-flavored
text manipulation) all involve *open-ended string handling*, which the
3b model struggles with one-shot even with 20 tries. This is a model-
class observation, not a benchmark-design one.

### 3. The candidate pool is undertuned, not the benchmark.

The benchmark mechanism is correct: tasks with both a hidden
deterministic bug and a unique clean fix; visible tests catch the
bug; held-out tests stress edge cases; `validate_bench.py --strict`
verified all 12. The pool's *content* is too parser-heavy relative
to algorithm-heavy. A re-tuned pool would shift the difficulty
distribution into the band.

---

## What an honest next attempt looks like

Three viable paths. Each is publishable. None is an exp004 re-run.

**Path A — relax the freeze band downward.** v4r1 §6 says the band is
`0.10 ≤ p1 ≤ 0.50`. The pre-registered design also says: *"If fewer
than 6 survivors: stop."* Modifying the band without re-registering
would violate the discipline. A new pre-registration could move the
band to `[0.05, 0.30]` (use a smaller model or larger K) and accept
that this is a *different* experiment. Honest framing: "exp005:
relaxed freeze band on FORKLAND-BENCH-002."

**Path B — re-author the candidate pool.** Author 8–10 *algorithm-heavy*
candidates (more like 006 / 008 / 011) and keep 4–5 of the existing
parser-heavy ones as control contrast. Re-register as exp005.
Honest framing: "exp005: re-tuned FORKLAND-BENCH-002."

**Path C — escalate the model.** Use a stronger coder (qwen2.5-coder:7b
or qwen3:4b) on the same candidate pool. With more capability, the
*p1* distribution should slide rightward and populate the band. We
already have evidence (`paper/MODEL_DECISION.md`) that
qwen2.5-coder:7b partial-offloads on 4 GB VRAM, but on hardware with
≥16 GB VRAM it should run fully and inflate p1 by some amount.
Honest framing: "exp005: FORKLAND-BENCH-002 on
`qwen2.5-coder:7b`."

**Path D — re-register the question.** The mechanism question
(filter vs amplifier) is fine. But the operational comparison might
need fewer arms (drop R as a sanity check, since it ties up budget)
or a different unit of replication (more replicates, fewer tasks).
Honest framing: "exp005: smaller-arm protocol 2."

Whichever path is chosen, the **deferred outcome here does not
count** as the result on the mechanism question. The pre-registration
was explicit. A new pre-registration will be explicit too. The
discipline continues.

---

## Reporting transparency

**What we ran:** calibration only. Arm N only, K=20, one replicate,
seed 20261026, 12 candidates. Total: 240 LLM calls in two sittings
(resumed from checkpoint at task 008 after a process-window timeout).

**What we did not run:** arm P, arm I, arm R. No main experiment. No
held-out comparison. No mechanism result.

**Reproducibility:**

```bash
# 1. Re-validate the candidate pool.
python bench/validate_bench.py --strict \
  --bench bench/benchmark_002_proof/FORKLAND-BENCH-002-candidates.jsonl

# 2. Run calibration (arm N only).
python -m forkling experiment run --protocol 2 \
  --bench bench/benchmark_002_proof/FORKLAND-BENCH-002-candidates.jsonl \
  --k 20 --replicates 1 --temperature 0.8 \
  --model qwen2.5-coder:3b --ollama-url http://127.0.0.1:11434 \
  --seed 20261026 --arms N \
  --checkpoint results/exp004_calibration.ckpt.jsonl \
  --out results/exp004_calibration.json

# 3. Apply the freeze rule.
python scripts/freeze_bench_002.py
# exit 0 -> FORKLAND-BENCH-002.jsonl written; proceed to main run.
# exit 1 -> deferred, as here.
```

`tests/test_experiment_power.py` 14/14 passes at the commit that
produced this data. Protocol 2 is verified.

---

## Sign-off

2026-09-27. Calibration complete. Freeze rule not met (3/12 survivors,
floor is 6). Per v4r1 §6, exp004 main is **deferred**, not failed and
not null. Honest next-attempt paths listed above. No mechanism result
to report on this benchmark; the discipline is to say so plainly and
re-register for the next attempt.
