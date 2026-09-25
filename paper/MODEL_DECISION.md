# FORKLAND Model Decision — 2026-09-25

## TL;DR

All future FORKLAND experiments (exp002 onward) will use
**`qwen2.5-coder:3b`** as the default model. The historical exp001
result (on `llama3.2:3b`) is preserved unchanged.

## Why

| Candidate | Disk | VRAM residency on RTX 2050 (4 GB) | Speed | Coder-specific? |
|---|---|---|---|---|
| `llama3.2:3b` | 2.02 GB | 100% | warm ~2–3 s/call | no |
| `qwen2.5-coder:3b` | 1.93 GB | 100% | warm ~0.7 s/call | **yes** |
| `qwen2.5-coder:7b` | 5.12 GB | partial (~44% in VRAM) | warm ~5–6 s/call + CPU bottleneck | **yes** |
| `qwen3:4b` | 2.50 GB | 100% | warm ~3–4 s/call | no |

`qwen2.5-coder:3b` is the largest coder-specific model that fits
fully in 4 GB VRAM. It's faster than `llama3.2:3b` (smaller model
with better architecture for code), coder-specific (the whole
reason for the model swap), and avoids the partial-CPU-offload
trap that killed the original exp002 attempt.

## What was tried

The first exp002 attempt used `qwen2.5-coder:7b` per the
originally registered hypothesis. The model is 5.12 GB on disk
but the GPU only has 4 GB VRAM, so Ollama split-loaded it: 2.28 GB
on GPU, 2.84 GB on CPU. The process ran for ~98 minutes making
calls before being killed by an unrelated task cleanup. During
that time GPU utilization was 54% (its share was busy) and CPU
was mostly idle (its share was bottleneck). Per-token inference
required GPU+CPU coordination, which made every call much slower
than expected — about 5–6 s per call instead of the probe's 0.5 s
warm estimate.

Process priority changes had no effect because python wasn't the
bottleneck. The bottleneck was GPU+CPU split-execution.

## What changed

- `paper/hypothesis_v2.md` — re-registered to use `qwen2.5-coder:3b`.
  The hypothesis text and primary metric are unchanged; only the
  model field.
- `paper/hypothesis_v3.md` — same.
- `paper/hypothesis.md` — **unchanged.** That doc describes the
  original exp001, which actually ran on `llama3.2:3b`. Editing it
  would be revising history.

## Open follow-ups (NOT pre-registered)

- **Larger hardware test.** Re-run exp002 on hardware with ≥16 GB
  VRAM, restoring the original `qwen2.5-coder:7b` model. Would
  test the "does a meaningfully stronger model change the result"
  question directly.
- **Bigger coder on this hardware.** Try `qwen2.5-coder:1.5b` if
  it's faster and produces comparable parse-rates — useful for
  rapid iteration but loses capability.
- **Compute-budget scaling.** Re-run with `K=20` or `K=50` on the
  same model, to test whether more iterations amplify or wash out
  the selection signal.
