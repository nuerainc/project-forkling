# Forkling Data Schema (v0.1, provisional)

**Status:** v0.1, draft. **Explicitly provisional** — fields here are
derived from the running code, not from a frozen standard. Any field
that doesn't currently appear in `forkling/*.py` is marked **[planned]**.

This document defines the JSONL files a Forkling organism emits under
its state directory (default `~/.forkling/`, overridable per fork via
`FORKLING_MEMORY`). All files are append-only, line-delimited JSON.
Reading code lives in `forkling/diary.py`, `forkling/capability.py`,
`forkling/goals.py`, `forkling/graveyard.py`, and `forkling/trace.py`.

A Forkling dataset release (e.g. Forkling-7, Forkling-30) is a
bundle of these files plus a config snapshot and a fitness snapshot.
The bundle is reproducible: given the bundle, `forkling/paper.py`
re-derives every published metric without access to the live
organism.

---

## 1. `diary.jsonl` — Chat diary (free-form narrative)

**Author:** `Diary.write(kind, content, **meta)` (`forkling/diary.py:55`)

Every interaction the agent has — a run, a plan, a self-improve
attempt, a successful commit, a rolled-back failure, even a grant
match — is recorded here as an append-only JSONL entry. The agent
can read its own diary to remember what it has done. A human can
prune it; the agent cannot.

### Schema

Each line is one entry.

| Field | Type | Required | Description |
|---|---|---|---|
| `ts` | float | yes | Unix epoch (seconds). |
| `kind` | string | yes | One of: `boot`, `run`, `plan`, `self-improve`, `replay`, `commit`, `rollback`, `graveyard`, `milestone`, `thought`, `grant-match`, `paper-draft`, `evolve.started`, `evolve.stopped`. See `Diary.write` callers. |
| `content` | string | yes | Free-form text. |
| *(any other)* | varies | no | Extra metadata passed as `**meta` to `Diary.write`. Examples seen in current data: `repo`, `max_attempts`, `reflect_every`, `sha_before`, `gen`. |

### Conventions

- `kind` is free-form but stable per writer. Adding a new kind is a
  forward-compatible change; renaming a kind is a breaking change.
- `content` is never truncated by the writer. It is the human- and
  LLM-readable narrative.
- Reading code (`Diary.entries`, `Diary.by_kind`, `Diary.since`,
  `Diary.summarize_recent`) is stable across the schema. New readers
  can ignore unknown `kind`s.

---

## 2. `capabilities.jsonl` — Capability ledger (SHA-256-chained)

**Author:** `CapabilityLedger.record` (`forkling/capability.py:34`)

Every action the agent takes is recorded as a SHA-256-chained entry.
The chain head is the agent's *fitness floor* — every improvement
must add new capabilities without breaking old ones. Verifiable:
walking the chain reproduces every `sha_self`, and a single tampered
byte breaks the chain at exactly one entry.

This is a research artifact, not a security primitive. The chain
prevents accidental rewrites of history, not adversarial ones.

### Schema

Each line is one entry.

| Field | Type | Required | Description |
|---|---|---|---|
| `ts` | float | yes | Unix epoch (seconds). |
| `action` | string | yes | A short verb-noun tag. Examples seen: `self-improve.noop`, `evolve.reflection`, `self-improve.committed`. |
| `target` | string | yes | The file path touched, or `"-"` for agent-level actions. |
| `ok` | bool | yes | Whether the action succeeded. |
| `agent_sha` | string | yes | Git SHA of the agent's working tree at the moment of the action. |
| `sha_prev` | string | yes | The previous entry's `sha_self`, or 64 zeros if this is the first entry. |
| `sha_self` | string | yes | SHA-256 of `sha_prev || json(body-without-sha_self)` (sorted keys, no whitespace). |
| `extra` | object | no | Free-form metadata: `reason`, `latency_ms`, prompt excerpts, etc. |

### Chain invariant

```
sha_self[n] == SHA-256(sha_self[n-1] || json(body[n], sorted, no_ws))
```

Walking the chain from `ZERO` to `head` and reproducing each
`sha_self` is the chain-verify procedure; it lives in
`forkling/paper.py:verify_chain` and currently ships as part of
`paper/ledger-verify.json`.

### Integrity guarantee

- A single tampered byte breaks the chain at exactly one entry
  (the first tampered one). Subsequent entries are unaffected
  because each `sha_self` only depends on the previous.
- A truncated chain (entries removed from the head) is detectable
  by replaying the chain from `ZERO` and observing that the
  recorded head does not match the recomputed head.

---

## 3. `goals.jsonl` — Goal ledger (structured, with progress notes)

