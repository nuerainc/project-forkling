# 🍴 forkland

> The MVP of a **self-contained, self-improving AI agent** that lives in a repo, plans/builds/tests/deploys/rolls back improvements to itself, runs on **local Ollama** (no paid APIs), and dogfoods from the first push. Branched from the original `dogfood` MVP; v0.2 adds a research-grade substrate for evolutionary AI.

```
task in  ──►  plan  ──►  act  ──►  test  ──►  ship?  ──►  done
                  ▲                              │
                  └──── reflect / rollback ──────┘
                                  │
                                  ▼
            capability ledger · patch graveyard · diary · fitness
```

## What's in v0.2

| Capability          | Implementation                                                                 |
| ------------------- | ------------------------------------------------------------------------------ |
| **Self-contained**  | Single Python package, stdlib only, no `requests`, no `click`.                 |
| **Low memory**      | Pure Python core ~1 MB. Ollama optional; rule-based fallback included.          |
| **No paid APIs**    | Talks to a local [Ollama](https://ollama.com) daemon over HTTP.                |
| **Plan**            | LLM (Ollama) decomposes task → JSON steps. Heuristic fallback included.        |
| **Build**           | Edits files, runs shell, applies safe patches (uniqueness-checked).            |
| **Test**            | Runs `pytest -q` before any self-change is kept.                                |
| **Deploy**          | `git tag` a release commit.                                                    |
| **Rollback**        | `git checkout` the previous SHA if tests fail.                                  |
| **Dogfood**         | `python -m forkling self-improve` lets the agent edit its own source.          |

### v0.2 additions — the research substrate

| Module                       | What it does                                                                       |
| ---------------------------- | ---------------------------------------------------------------------------------- |
| **`forkling/capability.py`** | SHA-256-chained append-only ledger of every action the agent takes.               |
| **`forkling/graveyard.py`**  | Records every rejected patch with reason. Injected into the next LLM prompt.       |
| **`forkling/evolution.py`**  | Multi-objective fitness (smartness + skill) and A/B lineage experiments.          |
| **`forkling/replay.py`**     | Phylogenetic replay — run an ancestor commit of forkling on a task.                |
| **`forkling/diary.py`**      | Append-only diary of every interaction. Forkland's memory of its own youth.       |
| **`forkling/grants.py`**     | Grant hunter — matches the project against `grants.json`, drafts proposals.       |

## Install

```bash
git clone <this repo> forkland && cd forkland
pip install -e .
pip install pytest        # dev only

python -m forkling doctor  # sanity check: python, git, ollama
```

> Don't have Ollama? Skip it. forkland falls back to a deterministic planner and still plans/acts/tests/rolls back. The LLM just makes planning smarter.

## Use

```bash
# Run a one-shot task in the repo
python -m forkling run "add a --dry-run flag to the cli"

# Plan only (no execution)
python -m forkling plan "list dogfood"

# Iterate: propose a self-improvement, run tests, commit if green, else rollback
python -m forkling self-improve

# Phylogenetic replay — run an ancestor commit on a task
python -m forkling replay <old-sha> "fix the foo bug"

# Diff two ancestor commits on the same task
python -m forkling diff-replays <sha-a> <sha-b> "fix the foo bug"

# List the SHAs on the path between two commits
python -m forkling lineage <sha-start> <sha-end>

# Grant hunter
python -m forkling grants list
python -m forkling grants draft 0       # draft proposal for the top match

# Diary — forkland's memory of its youth
python -m forkling diary tail 20
python -m forkling diary milestones
python -m forkling diary stats

# Fitness + ledger verification
python -m forkling fitness
python -m forkling verify
```

## How self-improvement works

1. Snapshot current `HEAD` SHA.
2. Read own source files (capability `read` recorded in the ledger).
3. Pick a small, safe improvement (LLM or rule-based).
4. Inject the **patch graveyard** into the prompt so the LLM learns from its own failures.
5. Apply the patch (uniqueness-checked).
6. Run `pytest -q`.
7. **Green → commit + tag. Red → `git checkout` previous SHA.** Always.
8. Record the outcome in the capability ledger, graveyard, and diary.

forkland never silently breaks itself. Every change is gated by its own test suite, and the entire history is auditable.

## Architecture

```
forkling/
├── __init__.py
├── __main__.py     # CLI entry (python -m forkling …)
├── config.py       # env-overridable settings; sovereign mode flag
├── llm.py          # Ollama HTTP client + rule-based fallback
├── tools.py        # filesystem / shell / git / patch primitives
├── memory.py       # JSON-backed memory (~/.forkling/memory.json)
├── planner.py      # task → ordered steps, graveyard-aware prompts
├── agent.py        # Plan → Act → Reflect loop
├── self_improve.py # gated self-edit orchestrator
├── capability.py   # SHA-256-chained append-only ledger
├── graveyard.py    # patch graveyard with prompt-injection
├── evolution.py    # multi-objective fitness + A/B lineages
├── replay.py       # phylogenetic replay (run ancestor agents)
├── diary.py        # append-only diary of every interaction
└── grants.py       # grant hunter (grants.json + match + draft)
tests/              # 50 pytest tests incl. self-dogfood test
grants.json         # seeded database of grant programs
scripts/            # bootstrap, self_improve entry for CI
.github/workflows/  # dogfood CI: forkling runs on itself every push
```

## A/B lineages (planned)

The `forkling/evolution.py::run_ab()` primitive spawns parallel agents in
git worktrees, each with different env vars (e.g. `FORKLING_STRATEGY`),
runs them for N generations, and ranks by fitness. The "control"
variant is **Spoonica**, the conservative sister. Hybrid is
**Sporklyn**, sharpest is **Knifling**. Coming after v0.2.

## Forkland & Family (federated, opt-in)

A "family" is just N independent forkling instances — each on its own
machine, repo, or worktree, each evolving on its own. The
`forkling/family.py` module is a registry (a phone book, not a
hierarchy) so the forks can know about each other.

We make **coordination easy** but **enforce nothing**. In real life,
organisms that can share information tend to do better than those that
can't — but we don't hard-code that preference. Each fork discovers its
own disposition toward its siblings: it may cozy up, keep its
distance, or ignore them. The fitness function does not reward or
punish either behavior.

```bash
forkling family register Forkland /path/to/forkland
forkling family register Spoonica /path/to/spoonica
forkling family list
forkling family sync Forkland   # copy Forkland's ledger for study
```

## License

MIT. See `LICENSE`.

## Authorship & agent credit

Primary authorship is held by the human maintainers. forkland is
acknowledged in `CITATION.cff` and in paper author-contributions
sections. The capability ledger, graveyard, and diary make the agent's
contribution auditable.