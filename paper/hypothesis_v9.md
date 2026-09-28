# FORKLAND Experiment 009 — Pre-registered Third-Seed + Temperature Sensitivity

**Author:** Jeremy Beebe
**Date written:** 2026-09-28
**Status:** ACTIVE — no exp009 data has been collected at
sign-off. `results/` contains no `exp009*` files.
**Supersedes:** None. v4r1, v5, v6, v7, v3b, v8 remain
operative. exp009 is a *new* registered experiment.
**Predecessors:**
- [hypothesis_v6.md](hypothesis_v6.md) — exp006, mechanism
  result on FORKLAND-BENCH-002 (filter only).
- [hypothesis_v7.md](hypothesis_v7.md) — exp007, seed-replication,
  reproduced directionally; combined-sample n=12.
- [exp006_results.md](exp006_results.md), [exp007_results.md](exp007_results.md).
- [exp008_results.md](exp008_results.md) — closed as envelope-bounded.
- [MODEL_DECISION.md](MODEL_DECISION.md).

---

## 0. Why this attempt

exp006 + exp007 closed the mechanism question on
FORKLAND-BENCH-002 with qwen2.5-coder:3b at temperature 0.8,
across two seeds. exp008 attempted model-change and closed as
envelope-bounded on 4 GB VRAM. exp003b attempted
benchmark-change and closed as floor-effect on
FORKLAND-BENCH-001.

The case is publishable on the existing n=12. But there are
two specific robustness questions that the existing record
does not address:

1. **Third-seed replication.** The mechanism is replicated
   across two seeds. Reviewers will ask "did you try a
   third?" The current n=12 has power for the headline
   (P − N p=0.0005) but a third seed tightens the CI further
   and moves the claim from "replicated at two seeds" to
   "replicated at three."

2. **Temperature sensitivity.** exp006 + exp007 used
   temperature 0.8. The mechanism (filter-only) is a
   property of LLM patch generation + selection. If the
   filter effect is real and reproducible, it should hold
   at lower entropy (temperature 0.5) and higher entropy
   (temperature 1.0). If it doesn't hold at one or both
   extremes, that tells us the mechanism is
   temperature-bounded — a substantive finding, not a
   failure.

These are different questions but they share infrastructure
(same model, same benchmark, same protocol, same
statistics), so v9 pre-registers them as a single
two-question study with three new cells.

---

## 1. The questions

**Q1 (third-seed replication):** does the filter effect
replicate at a third seed (different from 20261025 and
20261030), at the same temperature 0.8?

**Q2 (temperature sensitivity):** does the filter effect
hold at temperature 0.5 (low entropy, more deterministic)
and temperature 1.0 (high entropy, more random)?

**Pre-registered cells:**

| cell | model | seed | temperature | K | S | arms |
|------|-------|------|-------------|---|---|------|
| qwen-3b-coder | qwen2.5-coder:3b | (existing) | 0.8 | 10 | 5 | N,P,I,R |
| exp006 | qwen2.5-coder:3b | 20261025 | 0.8 | 10 | 5 | N,P,I,R |
| exp007 | qwen2.5-coder:3b | 20261030 | 0.8 | 10 | 5 | N,P,I,R |
| **exp009a** | qwen2.5-coder:3b | **20261104** | **0.8** | 10 | 5 | N,P,I,R |
| **exp009b-lowT** | qwen2.5-coder:3b | **20261105** | **0.5** | 10 | 5 | N,P,I,R |
| **exp009b-highT** | qwen2.5-coder:3b | **20261106** | **1.0** | 10 | 5 | N,P,I,R |

Each new cell: 6 tasks × 4 arms × 5 replicates × 10 calls =
1,200 calls. Total new compute: 3 × 1,200 = 3,600 LLM calls.

---

## 2. The benchmark (unchanged from v6 / v7)

`bench/FORKLAND-BENCH-002.jsonl` — frozen manifest from
exp006 calibration (commit `a201e78`). Not re-derived for
v9. Validated by `bench/validate_bench.py --strict` at this
commit.

Calibration is **not** re-run (manifest already frozen; no
new model). The v8 §7.1 parse-ok fallback is **not**
applicable here because v9 uses qwen2.5-coder:3b, which has
already produced the n=12 reference data.

---

## 3. The arms, endpoint, statistics (unchanged from v6 / v7)

- Four arms. K = 10 LLM calls per (task, arm, replicate).
  S = 5 replicates per (task, arm). Same N, P, I, R prompt
  structure.
- Primary endpoint: `returned_pass` for each (task, arm,
  replicate). Mean of S replicates per task per arm.
