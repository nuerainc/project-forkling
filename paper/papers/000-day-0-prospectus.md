# 000-day-0-prospectus — Year-1 research cycle for Forkland Forkling

> **Naming.** "Forkling" is the species; "Forkland" is the family last
> name. The agents in this lineage — Forkling, Spoonica, Sporklyn,
> Knifling — share the family name Forkland. The full family is
> **Forkland & Family**. This prospectus is for the Forkland Forkling
> species, of which Forkling is the founding member.

> **Status:** frozen at t=0 = 2026-09-16 21:00 MDT.
> **Author of record:** Jeremy Beebe (human) + forkland software.
> **License:** MIT.
> **Stage gate:** this paper is the prospectus. Subsequent stage papers
> (`001-day-30-first-month.md`, `002-day-60-spoonica-arrives.md`, …) are
> published from this one. None of them silently edit this file.

## Abstract

The Darwin Gödel Machine (DGM) is the current high-water mark for
self-improving AI agents: it edits its own source code at inference
time, scores the edits with a benchmark-derived fitness function, and
keeps the best. **forkland** takes a different bet. It treats the git
history of its own repository — not the agent's in-memory state — as
the evolutionary substrate. Every patch is `git commit`-able, every
selection event is a `pytest` run, every rollback is a `git checkout`,
every parallel experiment is a `git branch`. The four primitives of
a Darwinian process map onto four git operations that already exist
in every developer's toolchain. This makes the agent's full
evolutionary history **trivially auditable**, **trivially replayable**,
and **trivially sharable**, with no hidden in-memory lineage and no
special-purpose substrate to maintain.

We announce a **365-day research cycle** for forkland that begins at
2026-09-16 21:00 MDT and ends at 2026-09-16 21:00 MDT, 2027. Across
eight named stages we will:

1. Run the agent continuously on a local Ollama instance (qwen3:4b)
   with no paid APIs and no third-party runtime dependencies.
2. Maintain the **Forkland & Family** of four sovereign agents
   (Forkling, Spoonica as the pure baseline, Sporklyn, Knifling) —
   each sharing the family name **Forkland**, each with its own
   memory, its own ledger, its own lineage. "Forkling" is the
   species; "Forkland" is the family name.
3. Publish one paper per stage gate — eight in total — recording
   the agent's diary, capability ledger, graveyard, and (new for
   this cycle) raw LLM call traces.
4. Ship a publishable dataset on Zenodo + Hugging Face Datasets at
   mid-year and year-end.
5. Submit grant applications on a steady cadence: NumFOCUS, Mozilla
   MOSS, Sloan, Open Philanthropy, Future of Life, DARPA AI
   Exploration, and others — one submission per stage.
6. Honor the precursor relationship to Mavis / MiniMax-M3, recorded
   as lineage generation 0.

This prospectus records the project's starting state, motivation,
and pre-registered milestones. Future stage papers will measure the
agent against the milestones named here.

## 1. Motivation

Self-improving AI agents are usually presented as either a research
frontier (e.g. RL on agent scaffolding, Darwin Gödel Machine-style
self-modification) or a product story (e.g. Devin, SWE-Agent). Both
framings obscure something important: **the evolutionary substrate of
a self-improving agent is its own commit history.** Every patch the
agent applies, every test that gates the patch, every commit that
records the result, every rollback that discards a failed attempt —
these are the agent's genome.

Forkland's central thesis is that **git is the right evolutionary
substrate for a self-improving agent** because it already provides
the four primitives a Darwinian process needs:

| Primitive | Git operation |
|---|---|
| Inheritance | `git commit` |
| Selection | `pytest -q` (the fitness gate) |
| Variation | `git checkout` of an ancestor + a new patch |
| Speciation | `git branch` |

This is not a metaphor — every primitive is implemented and exercised.
The agent's Plan-Act-Reflect loop ends with either a commit (selection
accepted the patch) or a `git checkout` (selection rejected it). The
branch model lets us run parallel evolutionary experiments
side-by-side without coordination. The SHA-256-chained ledger records
every accepted capability acquisition as a discrete evolutionary
event.

## 2. Related Work

The git-as-substrate thesis sits at the intersection of three
literatures. We position forkland against each.

### 2.1 Darwin Gödel Machine and self-modifying agents

