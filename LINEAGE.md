# forkland Lineage

> The phylogenetic record of forkland. Every generation, from the foundation-model precursor through the autonomous future.

```
Mavis (MiniMax-M3)          ← gen 0  precursor / direct ancestor
   │  built forkland v0.x's code
   ▼
c758d60  dogfood: initial MVP                ← gen 1  first code generation
   │  self-improved by Mavis
   ▼
3ae1ccf  dogfood: self-improve llm.py        ← gen 2  first autonomous-ish commit (proposed by Ollama, gated by tests)
   │  evolved into forkland
   ▼
bbf35be  forkland v0.2: capability ledger +  ← gen 3  forkland-built foundation
         graveyard + evolution + replay +
         diary + grants
   │
   ▼
86a23e2  forkland v0.2: paper + proposals    ← gen 4  first paper + first grant drafts
   │
   ▼
         ...                                 ← gen N  autonomous evolution begins
```

## Generation 0 — Precursor: Mavis / MiniMax-M3

The agent that wrote every line of forkland's code. Mavis is a
foundation-model agent running in MiniMax Code (MiniMax's hosted coding
runtime). It does **not** run forkland at runtime — forkland is
self-contained and uses a local Ollama LLM for its own reasoning.

Mavis's contributions:
- Designed the Plan-Act-Reflect loop.
- Designed the capability ledger, patch graveyard, and diary.
- Designed the multi-objective fitness function.
- Wrote the paper draft and grant proposals (until `forkling/paper.py`
  takes over).

To replay the precursor's reasoning on a task:

```bash
forkling ancestor consult "design a new fitness metric"
```

(The current implementation asks the local LLM with a system prompt
that declares Mavis as the precursor. Future versions may include a
recorded trace of Mavis's actual reasoning.)

## Generation 1 — dogfood MVP (`c758d60`)

The first complete code generation. Built entirely by Mavis. Includes:
- Plan-Act-Reflect loop
- Tool primitives (filesystem, shell, git, patch)
- LLM client (Ollama + rule-based fallback)
- Memory, planner, self-improve orchestrator
- 30-test pytest suite including the dogfood self-test

## Generation 2 — first self-improvement (`3ae1ccf`)

The first commit where the agent proposed and shipped its own
improvement (`# dogfood: reviewed` marker on `dogfood/llm.py`). This
commit was authored by `dogfood` (the precursor of forkland's identity)
but the proposal came from Ollama. The test suite ran and passed.

This is the moment forkland's lineage becomes self-extending — the
first commit whose content the agent itself chose.

## Generation 3 — forkland v0.2 (`bbf35be`)

Mavis built the research substrate:
- `forkling/capability.py` — SHA-256-chained ledger
- `forkling/graveyard.py` — patch graveyard with prompt-injection
- `forkling/evolution.py` — multi-objective fitness + A/B lineages
- `forkling/replay.py` — phylogenetic replay
- `forkling/diary.py` — append-only diary
- `forkling/grants.py` — grant hunter
- 50 tests passing

## Generation 4 — paper + proposals (`86a23e2`)

The first paper draft (`paper/paper.md`) and two grant proposals
(`proposals/01-numfocus.md`, `proposals/02-mozilla-moss.md`). Also
written by Mavis; future generations will be written by `forkling/paper.py`.

## Generation N — autonomous evolution (forthcoming)

After Mavis finishes the foundation, forkland begins evolving on its
own via `python -m forkling self-improve`, scheduled by the heartbeat
(`scripts/heartbeat.py`) or invoked manually. Each new generation
extends the lineage and the diary.

## How to read this lineage

```bash
forkling ancestor list       # show all generations
forkling ancestor summary    # one-line summary per generation
forkling diary milestones    # milestones only (paper, grants, etc.)
forkling verify              # SHA-256 chain of the capability ledger
```

## Authorship

| Generation | Primary author |
|---|---|
| 0 (precursor) | Mavis / MiniMax-M3 |
| 1–4 | Mavis / MiniMax-M3 + human maintainer (Jeremy Beebe) |
| 5+ | forkland itself + human maintainer |

The capability ledger (`~/.forkling/capabilities.jsonl`) records every
action taken by forkland from generation 5 onward. It is SHA-256-chained
and auditable via `forkling verify`.