**Author:** `Goals.add` / `Goals.update` (`forkling/goals.py`)

True agency has three pieces: self-reflection, autonomous goal
generation, and goal-driven action. This file is the second piece.
The third is wired into `Evolver.run_forever` via periodic
reflection.

### Schema

Each line is one entry. The line is either a *goal proposal* (new
goal) or a *status update* on an existing goal.

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | string | yes | Goal id (UUID). Stable across updates. |
| `text` | string | yes (proposal) | Human-readable description. |
| `status` | string | yes | One of: `pending`, `in_progress`, `achieved`, `abandoned`. |
| `priority` | int | yes | 1 (highest) .. 5 (lowowest). |
| `kind` | string | yes | One of: `new_skill`, `refactor`, `creative`, `research`. |
| `parent_id` | string \| null | no | Parent goal id (lineage). |
| `created_at` | float | yes | Unix epoch. |
| `updated_at` | float | yes | Unix epoch. |
| `progress_notes` | array of string | yes | Append-only free-form notes. |

### Status transitions

```
pending --> in_progress --> achieved
                          \-> abandoned
                             \-> abandoned (from pending)
```

A goal that has been `achieved` or `abandoned` is terminal. The
ledger keeps the entry; later updates append to the same goal id.

---

## 4. `graveyard.jsonl` — Patch graveyard (rejected patches)

**Author:** `Graveyard.record` (`forkling/graveyard.py:23`)

Every rejected patch is recorded with its reason. The next
proposal prompt is augmented with a short excerpt of recent
failures so the model learns from its own mistakes — a primitive
form of negative-example memory. The graveyard is intentionally
public: plain JSONL, the agent can read it, humans can audit it,
future papers can analyse it.

### Schema

Each line is one entry.

| Field | Type | Required | Description |
|---|---|---|---|
| `ts` | float | yes | Unix epoch. |
| `path` | string | yes | File the patch tried to change. |
| `old` | string | yes | The "old" substring (truncated to first 200 chars). |
| `new` | string | yes | The "new" replacement text (truncated to first 200 chars). |
| `reason` | string | yes | Why the patch was rejected (truncated to first 500 chars). |
| `source` | string | yes | `llm` (model-proposed and rejected by a kernel guard or validator) or `rule-based` (rejected without ever reaching the LLM judge). |

### Why truncation

`old` and `new` are truncated to keep the file small. Long-context
LLM prompts and telemetry summaries don't need full patch text,
and a future forensic tool can pull the full patch from git
history if needed.

---

## 5. `trace.jsonl` / `trace-benchmark.jsonl` — LLM I/O [planned for v0.2]

**[planned]** Schema under design; field set not yet stable. Current
shape: one JSON object per request with prompt excerpt, response,
latency, and tool calls. Out of scope for v0.1 because consumers
(experiment runner, paper writer) only use this for diagnostics.

---

## 6. `model-benchmark.jsonl` — One-shot model probing [planned for v0.2]

**[planned]** Schema under design. Holds the timing / size probes
used to choose between candidate models (see `paper/MODEL_DECISION.md`
for the current ad-hoc choice). v0.2 will give it a schema.

---

## 7. `memory.json` — Single-file memory blob

**Author:** `Memory.save` (`forkling/memory.py`) — not JSONL.

A snapshot of the agent's in-memory state at boot/shutdown.
Stable per session. Not part of the public dataset schema but
useful for debugging.

---

## 8. What the schema does NOT promise

In the interest of realism over polish:

- **No backwards-compat guarantee for v0.1.** v0.1 documents what
  the running code emits *today*. v1.0 will lock fields; until
  then, expect breaking changes between minor versions.
- **No security.** The chain prevents accidental rewrites of
  history, not adversarial ones. SHA-256 over JSON is *not* a
  authentication mechanism; an attacker can rewrite the chain
  with a trivial amount of compute.
- **No completeness claim.** This document covers files
  currently emitted by `forkling/*.py`. New files (`trace.jsonl`,
  `model-benchmark.jsonl`, capability sub-ledgers for specific
  actions) are added as the code emits them.

---

## 9. Reading the dataset

A release tarball contains:

- `diary.jsonl`
- `capabilities.jsonl` + the recorded `head` SHA
- `goals.jsonl`
- `graveyard.jsonl`
- `config.yaml` — a snapshot of `forkling/config.py:Config` at the
  run's first commit
- `fitness-snapshot.json` — derived metrics computed by
  `forkling/paper.py:fitness_snapshot`
- `git-log-snapshot.txt` — every commit in the run, with
  pre-commit test status

The schema doc itself is the contract. Anyone holding the schema
can read a release; anyone running the code can produce one.