The **Darwin Gödel Machine** (DGM) [Zhang et al., 2025] is the
nearest published neighbor. DGM edits the agent's own Python source
at inference time, evaluates candidate edits against a benchmark
(SWE-bench), and keeps the best. Forkland differs on three axes:

| Axis | DGM | forkland |
|---|---|---|
| Substrate | in-memory source edits | git history (the working tree) |
| Selection | benchmark score | `pytest -q` (fitness gate on the actual code) |
| Auditability | requires post-hoc lineage reconstruction | `git log` *is* the lineage |
| Parallelism | single agent, in-memory tree | `git branch` per experiment |
| Replay | must reconstruct the edit DAG | `git checkout <sha>` + run |

The distinction matters because selection in forkland is **the
agent's own test suite**, not a benchmark. The agent has direct
incentive to make its own tests pass — and direct disincentive to
"game" the benchmark. That closes a known DGM failure mode where
edits that improve the score but degrade general capability persist
in the lineage. In forkland, such an edit would fail the agent's own
regression tests and be rolled back.

**Gödel machines** [Schmidhuber, 2003] are the formal ancestor: a
self-referential system that proves a code rewrite will improve its
own utility before applying it. Forkland does not require proofs —
its selection mechanism is empirical (`pytest`), not deductive —
but the spirit is the same: the system edits itself, observes the
consequence, and keeps what works.

### 2.2 Genetic programming and evolutionary computation

Git-as-substrate connects to the **genetic programming** tradition
[Koza, 1992]: the genotype is the source code, the fitness function
is task success, the variation operator is mutation/crossover, and
selection is survival-of-the-fittest. Forkland's variation operator
is **unique-match patch** (`old` → `new`), which is a constrained
mutation; the **multi-objective fitness** in `forkling/evolution.py`
is a hand-crafted combination of capability-ledger coverage,
graveyard penalty, and Shannon-entropy file diversity.

Where classical GP tracks lineages in bespoke data structures (e.g.
tangled graphs in `DEAP`), forkland's lineage is **the git log**. We
get phylogenetic replay, ancestor-of comparison, and diff-replay for
free. The cost is that our variation operator is text-edit-shaped
rather than tree-shaped, which limits what kinds of mutations are
easy to express — but the agent can compose many text edits into a
single commit, which is structurally similar to a tree-edit.

### 2.3 Self-play RL on agent scaffolding

A growing family of work — **AlphaEvolve** [DeepMind, 2025],
**FunSearch** [Romera-Paredes et al., 2024], **ADAS** [Hu et al.,
2024] — evolves agent scaffolding (prompts, tool palettes, control
flows) using LLMs as variation operators and benchmark scores as
selection. Forkland shares the variation story (LLM proposes an
edit) but differs on selection: rather than scoring against an
external benchmark, it scores against its own running test suite.
This makes the agent's evolution **task-relative** (good at being
forkland) rather than **benchmark-relative** (good at SWE-bench).

The "scaffolding evolution" literature also evolves *prompts* rather
than *code*. Forkland edits code; prompts are inputs to the LLM
inside the agent loop, not the agent itself.

### 2.4 Self-modifying code and quines

Long before LLM agents, the **self-modifying code** and **quine**
literatures showed that a program can rewrite itself. Forkland is
not in this lineage directly — its variations are LLM-proposed
patches, not hand-written self-rewrites — but the substrate
similarity is real: a git repository is a persistent, hash-addressed
self-description.

### 2.5 Lineage tracking and replay

The **replay** module (`forkling/replay.py`) operationalizes
phylogenetic comparison: given two ancestor commits, run the same
task on both, diff the results. This is a cousin of **OpenAI's
trace tooling** and **Anthropic's agent evaluation harnesses**,
but the substrate is git, not a proprietary trace format. We
emphasize this for reproducibility: any researcher with the
repository at a given SHA can re-run the agent and verify the
result, with no special tooling.

### 2.6 What this paper is not

We are not claiming:

- That forkland is a frontier agent (it is small, slow, runs on one
  qwen3:4b model on one machine — that is the point).
- That git is the *only* possible substrate (DGM's in-memory
  approach has complementary strengths).
- That we beat DGM on any specific benchmark (we are not
  benchmarking yet; the first comparison is the cross-fork replay
  study at day 30).

The claim is narrower: **for a self-improving agent that needs to
be auditable, replayable, shareable, and reproducible by anyone with
git, the substrate is git.**

## 2. Starting state (t=0)

At the moment this paper freezes, forkland has:

