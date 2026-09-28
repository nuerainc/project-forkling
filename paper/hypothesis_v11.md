# Hypothesis v11 — Backend-invariance replication (llama.cpp, local 4 GB)

**Registered:** 2026-09-28
**Status:** PRE-REGISTERED — no pilot data viewed
**Supersedes:** nothing
**Complements:** `hypothesis_v6.md` (exp006 mechanism), `hypothesis_v7.md`
(seed replication), `hypothesis_v8.md` (combined-sample load-bearing step),
`hypothesis_v9.md` (third seed + temperature)

---

## §1. Motivation

exp006 / exp007 / exp009a establish the FORKLAND-BENCH-002 mechanism
result on **Ollama** (local 4 GB VRAM, `qwen2.5-coder:3b`, Protocol 2,
temp = 0.8). Combined-sample n = 18 (three independent seeds):

| comparison | mean | 95% CI | p |
|---|---|---|---|
| P − N (filter) | +0.529 | [+0.412, +0.647] | **0.0003** |
| I − P (loop vs rerank) | −0.383 | [−0.500, −0.283] | **0.0249** |
| I − R | +0.371 | [+0.200, +0.557] | 0.0002 |
| I − N | +0.440 | [+0.320, +0.560] | 0.0010 |

Per the v6/v7 §5 interpretation rule, this is **"filter only — and the
loop's iteration actively hurts."** The loop reduces to draw-and-rerank;
the iteration inside the loop is wasted compute.

