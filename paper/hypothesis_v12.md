# Hypothesis v12 — Hardware-invariance replication (Azure T4, 16 GB VRAM)

**Registered:** 2026-09-28
**Status:** PRE-REGISTERED — no pilot data viewed
**Complements:** `hypothesis_v11.md` (backend-invariance, local 4 GB)

---

## §1. Motivation

Two replication axes are now open after exp009a:

| axis | question | experiment | status |
|---|---|---|---|
| **backend** | Is the filter-only result a property of the protocol, or of Ollama? | exp011 (v11) | llama.cpp server, 4 GB |
| **hardware** | Is the result a property of the protocol, or of the 4 GB envelope? | exp012 (v12) | **this doc** — Azure T4, 16 GB |

**v12 changes hardware AND compute density.** The Azure T4 has 16 GB
VRAM and we run `llama.cpp --parallel 8` (8 concurrent decoding
slots, 512 tokens KV each at `-c 4096`). exp009a ran Ollama serially
at 4 GB. Three things change at once:

1. Backend (Ollama → llama.cpp) — same axis as v11
2. VRAM (4 GB → 16 GB)
3. **Concurrency (serial → 8-way parallel)** — this is the novel axis

**Why concurrency is scientifically interesting here, not just
operationally:** the exp009a writeup's post-hoc mechanism hypothesis
was that "arm I terminates early (calls = 6.5 vs P's 10.0), so its
early-stop leaves signal on the table." That hypothesis is about
**compute-budget accounting inside a single arm.** Under 8-way
parallel execution, wall-clock is decoupled from call count, so:

- If I's underperformance is a **budget-accounting artifact**, more
  slots should let I's iterations actually run and the I − P gap
  should *shrink*.
- If I's underperformance is a **protocol property** (iteration
  genuinely doesn't help), the gap should *persist*.

This is a falsifiable prediction, registered before data. It's the
first experiment in the project that tests a *mechanistic*
explanation rather than just replicating a headline.

---

## §2. Design

### §2.1 Compute tier

```
compute_tier: azure-t4-freetrial
instance:     Standard_NC4as_T4_v3  (4 vCPU, 16 GB VRAM, 28 GB RAM)
region:       East US
priority:     Spot
eviction:     Stop/Deallocate   (disk survives; ckpt survives)
backend:      llama.cpp server (llama-server)
flags:        -c 4096 --parallel 8 -ngl 99
subscription: Azure Free Trial ($193.25, 22-day window from activation)
```

Recorded in the result file as `"compute_tier": "azure-t4-freetrial"`
per `docs/BACKENDS.md` §Compute tiers.

### §2.2 What changes vs exp011

| dimension | exp011 (v11) | exp012 (v12) |
|---|---|---|
| backend | llama.cpp | llama.cpp (**unchanged**) |
| hardware | 4 GB local | **16 GB Azure T4** |
| `--parallel` | 2 | **8** |
| per-slot ctx | 2048 | 512 |
| protocol | 2 | **unchanged** |
| benchmark | FORKLAND-BENCH-002 | **unchanged** (frozen `a201e78`) |
| arms / K / replicates | N,P,I,R / 10 / 5 | **unchanged** |
| temperature | 0.8 | **unchanged** |
| **seed** | 20261107 | **20261108** |

**The 2 → 8 parallel change is the only experimental manipulation.**
Backend, protocol, benchmark, arms, K, replicates, temperature are
all held fixed. That makes v12 a clean single-variable test of
concurrency.

---

## §3. Hypotheses

### H1 (PRIMARY) — mechanism replicates at 16 GB / 8-way

> Combined-sample P − N mean (pooling 3 Ollama seeds + 1 llama.cpp
> 4 GB seed + 1 llama.cpp T4 seed = 5 seeds, n ≈ 30 per-task pairs)
> falls within ±0.10 of the established Ollama combined-sample mean
> **+0.529**, i.e. in **[+0.429, +0.629]**.

### H0 (NULL) — mechanism does not replicate

> Combined-sample P − N mean falls outside [+0.429, +0.629], OR the
> combined-sample P − N test fails to reach p < 0.05.