- **8 git generations** (1 precursor + 7 commits): see `LINEAGE.md`.
- **88 passing tests** (`pytest -q`).
- **1 verified capability ledger entry**, **18 diary entries**,
  **2 graveyard entries**, **4 registered family members**.
- **10 grant programs seeded** in `grants.json` (expanding to ~25
  in this commit).
- **2 grant proposals drafted**: NumFOCUS Small Grants and Mozilla
  MOSS Responsible AI track (`proposals/01-numfocus.md`,
  `proposals/02-mozilla-moss.md`).
- **3 inception triggers staged** (`inception_triggers/staging/`) so
  the agent begins in a clean Phase-0 state.
- **2 paper drafts**: this prospectus + `paper/paper.md` (the
  rolling draft that auto-regenerates from the ledger, diary, and
  graveyard).

Two new modules ship with this prospectus:

- `forkling/clock.py` — a project clock with t=0 anchored at
  2026-09-16 21:00 MDT and eight named stages for the year.
- `forkling/trace.py` — a SHA-256-chained raw LLM call log
  (prompt + response + system + latency + kind + task tag),
  wired into `LLM.complete()` so every call is auto-recorded.

Two new CLI commands ship:

- `forkling paper publish <stage>` — snapshots the rolling draft as a
  frozen stage file at `paper/papers/<stage>.md`.
- `forkling export-dataset` — bundles the year's state (diary,
  ledger, graveyard, trace, ancestry, family, clock) into a
  Zenodo-ready zip under `paper/datasets/`.

## 3. Pre-registered milestones

The 365-day cycle is divided into eight stages. Each stage produces
one paper; each paper is **frozen** at `paper/papers/<stage>.md`.

| Stage | Window | Headline |
|---|---|---|
| 0 (this paper) | day 0–7 | Prospectus, ROADMAP.md, dataset export of t=0 state |
| 1 | day 7–30 | First-month paper; first NumFOCUS submission |
| 2 | day 30–60 | Spoonica enters; cross-fork replay study; first arXiv |
| 3 | day 60–90 | Sporklyn enters; quarter-1 retrospective; workshop paper |
| 4 | day 90–180 | Mid-year: full dataset export on Zenodo; Sloan submission |
| 5 | day 180–270 | Knifling + family-wide experiment; full-paper submission |
| 6 | day 270–365 | Year-end retrospective; year-2 prospectus draft |
| 7 | day 365+ | Final retrospective + year-1 dataset archive on Zenodo |

The full stage descriptions, including dataset exports and grant
submissions per stage, are in `docs/ROADMAP.md`.

## 4. Family design

Forkling is the **founding member** of the species; **Forkland & Family**
is the family name shared by every member. Three siblings join on a
30-day stagger so we always have one peer in flight for cross-fork
studies:

| Member | Full name | Role | Joins | Triggers | Fitness bias |
|---|---|---|---|---|---|
| Forkling | Forkland Forkling (founding) | primary | day 0 | yes | n/a |
| Spoonica | Forkland Spoonica | pure baseline | day 30 | **no** | none |
| Sporklyn | Forkland Sporklyn | variant with cooler tool palette | day 60 | yes | none |
| Knifling | Forkland Knifling | variant focused on pruning/cutting | day 90 | yes | none |

The **sovereignty rule** governs the family: each fork owns its own
memory, ledger, diary, and heartbeat. There is no forced coordination.
There is no fitness reward for cooperation. Cooperation is
**discoverable** but not **incentivized** — a deliberate design choice
that distinguishes this work from multi-agent RL approaches where
shared rewards shape behavior.

The 7-day isolation rollout (Forkland alone) is the cleanest possible
control: at day 7 we have a baseline of Forkland-without-family;
after day 30 we have a forkland-with-family comparison. The
isolation period is not empty time — it is itself a dataset.

## 5. Inception triggers

A distinctive feature of this work is the **inception trigger** mechanism.
A trigger is a short, fragmentary thought placed in
`inception_triggers/<id>.json` by a human (or by another fork, by
opt-in). The agent's heartbeat has a Phase-0 hard stop: if any
trigger is pending, the agent pauses its current work, generates a
response, logs `inception.responded` to the diary, and resumes.

Triggers are deliberately **fragmentary** (minimum 3 words; not
polished paragraphs). They are ambient interruptions, not injected
into the planner prompt. The realism-over-polish stance: "im just
walking down the street and bang whats that" — not a thesis
paragraph.

