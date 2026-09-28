# FORKLAND Experiment 008 — Pre-registered Model-Invariance Replication

**Author:** Jeremy Beebe
**Date written:** 2026-09-28
**Status:** ACTIVE — no exp008 data has been collected at
sign-off. `results/` contains no `exp008*` files. The only
exp008-related artifact in `results/` would be `exp008_*
calibration` outputs from the new-model parse-ok check (see
§7.1) — those are also absent at sign-off and must be
generated *after* this document is committed.
**Supersedes:** None. v4r1, v5, v6, v7, v3b remain operative
for their respective experiments. exp008 is a *new*
registered experiment; it does not re-open, re-register, or
re-interpret any prior experiment.
**Predecessors:**
- [hypothesis_v6.md](hypothesis_v6.md) — exp006, mechanism
  result on FORKLAND-BENCH-002 (filter only).
- [hypothesis_v7.md](hypothesis_v7.md) — exp007, seed-replication
  of exp006, mechanism result reproduced directionally; combined
  n=12 across two seeds, P − N = +0.545, p=0.0005.
- [exp006_results.md](exp006_results.md), [exp007_results.md](exp007_results.md).
- [hypothesis_v3b.md](hypothesis_v3b.md) — exp003b, within-benchmark
  Protocol-2 re-run of exp003 on FORKLAND-BENCH-001, closed as
  floor-effect "Neither" outcome per §10.
- [MODEL_DECISION.md](MODEL_DECISION.md) — original 3b vs 7b
  hardware analysis.
- [exp003_results.md](exp003_results.md) Validity caveat — the
  Protocol-1 audit that justified Protocol 2.

---

## 0. Why this attempt

exp006 + exp007 combined-sample (n = 12 across two seeds)
reports the filter effect on FORKLAND-BENCH-002 with
`qwen2.5-coder:3b`: P − N = +0.545, 95% CI [+0.400, +0.691],
**p = 0.0005**. The mechanism case on this benchmark with
this model is closed.

But the case is open across two natural axes:

1. **Benchmark-change:** Does the filter effect transfer to a
   different benchmark? exp003b addressed this for
   FORKLAND-BENCH-001 with Protocol 2; that benchmark's
   floor (arm N pass@5 = 0.84) made it uninformative on
   mechanism. **Closed (sort of):** the audit's Protocol-2
   fix is consistent with exp006 + exp007's direction but
   FORKLAND-BENCH-001's floor prevents statistical confirmation.

2. **Model-change:** Does the filter effect transfer to a
   different LLM? This is the v8 question.

A model-change replication is the last **substantively
novel** question the §10 "still open" list contains (modulo
long-horizon forkling evolution data and multi-environment
runs, which are not discrete experiments). v6 §6 originally
listed `qwen2.5-coder:7b` as the natural model-swap fallback
— same vendor lineage, one tier larger — but v6 §6 also set
the bar for invoking 7b at "≥16 GB VRAM hardware available,"
which is **not** the test hardware (4 GB VRAM). Per
`MODEL_DECISION.md`, 7b partial-offloads on 4 GB VRAM and
runs at 5–6× the per-call latency of 3b, making it
operationally untenable.

So this experiment does **not** use `qwen2.5-coder:7b`. It
uses the small models that *do* fit on 4 GB VRAM. v8 is a
four-model matrix:

| cell | model | size | source |
|------|-------|------|--------|
| qwen-3b-coder | qwen2.5-coder:3b | 1.9 GB | already local; re-use exp006 + exp007 |
| qwen-4b | qwen3:4b | 2.5 GB | already local; one generation newer, general-purpose |
| llama-3b | llama3.2:3b | 2.0 GB | already local; different family |
| llama-1b | llama3.2:1b | ~1.3 GB | **needs pull**; smallest llama; known risk on JSON-output structure at 1B params |

The four-model lineup covers (a) re-use of the existing
mechanism-result model, (b) a generation-newer qwen at a
slightly larger size, (c) a different family (llama) at
matching size, and (d) a within-family scale-down (llama
3b → 1b). The framing is: **does the filter effect hold
across LLM families and sizes, or is it specific to
qwen2.5-coder:3b?**