### H2 (SECONDARY, MECHANISTIC) — the I − P gap is a budget-accounting artifact

> If exp009a's post-hoc mechanism ("I terminates early and leaves
> signal on the table") is correct, then under 8-way parallel
> execution — where wall-clock is decoupled from call count — the
> **absolute magnitude** of I − P should shrink.

Registered as: `|mean(I − P)| at T4-parallel-8` < `|mean(I − P)| at
4 GB-parallel-2` (i.e. |−0.383| → something smaller in magnitude).

**This is a registered secondary with a directional prediction.** It is
deliberately NOT primary: a non-shrinking gap would not falsify H1
(protocol replication), and we do not want a mechanistic probe to
undermine the load-bearing claim.

### S1 (SECONDARY) — parse_ok does not degrade under 8-way

> I-arm `parse_ok` ≥ 0.85 at T4-parallel-8. A drop would indicate KV
> pressure or slot-contention artifacts, not a protocol effect.

Per-slot ctx drops from 2048 → 512. If that truncates our 1–2 K-token
prompts, parse_ok craters and the whole run is a configuration
failure, not a data point. This is the canary.

---

## §4. Metrics

**Primary:** combined-sample P − N paired difference, computed exactly
as in `scripts/combined_sample_analysis.py` (Wilcoxon signed-rank,
two-sided, zeros dropped, ties mid-ranked, exact permutation for
n ≤ 14, 10,000-resample bootstrap CI seed 20261030).

**Secondary:**
- H2: absolute magnitude of combined-sample I − P, T4 vs local.
- Per-arm `returned_pass`, `parse_ok`, `infra`, mean `calls`.
- Wall-clock per cell (T4 should be ~8× faster per cell than the
  4 GB box; a smaller speedup means slots are contending).

---

## §5. Stopping rule

### §5.1 Pilot gate (arm N, K = 20, 1 replicate, 6 tasks)

| condition | threshold | rationale |
|---|---|---|
| parse_ok | ≥ 6 of 24 | same gate as exp004/exp005 |
| infra | = 0.00 | any infra failure means the envelope is wrong |
| per-slot ctx | startup log `n_ctx_per_seq` = 512 | config sanity |
| **parse_ok at `--parallel 1`** | ≥ 6 of 24 | **required control** |

**The `--parallel 1` control is mandatory.** It isolates "512 tokens
per slot truncates prompts" from "8-way contention degrades quality."
Without it, a parse_ok crash is ambiguous. Run the pilot twice:
once at `--parallel 1`, once at `--parallel 8`. Both must pass.

- Both pass → freeze, run main.
- `--parallel 1` passes, `--parallel 8` fails → contention, not
  context. Re-run at `--parallel 4`. If that passes, register the
  reduced parallelism as an amendment BEFORE looking at effect sizes.
- Both fail → **DEFER**, close exp012 as envelope-bounded, keep the
  v11 (parallel 2, 4 GB) result as the hardware ceiling.

### §5.2 Main run

- 6 tasks × 4 arms × K = 10 × 5 replicates = 120 cells.
- Target wall-clock: **10–20 min** on T4 spot at `--parallel 8`
  (vs 60–90 min on the 4 GB box at `--parallel 2`).
- Hard stop: 40 min wall-clock, or `infra` > 0.05 in any arm at the
  halfway checkpoint.
- Checkpoint: continuous `*.ckpt.jsonl`, spot-eviction-safe. On
  eviction, `az vm start` then `--resume-from <ckpt>`.

### §5.3 No peeking

The pilot gate is parse_ok + infra + the parallel-1 control. **Not**
effect size. The parallel-1-vs-8 comparison is a *configuration*
diagnostic and is reported as such, never as a mechanism result.

---

## §6. Cost

At T4 spot (~$0.30/hr):

| phase | wall-clock | cost |
|---|---|---|
| VM provision | 3 min | $0.02 |
| `azure_setup_llamacpp.sh` | 5 min | $0.03 |
| pilot `--parallel 1` | 2 min | $0.01 |
| pilot `--parallel 8` | 2 min | $0.01 |
| main run | 15 min | $0.08 |
| deallocate | — | $0 |
| **total** | **~30 min** | **~$0.15** |