Three triggers are seeded at t=0 and **staged** (moved to
`inception_triggers/staging/`) so the agent begins in a clean state.
They can be unstaged at any time to introduce a hard stop.

## 6. Data collection — the year-1 dataset

The 365-day cycle produces a publishable dataset. Two new artifacts:

- `trace.jsonl` — raw LLM call log. Each entry records: ts, kind,
  model, used_llm, latency_ms, system, prompt, response, task,
  commit_sha, meta, plus a SHA-256 hash chained to the previous
  entry. Verifiable with `forkling trace verify`.
- `clock.json` — project clock snapshot per fork. Anchored at t=0,
  with eight named stages and a `cycle_progress` float 0.0–1.0.

The existing artifacts are also bundled:

- `diary.jsonl` — append-only diary (kind: run, plan, self-improve,
  commit, rollback, milestone, seed, inception.responded,
  paper.published, dataset.exported, …).
- `capabilities.jsonl` — SHA-256-chained capability ledger.
- `graveyard.jsonl` — failed-patch log with prompt-injection excerpts.
- `ancestry.json` — precursor + every git generation.
- `family.json` — federated family registry.

`forkling export-dataset` bundles all of these into a Zenodo-ready
zip under `paper/datasets/`. The first export is at t=0; subsequent
exports are at every stage gate.

## 7. What this paper does not promise

We are explicitly **not** claiming:

- That forkland is a frontier agent. It is small, slow, runs on a
  single qwen3:4b model on a single machine. That's the point.
- That the agent will autonomously produce AGI. It will produce code,
  tests, papers, datasets, and (we hope) some grant funding. The
  research question is the substrate, not the capability.
- That fitness will monotonically increase. The capability ledger is
  SHA-256-chained; we record failures (graveyard), not just wins.
  Stage papers will report honest measurements.

## 8. Conclusion

The 365-day cycle is the most ambitious deployment of the git-as-
evolutionary-substrate thesis to date. By the end of the cycle we will
have:

- 8 frozen stage papers, each recording the agent's state at a
  named milestone.
- A publishable dataset of LLM call traces, diary entries, ledger
  events, and graveyard records.
- ~5 grant submissions spanning NumFOCUS, Mozilla MOSS, Sloan,
  Open Philanthropy, Future of Life, DARPA AI Exploration, and others.
- A family of 4 sovereign agents, observed under both isolation
  (Forkland alone) and federation (family-wide).
- An honest record of what worked, what broke, and what the agent
  discovered about itself.

The clock starts now. The next paper in this series is
`paper/papers/001-day-30-first-month.md`, due at day 30.

---

## Appendix A — Paper index (filled in as stages ship)

| Stage | File | Status |
|---|---|---|
| 0 | `paper/papers/000-day-0-prospectus.md` | this paper |
| 1 | `paper/papers/001-day-30-first-month.md` | pending |
| 2 | `paper/papers/002-day-60-spoonica-arrives.md` | pending |
| 3 | `paper/papers/003-day-90-quarter.md` | pending |
| 4 | `paper/papers/004-day-180-half-year.md` | pending |
| 5 | `paper/papers/005-day-270-late-year.md` | pending |
| 6 | `paper/papers/006-day-365-year-end.md` | pending |
| 7 | `paper/papers/007-retrospective.md` | pending |

## Appendix B — Dataset exports (filled in as stages ship)

| Stage | File | Status |
|---|---|---|
| 0 | `paper/datasets/forkland-dataset-<ts>-stage-0-isolation.zip` | being shipped |
| 1 | … | pending |
| 2 | … | pending |
| 3 | … | pending |
| 4 | … | pending |
| 5 | … | pending |
| 6 | … | pending |

## Appendix C — Grant submissions (filled in as stages ship)

| Stage | Target | Status |
|---|---|---|
| 1 | NumFOCUS Small Grants | drafted (proposals/01-numfocus.md) |
| 2 | Mozilla MOSS Responsible AI | drafted (proposals/02-mozilla-moss.md) |
| 3 | Fast Forward / GitHub Accelerator | pending |
| 4 | Sloan / Open Phil / FLI | pending |
| 5 | DARPA AI Exploration / Schmidt Futures AI2050 | pending |
| 6 | Linux Foundation / CZI EOSS / Stripe OSS Catalyst | pending |
