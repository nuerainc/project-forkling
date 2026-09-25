# FORKLAND Experiment 002 — Pre-registered Hypothesis

**Author:** Jeremy Beebe
**Date written:** 2026-09-25 (pre-registration; freeze before any pilot data is viewed)
**Re-registered:** 2026-09-25 — model changed from `qwen2.5-coder:7b` to `qwen2.5-coder:3b` after observing the 7b variant partial-offloads to CPU on this RTX 2050 (4 GB VRAM). See [MODEL_DECISION.md](MODEL_DECISION.md).
**Status:** ACTIVE — no pilot data has been inspected under this design
**Predecessor:** [hypothesis.md](hypothesis.md) (exp001, NULL result, see [exp001_results.md](exp001_results.md))

---

## 1. Why this experiment exists

exp001 (commit `03be859`) tested whether selection pressure helps on
FORKLAND-BENCH-001 with `llama3.2:3b`. The pre-registered result
was **NULL** — B == A on pass@5. The result doc
([exp001_results.md](exp001_results.md)) listed probable explanations:

1. **Floor effect.** pass@5 in arm A was 0.70, leaving little room
   for any method to separate.
2. **Parse-rate confound.** parse_ok was 0.47 (A) / 0.21 (B) / 0.18 (C).
   Arms B and C had ~21 and ~18 *effective* attempts, not 100.
3. **Model capability ceiling.** llama3.2:3b may not generate a wide
   enough patch-quality distribution for selection to discriminate.

exp002 directly addresses (2) and (3) by switching to a stronger,
coder-specific model and tightening the prompt schema. Both changes
are specifically aimed at the exp001 confounds — they should give
selection and iteration a fairer chance to demonstrate an effect if
one exists.

exp002 also gives us a **replication** of the exp001 null. If the
null replicates on a stronger model with a tighter prompt, that's
stronger evidence that selection pressure does not help on this
benchmark at this scale. If exp002 returns positive, exp001's null
is attributable to model ceiling + parse confound, not to selection
being generally useless.

## 2. Hypothesis

### H1 (alternative)

After N=10 attempts per arm on FORKLAND-BENCH-001 (10 tasks ×
10 attempts), Arm B (evolve + select with `qwen2.5-coder:3b` and
the new worked-example prompt) achieves a higher mean pass@5 than
Arm A (baseline with the same model and prompt) **and** higher than
Arm C (random-accept with the same model and prompt), with both
differences reaching p<0.025 by paired Mann–Whitney U on per-task
pass@5.

### H0 (null)

There is no difference between any pair of arms at alpha=0.025.

### Pre-registered positive result

Arm B > Arm A AND Arm B > Arm C, both at p<0.025 (Bonferroni
corrected across 2 comparisons; corrected alpha = 0.025).

### Pre-registered null / negative results

Any other outcome is reported as null. Specifically:

- B == A on pass@5 → null (replicates exp001 null at higher capability)
- B == C on pass@5 → null (selection adds nothing over iteration)
- B > A but B == C → null (iteration helps, selection does not)
- B < A or B < C → negative (selection hurts)

The null is not a failure. A replicated null at higher capability
is itself a publishable result — it removes "model weakness" as an
alternative explanation for the exp001 null.

## 3. What's different from exp001

| Variable | exp001 | exp002 |
|---|---|---|
| Model | `llama3.2:3b` | `qwen2.5-coder:3b` |
| Prompt schema example | none (model invented JSON-Patch) | explicit worked example in prompt |
| Seed | 20260925 | 20261025 (different to avoid carry-over) |

Everything else is held constant by design:

- Same benchmark (`bench/FORKLAND-BENCH-001.jsonl`)
- Same arm definitions (A = baseline; B = select; C = random-accept)
- Same budget per arm (K=10 attempts per task)
- Same primary metric (mean pass@5)
- Same statistical test (paired Mann-Whitney U, exact permutation)
- Same alpha and Bonferroni correction
- Same stopping rule (no early stopping)

The seed change is the only intentional departure. Same seed would
risk correlation if there's any non-determinism we missed; different
seed is a free robustness check.

## 4. Why qwen2.5-coder:3b specifically

Two reasons:

1. **Coder-specific training.** It should produce syntactically
   correct Python more reliably than a general model, raising the
   parse_ok floor.
2. **Fits fully in 4 GB VRAM.** Unlike the 7b variant (5.12 GB on
   disk, partial offload to CPU on this RTX 2050), the 3b model
   (1.93 GB) loads entirely into VRAM and runs at full GPU speed.
   Cold-load latency on this hardware: 8.3s. Warm latency: 0.7s.