- `pass@1/5/10` (any-draw) computed for continuity.
- Test: exact two-sided Wilcoxon signed-rank on per-task
  paired differences. α = 0.05.
- Effect size: mean per-task difference with 10,000-resample
  bootstrap CI.
- Combined-sample analysis: registered secondary, run via
  `scripts/combined_sample_analysis.py` (extended in v8 to
  accept N result files).

---

## 4. Hypotheses

### Q1 — third-seed replication

**H1a (primary):** within exp009a, mean `returned_pass(P)`
> mean `returned_pass(N)`, Wilcoxon signed-rank, p < 0.05.

**H0a:** no difference at α = 0.05 within exp009a.

**Combined-seed H1a (registered secondary):** across
exp006 + exp007 + exp009a (all at temperature 0.8), the
filter effect holds at combined n=18 per-task paired
differences, p < 0.05.

### Q2 — temperature sensitivity

**H1b-low (primary, exp009b-lowT):** within exp009b-lowT
(temperature 0.5), mean `returned_pass(P)` > mean
`returned_pass(N)`, Wilcoxon signed-rank, p < 0.05.

**H0b-low:** no difference at α = 0.05.

**H1b-high (primary, exp009b-highT):** within exp009b-highT
(temperature 1.0), mean `returned_pass(P)` > mean
`returned_pass(N)`, Wilcoxon signed-rank, p < 0.05.

**H0b-high:** no difference at α = 0.05.

### Interpretation rules

| Q1 third-seed | Q2 low-T | Q2 high-T | interpretation |
|---|---|---|---|
| p<0.05 | p<0.05 | p<0.05 | **Robust**: filter holds across seeds and temperatures |
| p<0.05 | p<0.05 | n.s. | **Mostly robust**: filter holds in low-entropy and standard; high-entropy is power-bounded |
| p<0.05 | n.s. | p<0.05 | **Mixed**: filter holds in standard and high-entropy; low-entropy shows compression (less variation, less signal) |
| p<0.05 | n.s. | n.s. | **Temperature-bounded**: filter holds at the calibrated temperature; collapses at extremes |
| n.s. | p<0.05 | p<0.05 | **Inverted third-seed**: filter would replicate at temperatures but third-seed at standard is power-bounded |
| n.s. | any | any | **Power-bounded third-seed**: third seed alone does not reach α; combined-seed (n=18) is the load-bearing step |

The **combined-seed test** at temperature 0.8 (n=18 across
exp006 + exp007 + exp009a) is the registered load-bearing
step for Q1, regardless of exp009a's individual outcome.

The **temperature sensitivity** (Q2) is reported per-cell:
each of low-T and high-T gets its own Wilcoxon test; if
both pass, the filter is temperature-robust; if either
fails, that is a substantive finding about the mechanism's
temperature envelope.

---

## 5. Models and seeds

| cell | model | new / reused | seed(s) | temperature |
|------|-------|---|---|---|
| exp006 | qwen2.5-coder:3b | reused | 20261025 | 0.8 |
| exp007 | qwen2.5-coder:3b | reused | 20261030 | 0.8 |
| exp009a | qwen2.5-coder:3b | **new** | 20261104 | 0.8 |
| exp009b-lowT | qwen2.5-coder:3b | **new** | 20261105 | 0.5 |
| exp009b-highT | qwen2.5-coder:3b | **new** | 20261106 | 1.0 |

**Seeds are pre-registered and unique** (relative to all
prior seeds: 20261025, 20261030, 20261031, 20261101,
20261102, 20261103). PYTHONHASHSEED is set to match the run
seed per cell.

**No silent fallback.** If a cell fails the §6 stopping
rule (infra > 20% or parse_ok < 0.5), it is reported and
the remaining cells continue. The combined-seed test runs
on whatever cells completed.

---

## 6. Stopping rule

- **Main run (each new cell):** 6 tasks × 4 arms × 5
  replicates × 10 calls = 1,200 calls. ~30 min on
  qwen2.5-coder:3b at temperature 0.8; possibly faster at
  0.5 (more deterministic, fewer regenerations) and slower
  at 1.0 (more variability).
- parse_ok < 0.5 in arm N or P of the main run → report
  and do not interpret the primary for that cell.
- Timeouts + infra fallbacks > 20% of attempts in any arm
  → abort that cell's main run as infra failure.

---

## 7. Reproducibility