**The open threat to this result:** every data point was produced by
one inference backend (Ollama). A reader is entitled to ask whether the
result is a property of the *protocol* or an artifact of Ollama's
specific decoding behaviour (serial request handling, specific
prompt template handling, specific stop-token behaviour, specific
quantization of `qwen2.5-coder:3b` in Ollama's own GGUF conversion).

**This experiment is the backend-invariance test.** It re-runs the
identical protocol on `llama.cpp` server (`llama-server`) on the SAME
local 4 GB box, changing only the inference engine.

**Hypothesis v12** will repeat the test on Azure T4 (16 GB VRAM,
`--parallel 8`) to separate *backend* from *hardware*. v11 isolates
the backend; v12 conflates backend + hardware but adds throughput.

---

## §2. Design

### §2.1 What changes vs exp009a

| dimension | exp009a | exp011 (this) |
|---|---|---|
| backend | Ollama | llama.cpp server (`llama-server`) |
| base URL | `http://127.0.0.1:11434` | `http://127.0.0.1:11435` |
| model | `qwen2.5-coder:3b` (Ollama GGUF) | same weights, Q4_K_M GGUF |
| hardware | 4 GB VRAM | **unchanged** (4 GB VRAM) |
| protocol | 2 | **unchanged** |
| benchmark | FORKLAND-BENCH-002 | **unchanged** (frozen at `a201e78`) |
| arms | N, P, I, R | **unchanged** |
| K (draws/arm) | 10 | **unchanged** |
| replicates | 5 | **unchanged** |
| temperature | 0.8 | **unchanged** |
| **seed** | 20261104 | **20261107** (new, to avoid seed-selection) |

### §2.2 llama.cpp server configuration

```
llama-server \
  -m qwen2.5-coder-3b-instruct-q4_k_m.gguf \
  -c 4096 \
  --parallel 2 \
  -ngl 99 \
  --host 127.0.0.1 \
  --port 11435
```

- `--parallel 2` gives 2 concurrent decoding slots (the point of the
  migration: Ollama serializes, llama.cpp does not). Per-slot context
  = `4096 / 2` = 2048 tokens, which fits our 1–2 K-token prompts.
- `-ngl 99` offloads all layers to GPU.
- Startup log line `n_ctx_per_seq` must read `2048`. If it does not,
  abort and re-flag (this is a configuration error, not a data point).

### §2.3 Why seed 20261107 and not 20261104

Reusing exp009a's seed would confound "backend changed" with
"same seed, second draw." A fresh seed keeps the two-factor design
clean: exp009a already sampled the 20261104 draw; exp011 samples a
different draw under a different engine.

---

## §3. Hypotheses

Exactly one primary. Everything else is secondary or descriptive.

### H1 (PRIMARY) — mechanism replicates across backends

> The exp006 filter-only mechanism holds under llama.cpp server.
> Specifically, at combined-sample level (n = 18 pooled per-task
> pairs across 3 seeds: 20261025/20261030/20261104 on Ollama, plus
> 20261107 on llama.cpp) for the P − N comparison:
>
> **mean paired difference falls within ±0.10 of the Ollama
> combined-sample mean (+0.529), i.e. in [+0.429, +0.629]**

### H0 (NULL) — mechanism is backend-specific

> The combined-sample P − N mean falls outside [+0.429, +0.629], OR
> the combined-sample P − N test fails to reach p < 0.05.

**Decision rule (registered before data):**
- H1 supported → declare **backend-invariance confirmed**. The
  mechanism result is a property of the protocol, not of Ollama.
  Methods paper §3 gains a "backend-invariance" subsection.
- H0 supported → declare **exp006 result is Ollama-specific**. The
  methods paper §3 gains an "external validity" caveat. This is an
  honest and publishable outcome; it is NOT a failure.

### S1 (SECONDARY) — I vs P direction holds

> The I − P combined-sample mean remains negative (≤ 0) under
> llama.cpp. Directional only; not a separate primary.

Rationale for secondary: exp009a's combined-sample I − P moved from
p = 0.0547 (n = 12) to p = 0.0249 (n = 18). The direction is stable
across all 12 non-zero task-pairs. A backend that preserved direction
but lost significance would still be informative. Not promoted to
primary to preserve power for H1.

### S2 (SECONDARY) — per-slot context is not the confound

> If `--parallel 2` per-slot context (2048) is truncating prompts, the
> I-arm parse_ok rate would drop materially below the N/P arms.
> Register the expectation: I-arm parse_ok ≥ 0.85 (matching
> exp009a's 0.70 is already the low outlier; a context-truncation
> effect would push it toward 0.4–0.5).

This is a **plausibility check on the configuration**, not a claim
about the mechanism. Its purpose is to let us distinguish "backend
changed the result" from "backend truncated the prompts and broke the
protocol."

---

## §4. Metrics

**Primary metric:** combined-sample P − N paired difference.
Computed exactly as in `scripts/combined_sample_analysis.py`:
- Per-task arm scores pooled across seeds; seeds as paired blocks.
- Wilcoxon signed-rank, two-sided, zeros dropped, ties mid-ranked.
- Exact permutation null for n ≤ 14; normal approximation above.
- 95% CI from 10,000-resample bootstrap on non-zero diffs, seed 20261030.

**Secondary metrics:**
- Combined-sample I − P (Wilcoxon, same procedure).
- Per-arm `returned_pass`, `parse_ok`, `infra`, mean `calls`.

**Descriptive:** per-seed per-task diffs, printed for eyeball comparison
against the exp006/007/009a tables.

---

## §5. Stopping rule

- **Pilot / calibration:** arm N only, K = 20, 1 replicate, 6 tasks.
  Gate: ≥ 6 of 24 responses parse OK, and `infra` = 0.00.
  - Pass → freeze benchmark on this backend, run main.
  - Fail → **DEFER** (third time; declare backend envelope-bounded
    and close exp011 as Not-Run). Do NOT keep retrying.

- **Main run:** 6 tasks × 4 arms × K = 10 × 5 replicates = 120 cells.
  Target wall-clock: 60–90 min on 4 GB with `--parallel 2`.

- **Hard stop:** if the run exceeds 3 hours wall-clock, or if
  `infra` > 0.10 in any arm at the halfway checkpoint, abort and
  close as envelope-bounded. Do not extend.

- **No peeking.** The pilot gate is a parse/infra check, not an
  effect-size check. If the pilot's P − N sign looks wrong, that is
  NOT a stopping signal — only parse_ok and infra are.

---

## §6. Power analysis

Using the harness self-test (`tests/test_experiment_power.py`, 20/20
passing) with observed exp009a parameters:

- Per-seed n_nz for P − N was 6 of 6 tasks (all non-zero). Pooled
  across 3 seeds, n_nz = 17 of 18.
- Observed per-task P − N diffs cluster in [+0.20, +1.00], mean
  +0.529, sd ≈ 0.24.
- With n = 17 non-zero paired diffs at mean +0.529, sd 0.24, the
  Wilcoxon signed-rank has power > 0.99 to detect the effect at
  α = 0.05 two-sided.
- The H1 tolerance band (±0.10 around +0.529) is ≈ 0.42 sd. A
  single-seed perturbation of 0.10 would be detectable at roughly
  20% power; the 4-seed pooled design (Ollama×3 + llama.cpp×1)
  gives substantially more.

**Honest limitation:** exp011 contributes only 1 of 4 seeds. If it
lands far off (+0.30 or +0.70), the pooled mean shifts but the
Ollama-only result is unaffected. The correct reading of exp011 is
"does adding a llama.cpp seed keep the pooled result in band," not
"is the pooled result entirely llama.cpp-driven."

---

## §7. What this experiment does NOT test

Stated explicitly to prevent over-claiming in the writeup:

1. **Hardware invariance.** v11 holds hardware at 4 GB. v12 varies it.
2. **Temperature invariance.** temp pinned at 0.8. v9's exp009b-lowT
   (temp 0.5) and exp009b-highT (temp 1.0) test that.
3. **Scale invariance.** 6 tasks, K = 10. A 50-task / K = 100 study
   would be a different paper.
4. **Whether llama.cpp is a better *product* for the forkling evolve
   loop.** This is a throughput/ ergonomics question, not a science
   question. The parallel-2 throughput claim (~1.7–1.9×) is
   engineering, and should not appear in the methods paper as a
   scientific result.
5. **Cumulative improvement (v10a).** Orthogonal arm; separate pre-reg.

---

## §8. Decision tree after the run

```
pilot gate: parse_ok >= 6/24 AND infra == 0
  |
  +-- FAIL --> close exp011 as DEFERRED (third deferral). Write
  |            paper/exp011_results.md with the gate numbers.
  |            No effect-size analysis. Move on.
  |
  +-- PASS --> run main
               |
               +-- combined P-N mean in [0.429, 0.629] --> H1
               |     -> "backend-invariance CONFIRMED"
               |     -> methods paper §3 backend-invariance subsection
               |     -> v12 (Azure T4) becomes the hardware test
               |
               +-- combined P-N mean outside band --> H0
                     -> "exp006 result is OLLAMA-SPECIFIC"
                     -> methods paper §3 external-validity caveat
                     -> v12 becomes a CONFIRMATION attempt, not a
                        replication (we now know the failure mode)
```

---

## §9. Pre-registration commitment

This document was written and committed **before** any pilot data was
viewed on llama.cpp. The pilot gate is a parse/infra check with a
fixed threshold; the effect-size analysis runs once, on the frozen
post-gate dataset, with the decision rule in §3 applied without
modification.

If the result is H0 (backend-specific), that is reported as-is. The
project's standing preference is for an honest null over a
p-hacked positive, and this experiment is no exception.

---

## §10. Provenance

- Benchmark: `bench/FORKLAND-BENCH-002.jsonl`, frozen at commit `a201e78`.
- Runner: `scripts/run_llamacpp_remote.py` (committed `6b02f6d`).
- Server bootstrap: `scripts/azure_setup_llamacpp.sh` (committed `6b02f6d`).
- VM verification: `scripts/check_azure_vm.sh` (this commit).
- Analysis: `scripts/combined_sample_analysis.py`.
- Harness self-tests: `tests/test_experiment_power.py`, 20/20 passing.
- Backend survey + migration rationale: `docs/BACKENDS.md`.
- Azure provisioning guide: `docs/AZURE_SETUP.md`.
