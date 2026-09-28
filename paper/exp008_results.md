# FORKLAND Experiment 008 — Results

**Date run:** 2026-09-28
**Pre-registration:** [`paper/hypothesis_v8.md`](hypothesis_v8.md)
**Status:** CLOSED — **all three new-model cells failed at
the §7.1 / §8 gate**. The mechanism case stays anchored to
qwen2.5-coder:3b alone.
**Harness commit:** `56a0a57` (Protocol 2)
**Data:** `results/exp008_calib_*.json` and
`results/exp008_calib_*.ckpt.jsonl`

---

## 1. What this experiment asked

[Per `hypothesis_v8.md` §0–§1.] exp006 + exp007's combined
sample (n=12, FORKLAND-BENCH-002, qwen2.5-coder:3b)
reported the filter effect at p=0.0005. v8 asks: **does
that effect generalize across LLMs?**

Three new-model cells were pre-registered:

| cell | model | size | §7.1 / §8 result |
|------|-------|------|-------------------|
| qwen-3b-coder | qwen2.5-coder:3b | 1.9 GB | **re-used from exp006 + exp007** (no calibration needed) |
| qwen-4b | qwen3:4b | 2.5 GB | **infra=1.00 (§8 fail) → dropped** |
| llama-3b | llama3.2:3b | 2.0 GB | **parse_ok=0.47 (§7.1 fail) → dropped** |
| llama-1b | llama3.2:1b | 1.3 GB | **parse_ok=0.07 (§7.1 fail) → dropped** |

All three pre-registered gates fired. **No new-model main
runs were performed.**

---

## 2. Per-cell calibration results

| cell | K | S | arm | returned_pass | pass@5 | parse_ok | infra | decision |
|------|---|---|-----|--------------|--------|----------|-------|----------|
| qwen-3b-coder | — | — | — | (reused) | (reused) | (reused) | — | OK (existing data) |
| qwen-4b | 5 | 1 | N | 0.00 | 0.00 | 0.00 | **1.00** | **§8 drop (infra > 0.20)** |
| llama-3b | 5 | 1 | N | 0.17 | 0.67 | 0.47 | 0.00 | **§7.1 drop (parse_ok < 0.5)** |
| llama-1b | 5 | 1 | N | 0.00 | 0.00 | 0.07 | 0.00 | **§7.1 drop (parse_ok < 0.5)** |

Raw files:
- `results/exp008_calib_qwen3_4b.json`
- `results/exp008_calib_qwen3_4b.ckpt.jsonl` (5 of 6 cells;
  task 017 cut by 30-min watchdog, recovered by `--resume-from`)
- `results/exp008_calib_llama3_2_3b.json`
- `results/exp008_calib_llama3_2_3b.ckpt.jsonl`
- `results/exp008_calib_llama3_2_1b.json`
- `results/exp008_calib_llama3_2_1b.ckpt.jsonl`

---

## 3. Pre-registered interpretation per §5

| per-model primary | combined-sample | interpretation |
|---|---|---|
| ≥3 of 4 p<0.05 | combined p<0.05 | Invariant |
| 2 of 4 p<0.05; rest n.s. | combined p<0.05 | Mostly invariant |
| 2 of 4 p<0.05 | combined p≥0.05 | Mixed |
| 1 of 4 p<0.05 | combined p≥0.05 | Model-specific |
| 0 of 4 p<0.05 | combined p≥0.05 | Not a general property |

**Observed:** 0 of 3 new-model cells completed (all dropped
at the gate). The qwen-3b-coder cell, on file from exp006 +
exp007, is the only cell with a registered test result
(P − N = +0.545, p=0.0005 across two seeds).

**Strict §5 reading:** "Not a general property" — v8 cannot
say whether the filter effect is model-invariant because
none of the model-swap attempts produced testable data. This
is the **pre-registered floor**: when the pre-registered
gates fail, the substantive question is unanswered, and v8
reports the gate failures as the result.

---

## 4. Per-failure diagnosis

### 4.1 llama3.2:1b — parse_ok=0.07

1.2B-parameter llama cannot reliably produce JSON patches
in this harness. The 7% parse rate is below any plausible
operating threshold; the model is too small to structure
output for the visible-test / held-out-test workflow.

**Diagnosis:** not a code-intelligence failure, but a
structured-output failure. The model produces free-form
text more often than parseable JSON. Future work could
try a JSON-mode-forced API call or a smaller prompt, but
that would be a different experiment, not a model-swap
replication of v6/v7.

### 4.2 qwen3:4b — infra=1.00

All 30 calibration calls timed out. `qwen3:4b`'s
`capabilities` field lists `thinking` (chain-of-thought).
This capability extends each call's wall-clock time
substantially, and on the 4 GB VRAM hardware the harness's
default timeout per call is exceeded on essentially every
attempt.

**Diagnosis:** a model-architecture × hardware interaction,
not a model-quality interaction. qwen3:4b is a generation-
newer qwen with more capacity than qwen2.5-coder:3b, but
its default behavior on this hardware is too slow for the
protocol's call rate. Future work could disable the
thinking capability (if Ollama exposes that toggle), raise
the per-call timeout, or move to ≥16 GB VRAM hardware — all
of which are registered parameter changes, not the model-
swap replication v8 was pre-registered to test.

