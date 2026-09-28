# Inference backends for Forkland experiments

> Why we run our own LLM, which local servers we evaluated, and how to
> swap Ollama for something that actually parallelizes on consumer
> hardware. Read this before launching a long experiment.

## TL;DR

We currently use **Ollama** as the local inference backend. It works,
but on a 4 GB-VRAM box it processes requests **serially** per loaded
model — no real concurrency for our `qwen2.5-coder:3b` workload.

**For batched experiments (exp006+), the right migration target is
`llama.cpp` server with `--parallel 2 --ctx-size 4096`.** It runs on
the same hardware, exposes an OpenAI-compatible HTTP API our existing
`forkling/experiment2.py` already speaks, and gives us ~1.7–1.9× wall-clock
throughput on batched calls via real concurrent decoding slots. See
[§ Migration plan](#migration-plan).

## Constraints (binding, not preferences)

| Constraint | Source | Consequence |
|---|---|---|
| **stdlib-only** | forkling is pure Python stdlib | Backend must be called via `urllib.request` or `subprocess`; no SDK pip install |
| **4 GB VRAM** | User's test box / Pi-Zero target | Heavy server stacks (vLLM, SGLang, TGI, TensorRT-LLM) are off the table |
| **Windows** | Test environment | No Linux-only features; pre-built `.exe` preferred over `make` |
| **No paid APIs** | Sovereignty posture | Cloud inference (OpenAI, Anthropic, Together, Groq) is not a fallback |
| **Reproducible** | Pre-registration discipline | Backend swap must be documented in the methods paper; numerics are not bit-identical across backends |

## Why we'd switch off Ollama

Ollama is excellent ergonomically: `ollama pull`, `ollama run`,
`/api/chat`. But for our use case (hundreds of independent LLM calls
per experiment run, all to the same loaded model) its concurrency
model is the bottleneck:

- `num_parallel` exists as a setting, but on consumer GPUs Ollama
  still serializes request decoding for a single loaded model by
  default.
- Wall-clock for an N-call experiment is roughly N × (per-call latency),
  not N / (parallelism).
- We have CPU + memory headroom we cannot use because we are
  GPU-bound on a single decoding stream.

For our experiment harness — which loops `for cell in cells: llm.call(prompt)`
with no inter-cell dependency — that is wasted throughput.

## Candidates evaluated

### Ruled out for this hardware

| Backend | Why not |
|---|---|
| **vLLM** | 180+ concurrent slots, but wants ≥16 GB VRAM and PagedAttention. At 4 GB we cannot fit even one 3B model with its KV cache to spare. |
| **exo** | Distributes inference across multiple machines. We have one box. |
| **MLX** | Apple Silicon only. |
| **TensorRT-LLM / SGLang / TGI** | Same VRAM floor as vLLM. |
| **LocalAI** | Server-of-servers over llama.cpp. Adds operational complexity without buying us anything we don't already get from llama.cpp directly. |

### Realistic at 4 GB

| Backend | Concurrency mechanism | Single-file install | Fit at 4 GB |
|---|---|---|---|
| **Ollama (current)** | `num_parallel` setting, but serial decoding per loaded model on consumer GPUs | No (background service) | Works, but not actually parallel for our 3B model |
| **llama.cpp server** (`llama-server`) | `--parallel N` / `-np N` → N concurrent request slots sharing one KV cache; continuous batching on by default; OpenAI-compatible HTTP API | Yes (single binary) | **Strongest fit.** Stdlib-callable, real concurrency, fits comfortably. |
| **koboldcpp** | `--parallelrequests N` (experimental continuous batching) + `--multiuser N`; single `.exe` (PyInstaller) | Yes (single .exe + GUI loader) | Strong runner-up. Easiest setup. Parallel mode is labeled experimental. |
| **llamafile** | Same llama.cpp core, packaged as a single self-contained file; HTTP server | Yes (one file) | Same concurrency story as llama.cpp; less actively maintained. |

## Recommendation: `llama.cpp server --parallel 2`

Three reasons:

1. **Real concurrency on this hardware.** `--parallel 2` gives us 2
   simultaneous decoding slots on the same GPU. Expected aggregate
   throughput improvement is ~1.7–1.9× on batched workloads, not the
   theoretical 2× — bandwidth contention eats some of it. Verified
   in third-party benchmarks: two parallel slots turned a 2-minute
   request into 3.5 minutes each on a laptop GPU. Throughput knob,
   not latency knob.
2. **Stdlib call surface stays identical.** `llama-server` exposes an
   OpenAI-compatible HTTP API at `/v1/chat/completions`. Our existing
   `forkling/llm.py` already calls Ollama via HTTP; the swap is a
   base-URL change plus JSON-payload tweak. No third-party Python dep.
3. **Fits the VRAM budget with margin.** `qwen2.5-coder:3b` at Q4_K_M
   is ~2.0 GB. With `--parallel 2 --ctx-size 4096`, KV cache is ~200
   MB per slot (3B model, 4096 ctx). Total: 2.0 GB model + 0.4 GB
   KV + 0.5 GB headroom = ~2.9 GB. Comfortable under 4 GB.

   `--parallel 3` would push per-slot ctx to ~1365 — too small for our
   1–2 K-token prompts. **Stick with `--parallel 2`.**

### Per-slot context math (read this before changing flags)

`--ctx-size` is the **total** KV cache budget across **all** slots,
not per-request. Per-slot context is `ctx_size / parallel`. Read the
`n_ctx_per_seq` line in the server startup log every time you change
either flag — and cross-check via `curl -s localhost:8080/props`.

| Config | Per-slot ctx | Our prompts fit? |
|---|---|---|
| `--ctx-size 4096 --parallel 1` | 4096 | yes (with room) |
| `--ctx-size 4096 --parallel 2` | 2048 | yes (tight) — **recommended** |
| `--ctx-size 8192 --parallel 2` | 4096 | yes — if we ever need longer prompts |
| `--ctx-size 4096 --parallel 3` | ~1365 | **no** — too tight |

## Migration plan

**Phase 1 — pre-reg the swap as a backend-replication step** (do this
**before** running anything on llama.cpp):

1. Write `paper/hypothesis_v11.md` declaring:
   - H1: The exp006 mechanism result (filter-only; P > N, I ≤ P) holds
     on llama.cpp server within ±0.10 effect-size tolerance at α=0.05.
   - H0: It does not.
   - Primary metric: combined-sample P − N sign test on llama.cpp, n=12.
   - Stopping rule: 200 cells per arm or 4 hr wall-clock, whichever first.
   - Pre-registered decision: if H1 holds, declare backend-replication
     success; if H0 holds, exp006 result is **Ollama-specific** and the
     methods paper §3 needs an "external validity" caveat.

2. Author `scripts/run_llamacpp_server.py`:
   - Downloads the llama.cpp `llama-server` binary to `~/.forkling/llama.cpp/`
     on first use (no winget/scoop needed).
   - Downloads the `qwen2.5-coder:3b` GGUF (Q4_K_M) from HuggingFace
     on first use.
   - Starts the server with our flags: `-m <model.gguf> -c 4096 --parallel 2 -ngl 99 --host 127.0.0.1 --port 11435`.
   - Writes a JSON heartbeat (same format as `check_smart.py` expects)
     with phase + log size + checkpoint size + llama-server `/health` ping.
   - HEALTHY / STALLED / STALE / COMPLETE verdicts on `scripts/check_llamacpp.py`.
   - Compatible with `scripts/run_smart_detached.py` orchestration.

3. Add `FORKLING_BACKEND` env var to `forkling/llm.py`:
   - `FORKLING_BACKEND=ollama` (default) → existing behavior, base URL `http://127.0.0.1:11434`.
   - `FORKLING_BACKEND=llamacpp` → base URL `http://127.0.0.1:11435`, identical request schema.

**Phase 2 — calibration on llama.cpp before main run:**

1. Arm N, K=20, S=1 on FORKLAND-BENCH-002.
2. Same stop rule as exp004/exp005: ≥6/24 in band.
3. If passes, freeze benchmark on this backend; if not, defer.

**Phase 3 — main run, exp011 = backend-replication of exp006:**

- Same 6 tasks × 4 arms × K=10 × 5 reps = 1200 cells, but
  `llama.cpp server --parallel 2`. Compare combined-sample P − N to
  exp006+exp007 combined n=12.

## Reproducibility considerations

A backend swap is **not bit-identical**. Expect:

- Different KV cache layout → slightly different numerics under
  temperature sampling (we use temp=0.8 in exp009, so seed-replication
  is already non-trivial).
- Different batching policy → response timing differs.
- The judge (`passed = (canonical in response)`) is deterministic on
  the response text, so the *metric* is identical. What changes is the
  distribution of responses.

The methods paper §3 must say which backend each experiment ran on.
The recommended convention: tag each result file with
`"backend": "ollama"` or `"backend": "llamacpp"` (the runner writes
this; experiment2 reads it). exp001–exp009 are all Ollama.

## When NOT to switch

- **Single-call experiments** (exp003b, exp008) — no concurrency to
  exploit; Ollama is fine.
- **Mid-run** — never swap backends inside an experiment. The combined-
  sample analysis (v7 §4.2) assumes a single backend per cell.
- **For the daily-evolve loop** — `forkling evolve` is single-stream
  by design (one patch at a time, gated by `pytest -q`). Ollama is
  correct there.

## Open questions

1. **Does llama.cpp's continuous batching change pass-rates vs Ollama's
   serial decoding at temp=0.8?** Hypothesis v11 will measure this
   directly via exp011.
2. **At `--parallel 2`, does KV cache pressure degrade qwen2.5-coder:3b
   response quality on long-context prompts?** Calibration pass answers
   this.
3. **Is the `n_ctx_per_seq` warning at startup noisy enough to mask real
   misconfigurations?** Worth instrumenting the launcher to fail loud
   if `n_ctx_per_seq < 2048`.
