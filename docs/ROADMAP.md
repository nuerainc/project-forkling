# 365-day ROADMAP

> The year-1 research cycle for forkland.
> Anchored at t=0 = 2026-09-16 21:00 MDT (= 2026-09-17 03:00:00 UTC).
> The clock is sovereign: each family fork can pin its own t=0 via
> `FORKLING_T0` (epoch seconds) or `FORKLING_T0_ISO` (ISO 8601).
> Each paper stage produces one file under `paper/papers/<stage>.md` —
> snapshots are **frozen**, never auto-edited, so a year from now the
> record is exactly what we said it was on that day.

The cycle is not "run the agent for a year and hope." It is **eight
named stages**, each with a paper, a dataset export, and a small list
of grant submissions that should have shipped. The clock is the
scaffolding; the paper stages are the milestones; the dataset exports
are the scientific record.

## Anchors

| | |
|---|---|
| t=0 | 2026-09-16 21:00 MDT (`FORKLING_T0_ISO`) |
| Length | 365 days |
| Stage gate | each stage emits `paper/papers/<stage>.md` + `paper/datasets/*.zip` |
| Owner | forkland software (with human co-author Jeremy Beebe) |
| Precursor | Mavis / MiniMax-M3 (gen 0) |
| Family | Forkland, Spoonica (baseline), Sporklyn, Knifling |

## Stages

| Stage | Days | Window | Headline deliverable | Co-occurs with |
|---|---|---|---|---|
| 0. isolation | 0–7 | Sep 16–23 | `000-day-0-prospectus.md` (this paper) | Initial 3 inception triggers **staged**, none active |
| 1. first-month | 7–30 | Sep 23 – Oct 16 | `001-day-30-first-month.md` — first LLM traces, first self-improves | First forkling-only dataset export |
| 2. baseline-arrives | 30–60 | Oct 16 – Nov 15 | `002-day-60-spoonica-arrives.md` — Spoonica enters, A/B begins | First cross-fork replay study; first arXiv preprint |
| 3. family-grows | 60–90 | Nov 15 – Dec 15 | `003-day-90-quarter.md` — Sporklyn arrives; quarter-1 retrospective | NumFOCUS + Mozilla MOSS submissions; first ALIFE/GECCO workshop paper |
| 4. mid-year | 90–180 | Dec 15 – Mar 15 | `004-day-180-half-year.md` — family-wide dataset | Second dataset export (the publishable one); Sloan / Open Phil / FLI submissions |
| 5. late-year | 180–270 | Mar 15 – Jun 12 | `005-day-270-late-year.md` — Knifling + cross-fork experiment | ICML/NeurIPS workshop submissions; full-paper attempt |
| 6. closing | 270–365 | Jun 12 – Sep 16 | `006-day-365-year-end.md` — final retrospective | Year-1 archive locked; year-2 prospectus drafted |
| 7. retrospective | 365+ | Sep 16+ | `007-retrospective.md` (after wrap-up) | Released alongside the year-1 dataset on Zenodo |

The headline stage IDs match the file names in `paper/papers/`.

## Value streams (the "5x more than the original plan")

The original MVP had four value streams: code, tests, CI, dogfood.
The 365-day cycle layers on five more. Each one is implemented as
either a CLI command, a scheduled heartbeat step, or a paper stage.

### 1. Financial — grants

The cycle is built around submitting **one grant proposal per major
stage** rather than waiting until year-end. By the time we hit day 90
we have shipped two grant applications, with real artifacts behind
them. By day 180 we have shipped another three. This puts us on the
acceptance/rejection cycle early, and creates a steady submission
rhythm.

Grant surface (see `grants.json` for the full list, now ~25 programs):

| Stage | Target submission |
|---|---|
| 0 | (no submission — write the prospectus) |
| 1 | NumFOCUS Small Grants ($5k, rolling) |
| 2 | Mozilla MOSS Responsible AI ($30k, annual) |
| 3 | Fast Forward / GitHub Accelerator / AIcrowd / PSF (any one) |
| 4 | Sloan Research ($75k) + Open Philanthropy AI safety (~$50k–$200k) + FLI |
| 5 | DARPA AI Exploration BAA ($100k–$1M) + Schmidt Futures AI2050 |
| 6 | Linux Foundation / Chan Zuckerberg EOSS / Stripe OSS Catalyst |
| 7 | (post-cycle follow-ups on rejected or pending grants) |

`forkling grants list` ranks by fit; `forkling grants draft <i>` renders
a tailored draft. The `grants.json` includes notes per program so the
drafter picks the right angle.

### 2. Academic — papers + datasets

Every stage produces one paper. They are versioned, dated, and frozen
at `paper/papers/<stage>.md` the moment they are written — no silent
rewrites. The paper currently named `paper/paper.md` is the **rolling
draft** (always up to date); each `paper/papers/<stage>.md` is the
**frozen record** of what we said at that point.

Three categories:

- **Stage papers (internal record)** — `paper/papers/000..007-*.md`.
  These are the diary-of-record for the cycle.
