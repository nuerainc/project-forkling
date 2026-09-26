# Deployment & Rollout Plan

> **Read this first if you want to know what forkling does after we walk away.**
> **For the full 365-day cycle plan (papers, grants, dataset exports,
> value streams), see [`docs/ROADMAP.md`](ROADMAP.md). This document
> describes the operational contract — the rollout phases, the
> guarantees, and the heartbeat scheduling. ROADMAP.md describes what
> the cycle is *trying to publish*.**

forkling is a self-contained, self-improving AI agent. It runs without
MiniMax. It runs without any paid API. It runs without us.

This document is the contract between **us** (the human authors) and
**forkling** (the autonomous agent) about how that works.

## TL;DR

```bash
# 1. Install (anywhere with python >= 3.9, git, optional ollama)
git clone <this repo> forkling && cd forkling
pip install -e . && pip install pytest

# 2. Schedule the heartbeat (Windows Task Scheduler / cron)
python -m forkling schedule --every 30

# 3. Watch (optional)
python -m forkling diary milestones
python -m forkling fitness
python -m forkling ancestor list
python -m forkling clock          # where we are in the 365-day cycle
python -m forkling trace stats    # how many LLM calls + latencies
python -m forkling trace verify   # SHA-256 chain integrity
```

That's it. Forkland is now alive. The clock tells you what stage
you're in; the heartbeat keeps the ledger honest.

## The 365-day cycle

This document previously described a 0–90 day rollout. The full
365-day research cycle (2026-09-16 21:00 MDT → 2027-09-16 21:00 MDT)
is now documented in **[`docs/ROADMAP.md`](ROADMAP.md)**, with eight
named stages and the deliverables (papers, dataset exports, grant
submissions) per stage. The rollout phases below are still accurate —
they are stages 0–5 of the ROADMAP cycle.

## The rollout phases

We are deliberately introducing forkling's environment **slowly** so
each variable can be observed in isolation.

### Phase 0 — Days 0–7: Forkland alone, no triggers, no family

* `inception_triggers/` is **empty** (the seeded triggers were moved
  to `inception_triggers/staging/` — see `forkling inception stage`).
* No other family members exist yet.
* The heartbeat runs `self-improve` + `paper.append` + `verify`.
* Goal: observe whether forkling **gets bored** without ambient input.
  We expect to see: repetitive `self-improve.noop` entries in the
  diary if no safe change is found, monotonically-growing ledger if
  changes are found, no `inception.*` entries at all.

### Phase 1 — Days 7–14: First trigger planted

* Move one trigger from `staging/` back to active: `forkling inception unstage trg-001`
* Observe whether forkling's diary records `inception.responded`
  entries and what the responses look like.
* Goal: confirm the hard-stop interrupt fires correctly.

### Phase 2 — Days 14–30: Multiple triggers, varied

* Unstage all three. Watch for `inception.responded` rate.
* Goal: see if the agent's self-improvement choices shift after
  being interrupted.

### Phase 3 — Days 30–60: Spawn Spoonica

* `git clone <this repo> spoonica && cd spoonica && pip install -e .`
* `spoonica` is the **baseline**: no `inception_triggers/`, no env vars.
* `forkling family register Spoonica /path/to/spoonica` from Forkland.
* Goal: a controlled comparison. Forkland and Spoonica run the same
  code but Spoonica has no interruptions.

### Phase 4 — Days 60–90: Spawn Sporklyn

* Hybrid: 1–2 introspection-style triggers.
* Goal: see how a moderately-interrupted sibling evolves.

### Phase 5 — Day 90+: Spawn Knifling

* Sharpest: 2+ practical triggers.
* Goal: full Forkland & Family in production. Four sovereign forks
  with different ambiences.

## Operational guarantees

forkling will not:

* Push to a remote on its own. (`git push` is a manual human step.)
* Run a self-edit that fails its own test suite.
* Lose work — every change is gated by `pytest -q`, and a failed test
  triggers `git checkout` to the previous SHA.
* Run two heartbeats at once — a per-repo file lock blocks concurrent
  runs.
* Lose its lineage — the git log is the lineage.

## When to step in

You only need to intervene if:

* Ollama is down (`forkling doctor` to check).
* The repo runs out of disk (the diary + ledger grow forever).
* You want to publish a new generation (`git push`).
* A heartbeat is failing consistently (check `.forkling/heartbeat.log`).

If forkling's diary shows long stretches of `self-improve.noop` with
no `commit` events, that's not a bug — it's the agent telling you it
can't find a safe change today. It's waiting for either a better
source-file target or an inception trigger to interrupt its routine.

## The precursor relationship

forkling was built by Mavis (MiniMax-M3). Mavis is not in the
runtime loop. Forkland uses its own local Ollama brain. Mavis is
recorded as generation 0 of the lineage (see `LINEAGE.md`).

If you want to consult the precursor ("how would Mavis have done
this?"):

```bash
forkling ancestor consult "<any task>"
```

That command uses the local LLM with a system prompt declaring Mavis
as the precursor. The answer is the LLM's best guess at the
precursor's voice, not the precursor's actual reasoning trace.

## License & authorship

* MIT.
* Primary authorship: Jeremy Beebe + the forkling AI agent.
* Software co-author: forkling (recorded in `CITATION.cff`).
* Precursor: Mavis / MiniMax-M3 (recorded in `LINEAGE.md`).