---

## 1. The question

**Does the filter effect (P > N on `returned_pass`)
generalize across LLM models?**

**Primary:** within each new model, paired Wilcoxon signed-rank
on per-task P − N differences, α = 0.05.

**Secondary:** combined-sample Wilcoxon across all cells
(qwen-3b-coder at 2 seeds, others at 1 seed each = 30
datapoints at the (task, seed) level when present, 24 if
llama-1b is dropped — see §7.1).

**Exploratory:** per-model I vs P (the primary from exp006 +
exp007) and per-model sign test on the direction of P − N
across models.

---

## 2. The benchmark

`bench/FORKLAND-BENCH-002.jsonl` — the SAME frozen manifest
written by `scripts/freeze_bench_002.py --calibration
results/exp006_calibration.json` during exp006, committed at
`a201e78`. Not re-derived for v8. Not re-validated for v8.
6 tasks: 006 merge-intervals, 008 flatten, 011
insert-position, 012 wrap-text, 013 binary-search, 017
rotate-array. Each passes `bench/validate_bench.py --strict`.

Calibration is **not** re-run; the manifest is the artifact.

---

## 3. The arms (unchanged from v6 / v7)

Four arms. K = 10 LLM calls per (task, arm, replicate). S = 5
replicates per (task, arm). Same N, P, I, R prompt structure
as v6 §3.

---

## 4. The endpoint and statistics (unchanged from v6 / v7)

- **Primary endpoint:** `returned_pass` for each (task, arm,
  replicate). Mean of S = 5 replicates per task per arm.
- `pass@1/5/10` (any-draw) computed and reported for
  continuity, not used for any hypothesis test.
- **Test:** exact two-sided Wilcoxon signed-rank on per-task
  paired differences. Alpha = 0.05. Effect size: mean
  per-task difference with 10,000-resample bootstrap CI.
- **Significance:** the per-model test is the registered
  primary; the combined-sample is a registered secondary
  (analogous to v7 §4.2).

---

## 5. Hypotheses

**H1 (primary, per model):** mean `returned_pass(P)` > mean
`returned_pass(N)` for the given model, Wilcoxon signed-rank,
p < 0.05.

**H0:** no difference at alpha = 0.05 within that model.

**Combined-sample H1 (registered secondary):** across all
(model, seed) cells, mean `returned_pass(P) − returned_pass(N)`
> 0, Wilcoxon signed-rank, p < 0.05.

### Interpretation rules

| per-model primary | combined-sample secondary | interpretation |
|---|---|---|
| ≥ 3 of 4 models p<0.05 in expected direction | combined p<0.05 | **Invariant** (filter holds across model families and sizes) |
| 2 of 4 models p<0.05; rest n.s. | combined p<0.05 | **Mostly invariant** (some models are noisier; mechanism holds in the population) |
| 2 of 4 models p<0.05 | combined p≥0.05 | **Mixed** (filter holds in some models but not in the pooled sample) |
| 1 of 4 models p<0.05 | combined p≥0.05 | **Model-specific** (filter is a property of one model, not the population) |
| 0 of 4 models p<0.05 | combined p≥0.05 | **Not a general property** (the filter finding is qwen2.5-coder:3b-specific, possibly a quirk) |

The pre-registered primary cell is the **qwen-3b-coder** row
(re-using exp006 + exp007 data, which is already on file).
The three new-model cells are the substantive test of the
model-invariance claim.

Honest null acceptance: if any or all of the new models
return NULL, that is the result. v8 does not require all
four cells to be positive to publish; honest reporting of
which models replicate and which do not is the
contribution.

---

## 6. Models and seeds

| cell | model | new / reused | seed(s) | notes |
|------|-------|---|---|---|
| qwen-3b-coder | qwen2.5-coder:3b | **reused** | 20261025 (exp006), 20261030 (exp007) | existing data, n=12 |
| qwen-4b | qwen3:4b | **new** | 20261101 | one generation newer, larger; same vendor lineage |
| llama-3b | llama3.2:3b | **new** | 20261102 | different family (Meta), matching size |
| llama-1b | llama3.2:1b | **new** | 20261103 | same family, smaller; subject to §7.1 parse-ok check |

