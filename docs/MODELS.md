# Model selection for the Forkland Forkling evolution loop

> How to pick a local Ollama model for `forkling evolve`, and what
> tradeoffs each choice implies. Read this before pulling a model.

## TL;DR

**Default to `qwen3:4b`.** It's the sweet spot — coherent patches at
~30–60 s per generation, ~3 GB RAM. Lean smaller only if you need
higher cadence; lean larger only if commit rate is collapsing.

## The natural-selection model

`forkling evolve` runs continuous natural selection:

```
generation = pick target + propose patch + pytest + commit/rollback
```

Two forces shape the cycle:
- **Variation** (the LLM) — how often a viable patch is proposed.
- **Selection** (`pytest -q`) — how strict the gate is.

The LLM call duration is the natural throttle. The faster the model,
the more generations per day, the more opportunities for selection to
find something useful.

## The tradeoff matrix

| Model | Params | RAM | ~sec/gen | Patch quality | Notes |
|---|---|---|---|---|---|
| qwen3:0.6b | 0.6 B | ~0.7 GB | 3–8 | low (many noops) | floor — useful only for ablation |
| qwen3:1.7b | 1.7 B | ~1.5 GB | 8–20 | medium | fast cadence; commit rate ~30–50% of qwen3:4b |
| **qwen3:4b** (default) | 4 B | ~3 GB | 30–60 | high | sweet spot for evolve loop |
| qwen2.5-coder:3b | 3 B | ~2.5 GB | 15–30 | medium-high | code-specialized; less general reasoning |
| qwen2.5-coder:7b | 7 B | ~5 GB | 90–180 | very high | lower cadence, higher commit rate |
| qwen2.5-coder:14b | 14 B | ~10 GB | 240–600 | very high | only viable on a beefy GPU |
| phi-4-mini | 3.8 B | ~3 GB | 30–60 | medium-high | strong reasoning for size; less code-tuned |
| gemma3:4b | 4 B | ~3 GB | 30–60 | medium | alternative to qwen3 family |

Numbers are estimates on a typical CPU-only Ollama install. Real
times depend on your hardware. **Time your actual model before
committing to a 365-day cycle on it.**

## Why smaller can beat larger for the evolve loop

In natural selection, generation *count* dominates generation
*quality* for adaptation speed, **as long as selection is sharp
enough to keep the good ones**. Our selection (`pytest -q`) is sharp —
it accepts only patches that don't break the test suite. A 1.7b
model producing a valid docstring patch and a 7b model producing a
valid docstring patch get the same fitness from selection. The 1.7b
model did it in 1/5th the time, so over a fixed wall-clock window it
produces 5× more generations and therefore 5× more opportunities to
find a viable change.

The floor: if the model is too dumb, *every* generation produces a
noop or a rolled-back patch. Selection has nothing to act on. The
loop runs but nothing evolves.

## Why thinking mode is off by default

qwen3 emits a long "thinking" block by default (10–50× more tokens
than the actual answer). We disable it in `forkling/llm.py` via the
`think: false` API option for the evolve loop because:

1. The patch output is constrained (`{"old": "...", "new": "..."}`).
   A 5 000-token internal monologue followed by a 50-token patch is
   wasted inference.
2. Empirically, thinking mode is 10× slower with no measurable gain
   in commit rate. The model gets lost in its own reasoning.
3. Local inference has no per-token cost, but it does have
   wall-clock cost. We optimize for generations per hour.

If you want thinking mode on for a specific task (the prospectus
paper, a grant draft, a complex refactor), set `FORKLING_THINK=1`
in the env. It stays off by default.

## When to use a bigger model

Not for the evolve loop. Use a bigger model for:

- **One-shot deep-reasoning tasks** — `forkling ancestor consult`,
  paper drafting, grant drafts. Override `FORKLING_OLLAMA_MODEL` for
  the duration of that task only.
- **Critical correctness** — if the evolve loop is hitting
  `commit_rate < 10%` consistently, try `qwen2.5-coder:7b` for a
  few hours and see if it picks up. (It probably won't on docstring
  tweaks, but it will on harder patches.)
- **Baseline comparison** — run Forkland on 4b and Forkland on 7b
  for a week each. If 7b's higher commit rate doesn't beat 4b's
  higher cadence, that confirms the hypothesis.

## When to use a smaller model

- **High cadence experiments** — testing "does generation count
  beat quality?" Set `--model qwen3:1.7b` on Sporklyn and let it
  run for a day. Compare its commits-per-hour to Forkland's.
- **Memory-constrained hardware** — Raspberry Pi Zero (512 MB) can't
  load 4b. Drop to qwen3:1.7b or qwen3:0.6b.
- **Power-constrained / laptop-on-battery** — every parameter costs
  watts. Smaller model = longer battery.

## The model-size A/B study (stage-4 of the cycle)

This is the pre-registered experiment that the family design unlocks:

| Fork | Model | Cadence | Hypothesis |
|---|---|---|---|
| Forkling | qwen3:4b | baseline | control — current behavior |
| Spoonica | qwen3:4b | baseline | control — no triggers |
| Sporklyn | qwen3:1.7b | higher | smaller model = more generations = more adaptation? |
| Knifling | qwen2.5-coder:7b | lower | bigger model = better patches = higher commit rate? |

At day 90 (stage 3), we have the first month of data. By day 180
(stage 4), we have enough generations per fork to compare:

- `commits_per_hour = committed_count / wall_clock_hours`
- `commit_rate = committed_count / attempt_count`
- `ledger_growth = capabilities_after - capabilities_before`

The prediction is **Sporklyn beats Knifling on commits-per-hour** but
**Knifling beats Sporklyn on commit-rate and patch depth**. Both can
be true. If so, the year-1 paper has a real result: "for
self-improving agents gated by an external test suite, generation
count dominates generation quality for adaptation speed."

## Switching models mid-cycle

Per-fork, per-day. No code changes needed.

```bash
# Sporklyn: smaller model, higher cadence
ollama pull qwen3:1.7b   # one-time
FORKLING_OLLAMA_MODEL=qwen3:1.7b python -m forkling evolve start --repo /path/to/sporklyn

# Knifling: bigger model, lower cadence
ollama pull qwen2.5-coder:7b   # one-time
FORKLING_OLLAMA_MODEL=qwen2.5-coder:7b python -m forkling evolve start --repo /path/to/knifling

# or with the CLI flag
python -m forkling evolve start --repo /path/to/knifling --model qwen2.5-coder:7b
```

Forkland and Spoonica stay on `qwen3:4b` — they are the controls.

## Sovereign-mode reminder

If you set `FORKLING_SOVEREIGN=1`, only the rule-based planner is
used (no LLM at all). The evolve loop will still run, but every
generation will be a rule-based noop. Useful only for verifying
that the substrate works without a model loaded.
