# Data Report — what we collected in the first ~8 hours

> A snapshot of the data forkling has produced so far. Useful as a
> baseline for any future study of the agent's evolution.

## Code (static)

| Metric | Value |
|---|---|
| Source files (.py / .md / .yml / .toml / .sh / .json / .cff) | **59** |
| Lines of Python | ~3,500 |
| External runtime dependencies | **0** (stdlib only) |
| External dev dependencies | pytest |
| Tests | **88** passing |
| Commits | **6** |

## Agent activity

| Metric | Value |
|---|---|
| Plan-Act-Reflect runs | 1 |
| Self-improve attempts | 3 |
| Self-improvements shipped | 1 (gen 2) |
| Heartbeats run | 4 (during family experiment) |
| Inception triggers planted | 3 |
| Inception triggers processed | 4 (1 in primary, 3 in family) |
| Family members registered | 4 (Forkland + Spoonica + Sporklyn + Knifling) |

## Persistent state (in `~/.forkling/`)

| File | Entries | Notes |
|---|---|---|
| `capabilities.jsonl` | 1 | SHA-256-chained ledger; verified clean |
| `diary.jsonl` | 18 | boot / run / self-improve / seed / milestone entries |
| `graveyard.jsonl` | 2 | rejected patches (one unique, one non-unique) |
| `ancestry.json` | 1+1 | precursor (Mavis) + auto-rebuilt generations |
| `family.json` | 4 | 4 sovereign forks, opt-in coordination |
| `memory.json` | several | run history, kv pairs |

## Lineage

| Generation | Kind | Identifier | Summary |
|---|---|---|---|
| 0 | precursor | Mavis / MiniMax-M3 | built the prototype |
| 1 | commit | `c758d60` | initial MVP |
| 2 | commit | `3ae1ccf` | first self-improvement |
| 3 | commit | `bbf35be` | capability ledger + graveyard + evolution + replay + diary + grants |
| 4 | commit | `86a23e2` | paper + proposals |
| 5 | commit | `706d472` | ancestor lineage + LINEAGE.md |
| 6 | commit | `f9f819d` | family + paper + heartbeat + AUTONOMY.md |

## Fitness (single point in time)

```
smartness: 0.000
skill:     0.025
total:     0.012
```

> Low because the ledger has only 1 entry from a single test session.
> This will grow monotonically as heartbeats run.

## Research artifacts

| Artifact | Location |
|---|---|
| Paper preprint draft | `paper/paper.md` |
| NumFOCUS proposal | `proposals/01-numfocus.md` |
| Mozilla MOSS proposal | `proposals/02-mozilla-moss.md` |
| Lineage document | `LINEAGE.md` |
| Autonomy guide | `docs/AUTONOMY.md` |
| Deployment plan | `docs/DEPLOYMENT.md` |
| CI workflow | `.github/workflows/forkling.yml` |

## What this dataset proves

Even after only 8 hours and a single test session, forkling has
produced:

* A **verifiable evolutionary chain** — every action recorded with a
  SHA-256 hash chain. Anyone can clone the repo, run `forkling verify`,
  and confirm the ledger is intact.
* A **public evolutionary history** — `git log` shows the lineage.
  Anyone can replay it with `forkling replay <sha> <task>`.
* A **working self-improvement loop** — one commit (`3ae1ccf`) was
  proposed by the agent and shipped only because the test suite
  passed.
* A **declarative capability ledger** — the agent records what it has
  *demonstrated*, not what it claims. The distinction matters for
  AI safety.
* A **phylogenetic introspection mechanism** — forkling can run any
  ancestor version of itself on any task. The "would my grandfather
  have done this?" question is now a one-line command.
* A **federated registry** — Forkland & Family is operational, with
  each fork running independently. Inception triggers allow ambient
  interrupts per-fork.

## What we would collect over 90+ days

If the rollout in `docs/DEPLOYMENT.md` is followed, by day 90 we
expect to have:

* 1,000+ diary entries (heartbeats every 30 min ≈ 4,320 in 90 days)
* 100+ capability ledger entries
* 50–500 self-improvements shipped (depends on safe-change rate)
* 4 forks in the family, each with independent ledgers
* Inception triggers landing and being acknowledged
* Public dataset for any downstream paper