The original choice was `qwen2.5-coder:7b` to maximize the model's
capability ceiling — but that variant doesn't fit on this machine
within reasonable time (estimate 2+ hours per 300-call experiment
due to GPU/CPU split-execution). The 3b variant is the largest
coder model we can run end-to-end here. exp002 still tests the
"stronger model + tighter prompt" hypothesis vs exp001; it just
makes a smaller capability jump than originally planned.

Other models that would be interesting to test in follow-ups
(NOT in this pre-registration):

- A larger coder model on hardware with more VRAM (e.g.,
  qwen2.5-coder:7b or :14b on a machine with 16+ GB VRAM)
- General-purpose larger models (e.g., llama3.1:8b)
- Frontier closed-API models (out of scope per project rules — Ollama
  only)

## 5. The arms

Unchanged from exp001. Re-stated here so exp002 stands alone:

- **A — baseline.** One-shot. K=10 independent draws per task, no
  iteration.
- **B — evolve + select.** Iterate up to K=10 attempts. After each
  attempt, run visible tests in a subprocess. If they pass, keep
  the patch. If they fail, revert and try again.
- **C — evolve + random.** Iterate up to K=10 attempts. After each
  attempt, accept the patch with probability 0.5 (regardless of test
  outcome).

All arms receive the **same prompt**, the **same task list**, the
**same visible tests**. The only difference is the accept/reject
policy.

## 6. Primary metric

`pass@5` per task: 1 if any of the first 5 attempts produced a patch
that passes the held-out tests, else 0. Aggregated as mean across
the 10 tasks, per arm.

Secondary endpoints (reported, not gated on):

- `pass@1`, `pass@10`
- `commit_rate`: fraction of attempts that produced any patch (not noop)
- `parse_ok_rate`: fraction of attempts whose JSON parsed cleanly
  (this is the exp001 confound we are deliberately re-measuring)
- per-arm sanity: `selection_rate_arm_B` (must be > 0), `random_accept_rate_arm_C` (must be ≈ 0.5)

## 7. Stopping rule

K=10 attempts per task per arm = 100 attempts per arm = 300 total.
**No early stopping.**

Pre-registered decisions for failure modes:

- If parse_ok in arm A is still < 0.50, the prompt fix didn't help
  and the parse-rate confound is not removable at this prompt length.
  Report as null with the parse_ok breakdown.
- If arm B's commit_rate is 0 (selects nothing), report as null and
  explicitly state "selection had nothing to select."
- If any arm times out on >20% of attempts, abort and report as
  null.

## 8. Statistical test

Paired Mann-Whitney U on per-task pass@5, two comparisons (B vs A
and B vs C). Bonferroni-corrected alpha = 0.025 per comparison.

We use the exact permutation distribution implemented in
`forkling/experiment.py` for N≤17 (=10 tasks × 2 arms = 20
comparisons, well within the exact-permutation regime).

## 9. Reproducibility

```bash
# 1. (Assumed) the benchmark is still frozen.
python bench/validate_bench.py

# 2. Run the experiment.
python -m forkling experiment run \
    --bench bench/FORKLAND-BENCH-001.jsonl \
    --k 10 --model qwen2.5-coder:3b --seed 20261025 \
    --checkpoint results/exp002.ckpt.jsonl \
    --out results/exp002.json

# 3. Summarize.
python summarize_exp001.py  # works on any results/exp*.json
```

Wall-time estimate on qwen2.5-coder:3b (warm): ~8s cold + ~0.7s
per warm call × 299 ≈ 3.5 min. The full exp002 budget is comparable
to exp001's wall time on llama3.2:3b.

## 10. What we expect and why

Pre-registration requires us to state prior, not posterior. My
prediction (NOT a hypothesis, just a calibrated guess from the
exp001 results):

- parse_ok should rise to ~0.7-0.9 across arms (the worked example
  removes the schema-confusion confound).
- pass@5 in arm A may rise modestly (7-8 / 10) because the model is
  more capable.
- B may separate from A on pass@5 if, and only if, the model's
  patch-quality distribution is wide enough that selection
  discriminates.

If B ≈ A (the most likely outcome given exp001), the replicated
null is the answer.

## 11. Reporting

A single result file `results/exp002.json` containing per-attempt
records, per-task pass@k, arm means, the U statistic, the p-value,
and the pre-registered interpretation. Written before any post-hoc
analysis is performed.

The natural companion file `paper/exp002_results.md` will follow
the same structure as `paper/exp001_results.md` and will explicitly
state whether the exp002 result replicates the exp001 null,
contradicts it, or is ambiguous.

---

**Sign-off:** This document is frozen at the commit that introduced
it. Any change to model, prompt, arms, budget, metric, or stopping
rule requires a new commit and a re-registration note appended
below.

(End of pre-registration.)