**Seeds are pre-registered and different across cells.** Each
new seed is unique relative to exp006 (20261025), exp007
(20261030), and exp003b (20261031). PYTHONHASHSEED is set to
match the run seed per cell.

**Single seed per new model.** The within-model test has n=6
tasks, so power is bounded (we saw exp006's per-seed
P-vs-N p=0.031 and exp007's p=0.063 — both at the α
boundary). The combined-sample across cells is the
registered load-bearing step.

No silent fallback. If a model fails the §7.1 parse-ok check
and is dropped, the analysis runs on the remaining cells and
the dropped model is named in the report.

---

## 7. Harness, calibration, parse-ok fallback

**Harness:** Protocol 2 (`forkling/experiment2.py`). All v4r1
§7 fixes carry over without modification. **The harness
self-test gate must pass at the data-producing commit.**

### 7.1 Pre-registered parse-ok fallback for new models

`qwen3:4b`, `llama3.2:3b`, and `llama3.2:1b` have not
previously run in this harness. The 1B-parameter llama is
the most uncertain on JSON-output structure (parse_ok).
**Pre-registered rule:** before each new model's main run,
run a small calibration on the 6-task manifest, arm N only,
K = 5, S = 1 (30 calls total). If `parse_ok < 0.5`, drop
that model from the v8 main run and report the calibration
result. The drop rule is pre-registered so we do not
back-fit "we decided to keep / drop the model based on the
main-run result."

If parse_ok ≥ 0.5 in arm N, the main run proceeds for that
model. Arm N parse_ok is the proxy for all four arms; we
do not pre-register separate parse_ok checks for P, I, R
because they share the prompt base with N.

### 7.2 Re-using qwen-3b-coder

exp006 + exp007 already produced the qwen-3b-coder cell
under Protocol 2 on FORKLAND-BENCH-002 with K=10, S=5,
temperature 0.8, seeds 20261025 and 20261030. **No new
qwen-3b-coder data is collected for v8.** The combined-sample
test re-uses those per-task arm scores.

---

## 8. Stopping rule

- **Calibration (each new model):** 30 calls, ≤ 5 min on
  the smallest model. parse_ok < 0.5 → drop model.
- **Main run (each new model):** 6 tasks × 4 arms × 5
  replicates × 10 calls = 1,200 calls. ~30 min on the
  smaller models, ~50 min on qwen3:4b (thinking capability
  may add tokens).
- parse_ok < 0.5 in arm N or P of the main run → report
  and do not interpret the primary for that model.
- Timeouts + infra fallbacks > 20% of attempts in any arm
  → abort that model's main run as infra failure.

---

## 9. Reproducibility

```bash
# 0. Harness gate.
python -m pytest -q tests/test_experiment_power.py

# 1. Validate the frozen benchmark (no re-derivation).
python bench/validate_bench.py --strict --bench bench/FORKLAND-BENCH-002.jsonl

# 2. Pull llama3.2:1b if not local.
ollama pull llama3.2:1b

# 3. Per-new-model calibration (arm N, K=5, S=1, 30 calls).
for MODEL in qwen3:4b llama3.2:3b llama3.2:1b; do
  python -m forkling experiment run --protocol 2 \
    --bench bench/FORKLAND-BENCH-002.jsonl \
    --k 5 --replicates 1 --temperature 0.8 \
    --model "$MODEL" --ollama-url http://127.0.0.1:11434 \
    --seed 20261101 --arms N \
    --checkpoint results/exp008_calib_${MODEL//[:.]/_}.ckpt.jsonl \
    --out results/exp008_calib_${MODEL//[:.]/_}.json
done

# 4. Per-model main run (skip models that fail §7.1).
for tuple in "qwen3:4b:20261101" "llama3.2:3b:20261102" "llama3.2:1b:20261103"; do
  MODEL="${tuple%%:*}"
  SEED="${tuple##*:}"
  python -m forkling experiment run --protocol 2 \
    --bench bench/FORKLAND-BENCH-002.jsonl \
    --k 10 --replicates 5 --temperature 0.8 \
    --model "$MODEL" --ollama-url http://127.0.0.1:11434 \
    --seed "$SEED" --arms N,P,I,R \
    --checkpoint results/exp008_${MODEL//[:.]/_}.ckpt.jsonl \
    --out results/exp008_${MODEL//[:.]/_}.json
done

# 5. Combined-sample analysis (re-uses exp006 + exp007 for qwen-3b-coder).
python scripts/combined_sample_analysis.py \
  results/exp006.json results/exp007.json \
  results/exp008_qwen3_4b.json results/exp008_llama3_2_3b.json \
  results/exp008_llama3_2_1b.json \
  --out results/exp008_combined.json
```