```bash
# 0. Harness gate.
python -m pytest -q tests/test_experiment_power.py

# 1. Validate the frozen benchmark (no re-derivation).
python bench/validate_bench.py --strict --bench bench/FORKLAND-BENCH-002.jsonl

# 2. Three main runs (sequentially or interleaved; same Ollama
#    instance, same model — sequential is faster on a single GPU).
for tuple in "20261104:0.8" "20261105:0.5" "20261106:1.0"; do
  SEED="${tuple%%:*}"
  TEMP="${tuple##*:}"
  python -m forkling experiment run --protocol 2 \
    --bench bench/FORKLAND-BENCH-002.jsonl \
    --k 10 --replicates 5 --temperature "$TEMP" \
    --model qwen2.5-coder:3b --ollama-url http://127.0.0.1:11434 \
    --seed "$SEED" --arms N,P,I,R \
    --checkpoint "results/exp009_seed${SEED}_temp${TEMP}.ckpt.jsonl" \
    --resume-from "results/exp009_seed${SEED}_temp${TEMP}.ckpt.jsonl" \
    --out "results/exp009_seed${SEED}_temp${TEMP}.json"
done

# 3. Per-cell Wilcoxon summaries.
python scripts/summarize.py results/exp009_seed20261104_temp0.8.json
python scripts/summarize.py results/exp009_seed20261105_temp0.5.json
python scripts/summarize.py results/exp009_seed20261106_temp1.0.json

# 4. Combined-seed test (Q1: third-seed replication).
python scripts/combined_sample_analysis.py \
  results/exp006.json results/exp007.json \
  results/exp009_seed20261104_temp0.8.json \
  --sign-test --out results/exp009_combined_seed.json

# 5. Per-cell temperature sensitivity reporting.
python scripts/combined_sample_analysis.py \
  results/exp009_seed20261104_temp0.8.json \
  results/exp009_seed20261105_temp0.5.json \
  results/exp009_seed20261106_temp1.0.json \
  --out results/exp009_temperature.json
```

The combined_sample_analysis.py script (extended in v8 §9)
already supports N result files. The two combined-sample
analyses above use the same script with different cell sets
to answer Q1 (third-seed) and Q2 (temperature sensitivity)
separately. **We do not pool across temperatures** for the
load-bearing step because temperature is a substantive
treatment, not a nuisance variable.

---

## 8. What changes from v6 / v7

| | v6 | v7 | this document (v9) |
|---|---|---|---|
| Question, arms, endpoint, statistics | same | same | same |
| Temperature | 0.8 | 0.8 | **0.8 (third seed), 0.5 (new), 1.0 (new)** |
| Seeds at temp=0.8 | 20261025 | 20261030 | + 20261104 (new) |
| Combined-seed analysis (temp=0.8) | n/a | n=12 | **n=18 (Q1)** |
| Temperature-sensitivity cells | n/a | n/a | **2 new cells at 0.5 and 1.0 (Q2)** |
| Model | qwen2.5-coder:3b | same | same |

---

## 9. Reporting

`results/exp009_seed<SEED>_temp<TEMP>.json` per cell,
`results/exp009_combined_seed.json` for Q1,
`results/exp009_temperature.json` for Q2,
`paper/exp009_results.md` for the writeup:
- Per-cell Wilcoxon signed-rank results.
- Q1 combined-seed analysis (n=18) as registered secondary.
- Q2 per-temperature Wilcoxon; sign test across temperatures.
- §4 interpretation row matched against the observed pattern.
- **The honest outcome** — naming which cells replicated and
  which didn't.
- Whether the harness self-test passed at the data-producing
  commit.

---

## 10. What we are *not* doing

- **Not** running model-change. v8 closed that as
  envelope-bounded.
- **Not** running benchmark-change. exp003b closed that as
  floor-effect.
- **Not** re-running exp006 + exp007. Those cells are reused.
- **Not** re-deriving the FORKLAND-BENCH-002 manifest.
- **Not** tuning seeds or temperatures to fit. All three new
  cells are pre-registered.
- **Not** silently dropping a cell. If a cell fails the §6
  stopping rule, it is reported and the dropped cell is
  named in the report.

---

## 11. Sign-off

**Sign-off:** 2026-09-28. Pre-registered before any exp009
data viewed. The hypothesis is **a third-seed + temperature
sensitivity study on the existing mechanism result**; the
test is the same Wilcoxon signed-rank on per-task paired
differences, run within each new cell and combined across
the third-seed cell for Q1.

The mechanism question is preserved (filter only, p=0.0005
on n=12 across two seeds). v9 tests whether the result is
robust to (a) a third stochastic realization and (b) the
sampling-temperature parameter. Either outcome —
replication with parameter robustness, or replication with
parameter boundary — is publishable. The discipline is the
same: committed pre-registration, per-cell honest
reporting, §4 interpretation row matched to the data.