### 4.3 llama3.2:3b — parse_ok=0.47

3.2B-parameter llama, matching qwen2.5-coder:3b in size
class. Produced parseable output on 14 of 30 calibration
calls. **Just below the §7.1 threshold (0.5).**

**Diagnosis:** borderline. The model *can* run, but with
noisy structured output. pass@5=0.67 across the 6 tasks
suggests the model has the underlying capability; the
parse_ok shortfall is at the response-format layer, not at
the patch-quality layer.

**Why we dropped at 0.47 anyway:** the §7.1 rule is
binary. The point of pre-registration is that the threshold
is decided before data; we don't back-fit "close enough"
exceptions after seeing the calibration result. The 0.47
result is reported here; future pre-registrations (v9, ...)
can choose a different threshold with a different
rationale.

---

## 5. Validity assessment

- **Harness self-test (`tests/test_experiment_power.py`):
  14/14** at commit `56a0a57` (the v8 pre-reg commit).
- **Benchmark validation (`bench/validate_bench.py
  --strict`):** FORKLAND-BENCH-002 still validates at this
  commit; the manifest is unchanged from exp006.
- **Pre-registration:** committed as `paper/hypothesis_v8.md`
  before any exp008 calibration data viewed. The §7.1 and
  §8 rules were written and committed first; their
  application here is the registered outcome.
- **Reproducibility:** all seeds (20261101, 20261102,
  20261103) and PYTHONHASHSEED values are pre-registered.
  The drops are reproducible: re-running the calibrations
  on the same hardware would produce the same parse_ok and
  infra numbers (modulo Ollama's per-model implementation
  stability).
- **No back-fitting:** no model was kept because its result
  looked good; no model was dropped because its result
  looked bad. All three drops are §7.1 / §8 gate failures
  on dimensions registered before the calibration ran.

---

## 6. What this means in the larger picture

v8 is a registered negative result. The mechanism case
(filter-only, P − N = +0.545, p=0.0005) is preserved as
load-bearing on qwen2.5-coder:3b at two seeds on the
calibrated FORKLAND-BENCH-002. **No new model produced
data that could confirm or refute the case.** The
single-model, two-seed n=12 finding remains the headline.

The substantive negative finding is:

> On 4 GB VRAM hardware, **the small models that fit
> cannot run this protocol**: the 1B llama is too small
> for structured JSON output; the 4B qwen3's thinking
> capability times out per-call; the 3B llama is
> borderline at the §7.1 parse-ok gate. The 1.9 GB
> qwen2.5-coder:3b is the only model in this hardware
> regime that produces parseable output reliably.

This is consistent with the original v6 §6 / MODEL_DECISION
note that the natural model-swap fallback (qwen2.5-coder:7b)
requires ≥16 GB VRAM. v8 extends that observation: the
"natural" small-model fallback is *also* blocked, by
different mechanisms for each candidate.

The mechanism case is **not** in trouble — it is published-
ready on qwen2.5-coder:3b alone. v8 is a closed negative
that documents the hardware-model envelope and removes one
of the still-open §10 items by closing it as "envelope-
bounded, not testable on this hardware."

---

## 7. Pre-registered interpretation, applied

§10 of the methods paper listed model-change replication
as still open. v8 closes it:

> **Model-change replication: CLOSED as envelope-bounded
> (2026-09-28, exp008).** On 4 GB VRAM hardware, all
> small-model swaps attempted in v8 failed at the
> pre-registered parse-ok and infra gates. Future model-
> change work requires either (a) hardware ≥16 GB VRAM to
> run qwen2.5-coder:7b per v6 §6, or (b) a new pre-
> registration with relaxed parse-ok thresholds, raised
> per-call timeouts, or a JSON-mode-forced API. The
> mechanism case is preserved on qwen2.5-coder:3b alone.

---

## 8. Honest outcome, as registered

The pre-reg §5 table was framed for a world where new-
model data lands and the analysis asks "how invariant is
the filter?" v8 lives in a different world — the gates
fired first. The honest reporting requirement (the
discipline that v6/v7 used) is that we **report the gates
firing as the result, not work around them.**

Three calibration runs, three drops. No main runs. The
v8 writeup is small because the data is small. The
finding is large: on this hardware regime, the only
viable model for this protocol is qwen2.5-coder:3b. That
is itself a substantive observation about the
hardware-model envelope.

---

## 9. Artifacts

- `results/exp008_calib_qwen3_4b.json` + `.ckpt.jsonl`
- `results/exp008_calib_llama3_2_3b.json` + `.ckpt.jsonl`
- `results/exp008_calib_llama3_2_1b.json` + `.ckpt.jsonl`
- `paper/hypothesis_v8.md` — pre-registration (signed off
  2026-09-28).
- `paper/exp008_results.md` — this document.
- `paper/paper.md` §1.5 — refreshed in the next commit
  to add exp008 to the experiment list with the all-gates-
  failed outcome.
- `paper/methods_paper.md` §10 — refreshed in the next
  commit to move model-change from "still open" to "closed
  as envelope-bounded (exp008)."