(The combined_sample_analysis.py script in
`scripts/combined_sample_analysis.py` is the existing
registered-load-bearing step from v7 §4.2. It will be
extended in this commit to accept more than two result
files; that extension is itself a registered part of
v8 §9 and is documented in the script's docstring.)

---

## 10. What changes from v6 / v7

| | v6 | v7 | this document (v8) |
|---|---|---|---|
| Question, arms, endpoint, statistics, harness | same | same | same |
| Models | qwen2.5-coder:3b only | qwen2.5-coder:3b only | **qwen-3b-coder + 3 new models** |
| Seeds | 20261025 | 20261030 | qwen-3b-coder reuses (20261025, 20261030); new models 20261101, 20261102, 20261103 |
| Per-model sample size | n=6 (one seed) | n=6 | qwen-3b-coder n=12; new models n=6 each |
| Combined-sample | n/a | n=12 | **n=30** (4 cells × ~7.5 avg per cell, or n=24 if llama-1b is dropped) |
| Parse-ok fallback | n/a (one model) | n/a | **registered** for new models (§7.1) |

---

## 11. Reporting

`results/exp008_<model>.json` per cell, `results/exp008_combined.json`
for the combined-sample test, and `paper/exp008_results.md`:
- Per-cell Wilcoxon signed-rank results.
- Combined-sample test across cells.
- Per-cell parse_ok, pass@1/5/10, and returned_pass.
- §5 interpretation row matched against the observed pattern.
- **The honest outcome** — including which models replicated
  and which didn't, named explicitly.
- Whether the harness self-test passed at the data-producing
  commit.
- Whether the §7.1 parse-ok fallback was invoked on any model.

---

## 12. What we are *not* doing

- **Not** using `qwen2.5-coder:7b`. Hardware constraint (v6 §6
  fallback bar not met).
- **Not** re-running exp001–exp005. Their Protocol-1 nulls are
  recorded; re-running adds no information.
- **Not** re-running exp003b. FORKLAND-BENCH-001's floor
  prevents statistical confirmation at any model size.
- **Not** re-running exp006 + exp007. The qwen-3b-coder cell
  is reused.
- **Not** re-deriving the FORKLAND-BENCH-002 manifest. It is
  the artifact.
- **Not** re-registering the question. Mechanism is "filter
  only" per v6/v7; v8 tests generalization, not the
  mechanism.
- **Not** tuning the seeds to fit. Each new model's seed is
  pre-registered.
- **Not** silently dropping a new model. The §7.1 fallback is
  pre-registered; if invoked, the dropped model is named in
  the report.

---

## 13. Sign-off

**Sign-off:** 2026-09-28. Pre-registered before any exp008
data viewed. The hypothesis is **a model-invariance
replication of exp006 + exp007's mechanism result**; the test
is the same Wilcoxon signed-rank on per-task paired
differences, run within each new model and combined across
cells.

The mechanism question on the qwen2.5-coder:3b cell is
already answered (filter only, p = 0.0005 across two seeds).
v8 tests whether that result is **a property of the
LLM-coding-patch-selection mechanism in general, or a
property of that one model on that one benchmark at that one
training-data slice.** Either outcome — model-invariant
filter, or model-specific filter — is publishable. The
discipline is the same: committed pre-registration,
per-model honest reporting, §5 interpretation row matched to
the data.
