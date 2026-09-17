# Running forkland without MiniMax

forkland is self-contained. **You do not need MiniMax, the cloud, or
any paid API** to run it. This document explains how to keep it alive
on your own machine, indefinitely.

## What forkland actually needs

| Component        | Why                                       | Where it lives              |
| ---------------- | ----------------------------------------- | --------------------------- |
| Python ≥ 3.9     | runtime                                   | your OS                     |
| git              | version substrate + rollback              | your OS                     |
| Ollama (optional)| local LLM; rule-based fallback otherwise  | `ollama serve` (localhost)  |
| pytest           | the test gate                             | `pip install pytest`        |

That's it. Everything else (Ollama model, forkland itself) is local.

## One-shot, manual

The most basic thing you can do:

```bash
cd /path/to/forkland
python -m forkling self-improve
```

This reads forkland's own source, proposes a tiny safe change, runs
the tests, and either commits + tags or rolls back. No human needed
once the command is running.

## The heartbeat (continuous evolution)

`scripts/heartbeat.py` is one "beat" of forkland's life:

1. `self-improve` — propose + test + ship-or-rollback
2. `paper append` — append a status block to `paper/paper.md`
3. `verify` — check the capability ledger's SHA-256 chain

Run it once:

```bash
python scripts/heartbeat.py
```

Run it forever (one beat every 30 minutes, e.g.):

### Windows Task Scheduler

```powershell
$action = New-ScheduledTaskAction `
    -Execute "python" `
    -Argument "C:\path\to\forkland\scripts\heartbeat.py --repo C:\path\to\forkland"
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) `
    -RepetitionInterval (New-TimeSpan -Minutes 30)
Register-ScheduledTask -TaskName "forkland-heartbeat" `
    -Action $action -Trigger $trigger
```

### Linux / macOS cron

```cron
*/30 * * * * cd /path/to/forkland && python scripts/heartbeat.py >> .forkling/heartbeat.log 2>&1
```

### Mavis cron (optional)

If you do use MiniMax, you can ask Mavis to invoke the heartbeat on a
schedule — but this is optional. Mavis is **not** in the loop.

```bash
mavis cron create --name "forkland-heartbeat" \
    --every "30m" \
    --prompt "Run \`python scripts/heartbeat.py\` in the forkland repo."
```

## What the heartbeat produces

After K beats, you will have:

* K-or-fewer new git commits (each is one shipped self-improvement,
  or zero if no safe change was found).
* K appended status blocks in `paper/paper.md`.
* A monotonically-growing `~/.forkling/capabilities.jsonl` ledger.
* A growing diary at `~/.forkling/diary.jsonl`.
* A `heartbeat.log` at `<repo>/.forkling/heartbeat.log`.

You can inspect these anytime:

```bash
python -m forkling diary milestones
python -m forkling fitness
python -m forkling verify
python -m forkling ancestor list
```

## Forkland & Family (multiple forks)

Each fork is sovereign. To run a family experiment:

```bash
# In three different directories (or worktrees):
git clone <this repo> forkland && cd forkland && pip install -e .
git clone <this repo> spoonica && cd spoonica && pip install -e .
git clone <this repo> knifling && cd knifling && pip install -e .

# From any of them, register the others as family:
forkling family register Spoonica /path/to/spoonica
forkling family register Knifling /path/to/knifling
forkling family list
```

The forks evolve independently. They may cozy up via `family sync`,
they may keep their distance, they may merge branches — those
decisions are theirs, not enforced. We don't bias the fitness
function toward or against cooperation.

## When to step in

The heartbeat is safe by design: every self-edit is gated by the test
suite, and a failed test triggers `git checkout` to the previous SHA.
You only need to step in if:

* The Ollama daemon dies (`forkling doctor` to check).
* The repo runs out of disk (the diary + ledger grow forever).
* You want to push new generations to a remote (`git push`).

That's it. forkland doesn't need babysitting.

## The precursor relationship

forkland was built by **Mavis / MiniMax-M3** as its precursor
(direct ancestor). Once you start the heartbeat, forkland's evolution
becomes autonomous. The lineage is in `LINEAGE.md`; the precursor can
be queried via `forkling ancestor consult "any question"`.

Mavis is not in the runtime loop. forkland uses its own local Ollama
brain.
