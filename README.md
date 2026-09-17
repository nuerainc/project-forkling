# 🐶 dogfood

> The absolute MVP of a **self-contained, self-improving AI agent** that lives in a repo, plans/builds/tests/deploys/rolls back improvements to itself, runs on **local Ollama** (no paid APIs), and dogfoods from the first push.

```
task in  ──►  plan  ──►  act  ──►  test  ──►  ship?  ──►  done
                  ▲                              │
                  └──── reflect / rollback ──────┘
```

## What you get

| Capability        | MVP implementation                                                          |
| ----------------- | --------------------------------------------------------------------------- |
| **Self-contained** | Single Python package, stdlib only, no `requests`, no `click`.            |
| **Low memory**     | Pure Python core ~1 MB RAM. LLM is optional; rule-based fallback included. |
| **No paid APIs**   | Talks to a local [Ollama](https://ollama.com) daemon over HTTP.             |
| **Plan**           | Decomposes a task into ordered steps using the LLM (or a heuristic).        |
| **Build**          | Edits files, runs shell commands, applies patches.                          |
| **Test**           | Runs `pytest` (or any command) before any self-change is kept.              |
| **Deploy**         | `git tag` a release commit.                                                 |
| **Rollback**       | `git checkout` the previous SHA if tests fail.                              |
| **Dogfood**        | `scripts/self_improve.py` lets the agent edit its own source and ship it.   |

## Install (any device with Python ≥3.9)

```bash
git clone <this repo> dogfood && cd dogfood
pip install -e .            # or just: python -m dogfood --help
python -m dogfood doctor    # sanity check: python, git, ollama
```

> Don't have Ollama? Skip it. The agent falls back to a deterministic planner and still plans/acts/tests/rolls back. The LLM just makes planning smarter.

## Use

```bash
# Run a one-shot task in the current repo
python -m dogfood run "add a --dry-run flag to the cli"

# Iterate: propose a self-improvement, run tests, commit if green, else rollback
python -m dogfood self-improve

# CI / dogfood loop: agent reads itself, picks one tiny safe change, ships it
python scripts/self_improve.py
```

## How self-improvement works

1. Snapshot current `HEAD` SHA.
2. Read own source files.
3. Pick a small, safe improvement (typo fix, missing docstring, unused-import removal).
4. Apply the patch.
5. Run `pytest -q`.
6. **Green → commit + tag. Red → `git checkout` previous SHA.** Always.

The agent never silently breaks itself. Every change is gated by its own test suite.

## Architecture

```
dogfood/
├── __init__.py
├── __main__.py     # CLI entry (python -m dogfood …)
├── config.py       # settings (env-overridable)
├── llm.py          # Ollama HTTP client + rule-based fallback planner
├── tools.py        # filesystem / shell / git / patch primitives
├── memory.py       # tiny JSON-backed memory in ~/.dogfood/
├── planner.py      # task → ordered steps
├── agent.py        # Plan → Act → Reflect loop
└── self_improve.py # gated self-edit orchestrator
tests/              # pytest suite incl. self-dogfood test
scripts/            # bootstrap, self_improve entry for CI
.github/workflows/  # dogfood CI: agent runs on itself every push
```

## Why "MVP"

Everything above is the smallest set of pieces that closes the loop end-to-end. From commit 1 the agent can read itself, propose a change, run its tests, and either ship it or roll back. There is no paid API anywhere in the path. Drop it on a Raspberry Pi, a VPS, or a laptop — same code.

## License

MIT. See `LICENSE`.