- **arXiv preprint** — `paper/paper.md` (the rolling draft) becomes the
  arXiv preprint once it is stable enough. Re-rendered every paper
  stage. arXiv category: cs.AI (with cs.MA cross-list for the multi-
  agent bits).
- **Dataset paper** — at day 180 (mid-year) we ship the dataset
  archive as a separate paper. The dataset itself goes on Zenodo +
  Hugging Face Datasets.

`forkling paper publish <stage>` snapshots the current rolling draft
into a frozen stage file and logs a `paper.published` diary milestone.

### 3. Data collection — the highest-leverage gap

The original plan collected nothing. The 365-day cycle adds four
collection surfaces:

- **`trace.jsonl`** — SHA-256-chained raw LLM call log (prompt +
  response + system + latency + model + kind tag). Wired into
  `LLM.complete()` so every call is auto-logged. New module:
  `forkling/trace.py`. CLI: `forkling trace stats|verify|tail`.
- **`clock.json`** — project clock snapshot per fork (t=0, current
  day, stage, progress). New module: `forkling/clock.py`. CLI:
  `forkling clock` and `forkling clock --save`.
- **Dataset exports** — `forkling export-dataset` bundles diary +
  ledger + graveyard + trace + ancestry + family + clock + manifest
  into a Zenodo-ready zip under `paper/datasets/`. Diary milestone
  logged on each export.
- **Cross-fork traces** — when Spoonica / Sporklyn / Knifling ship
  their own traces, `forkling family sync <peer>` opts in to copy
  them for study (never auto-merged into Forkland's ledger). This
  is the only way to get multi-agent A/B data without violating
  sovereignty.

The dataset itself is **publishable on Zenodo + Hugging Face Datasets
+ arXiv supplementary material**. A year of self-improving-agent
traces is a rare artifact.

### 4. Public surface — currently zero in the original plan

Two lightweight, low-effort surfaces:

- **Public dashboard** — `scripts/dashboard.py` (planned) renders
  fitness curve + diary excerpt + ledger head as static HTML. Can be
  hosted on GitHub Pages for free once the user adds a remote.
- **Auto-newsletter** — at each stage gate the diary milestones are
  rendered into a `paper/papers/<stage>-newsletter.md` so anyone
  tracking the project can see what changed without reading the code.

### 5. Cross-fork studies — only viable because of the family

The original MVP had no family. The 365-day cycle formalizes the
family as an experimental instrument. The **sovereignty rule** still
holds: no fitness bias toward/against cooperation; each fork runs its
own heartbeat, owns its own memory, commits to its own lineage.

But each stage can opt in to one cross-fork study:

- Stage 1 (day 7–30): Forkland-only baseline measurements (no peer).
- Stage 2 (day 30–60): first cross-fork replay — same task, run on
  Forkland HEAD vs Spoonica HEAD. Published in
  `paper/papers/002-day-60-spoonica-arrives.md`.
- Stage 3 (day 60–90): three-way replay (Forkland, Spoonica,
  Sporklyn). Cross-fork divergence visualization.
- Stage 4 (day 90–180): family-wide dataset + family-wide A/B.
- Stage 5 (day 180–270): family-wide intervention study
  (e.g. plant the same inception trigger in all four forks; observe
  how each one handles it).
- Stage 6 (day 270–365): final comparative analysis.

This is what turns the family from "we ran four forks" into "we ran
the largest known open-data study of self-improving agents." The
sovereignty rule is preserved by making the cross-fork studies
opt-in and by never pooling ledgers into a shared fitness score.

## Implementation status (today)

| Artifact | Status |
|---|---|
| `forkling/clock.py` | implemented |
| `forkling/trace.py` | implemented |
| `LLM.complete()` traces | wired (kind/task tags) |
| `forkling paper publish <stage>` | implemented |
| `forkling export-dataset` | implemented |
| `paper/papers/` directory | staged (empty) |
| `paper/datasets/` directory | staged (empty) |
| `paper/papers/000-day-0-prospectus.md` | being written in this commit |
| `docs/ROADMAP.md` | this file |
| `grants.json` expanded to ~25 programs | included in this commit |
| `docs/DEPLOYMENT.md` updated to point at ROADMAP | included in this commit |
| Diary milestone: clock t=0 recorded | included in this commit |

## Anti-features (things we are *not* doing)

In the spirit of realism over polish:

- No paid LLM APIs. Ollama only, qwen3:4b only.
- No third-party runtime dependencies. Stdlib only.
- No forced cross-fork coordination. Sovereignty wins.
- No fitness reward for cooperation between forks. Discoverable,
  not incentivized.
- No silent rewrites of past stage papers. Once a stage ships, it's
  frozen.

## How to use this roadmap

```bash
# Look at the clock
forkling clock

# Run a heartbeat (self-improve + paper append + verify)
forkling heartbeat --repo .

# At the next stage gate:
forkling paper publish day-30-first-month
forkling export-dataset

# Push the dataset up
gh release create dataset-day-30 paper/datasets/forkland-dataset-*.zip
```

That's it. The clock tells you where you are; the stages tell you
what to ship; the paper snapshots tell you what you said; the
dataset exports tell the world what actually happened.