Plus ~$7/month storage if the disk is retained. Under the $193.25
Free Trial balance with enormous margin. v11 (local, no Azure) costs
$0.

---

## §7. Known confounds, stated honestly

1. **Three variables move together** (backend + VRAM + concurrency).
   v11 isolates backend; v12 does not. Neither alone gives a clean
   hardware-only test. A v13 running Ollama on the T4 would complete
   the 2×2, but that requires Ollama on Ubuntu with GPU support and
   is a larger lift than it's worth for a methods paper. Stated as a
   limitation, not papered over.

2. **Per-slot ctx drops 2048 → 512.** Our prompts are 1–2 K tokens.
   At 512/slot, prompt *processing* will truncate or overflow. This
   is the single most likely failure mode and is why the parallel-1
   control is mandatory. If the parallel-8 pilot fails on parse_ok
   while parallel-1 passes, the answer is to raise `-c` to 8192
   (→ 1024/slot) at the cost of higher KV memory, or drop to
   `--parallel 4` at `-c 8192` (→ 2048/slot, 8 slots total needs
   ~2.5 GB KV, still fits 16 GB).

3. **Spot eviction.** 30-second warning. The ckpt pattern handles it,
   but a mid-run eviction means the resumed cells ran on a *different
   physical host*. Numerically this should be identical (same
   weights, same flags) but it is not bit-guaranteed. If ≥ 2
   evictions occur, note it in the writeup as a caveat.

4. **Batch numerics.** llama.cpp's continuous batching can produce
   slightly different floating-point results depending on how many
   other slots are active at the moment of each forward pass. Under
   temp = 0.8 this is not deterministic across slot occupancy. This
   is inherent to any batched inference and is part of what v11/v12
   are testing. It is not a bug to be fixed.

---

## §8. Decision tree after the run

```
pilot: parallel-1 parse_ok >= 6/24 AND parallel-8 parse_ok >= 6/24
  |
  +-- BOTH FAIL --> close as envelope-bounded. v11 stands as ceiling.
  |
  +-- p8 FAIL, p1 PASS --> contention. Amend to --parallel 4 (registered
  |                       before effect-size viewing), re-pilot, re-run.
  |
  +-- BOTH PASS --> main run
                    |
                    +-- combined P-N in [0.429, 0.629] --> H1
                    |     "hardware-invariance CONFIRMED at 16 GB / 8-way"
                    |     -> methods paper §3 gains both backend- and
                    |        hardware-invariance subsections
                    |     -> H2 reported as a registered mechanistic
                    |        probe, either direction
                    |
                    +-- combined P-N outside band --> H0
                          "mechanism does NOT survive the hardware jump"
                          -> report as-is. Honest null preferred.
```

---

## §9. Pre-registration commitment

Written and committed **before** any Azure pilot data was viewed and
**before** the VM was provisioned. The parallel-1 control is
registered as a mandatory gate, not an optional diagnostic. The H2
directional prediction is registered even though we expect it might
fail — a registered secondary that comes out null is still evidence
about the mechanism, which is exactly what v12 is for.

The project's standing preference: **an honest null beats a p-hacked
positive.** If T4-parallel-8 breaks the result, that is the finding.

---

## §10. Provenance

- Benchmark: `bench/FORKLAND-BENCH-002.jsonl`, frozen at `a201e78`.
- Runner: `scripts/run_llamacpp_remote.py` (`6b02f6d`).
- Server bootstrap: `scripts/azure_setup_llamacpp.sh` (`6b02f6d`).
- VM verification: `scripts/check_azure_vm.sh`.
- Azure walkthrough + NSG + `az` CLI: `docs/AZURE_SETUP.md`.
- Backend survey + compute-tier table: `docs/BACKENDS.md`.
- Analysis: `scripts/combined_sample_analysis.py`.
- Harness self-tests: `tests/test_experiment_power.py`, 20/20.
- Upstream data: `results/exp006.json`, `exp007.json`,
  `exp009_seed20261104_temp0.8.json`, `exp011` (v11).
