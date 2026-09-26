# Ollama probes (historical)

One-off diagnostics from the model-selection work of 2026-09-25 that led
to [`paper/MODEL_DECISION.md`](../../paper/MODEL_DECISION.md). Kept for
provenance; nothing imports them. Each talks to a local Ollama at
`http://127.0.0.1:11434` and can be run from any directory.

| Script | What it checked |
|---|---|
| `probe_qwen.py` | Minimal prompt to reproduce the `qwen2.5-coder:7b` HTTP 500 |
| `probe_qwen2.py` | Growing prompt sizes to find the 7b failure point |
| `probe_qwen3.py` | Cold-load latency after unloading the model |
| `probe_qwen3b.py` | `qwen2.5-coder:3b` fits fully in VRAM and follows the patch schema |
| `probe_qwen_prompt.py` | Whether the 7b model follows an explicit JSON schema |

For a quick "which models are pulled" check, use `python scripts/check_ollama.py`.
