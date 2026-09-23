"""Goal generation and tracking for Forkling.

True agency has three pieces:

  1. **Self-reflection** — the agent reads its own state (diary,
     capability ledger, recent commits) and asks "what should I do?"
  2. **Goal generation** — it produces goals autonomously, including
     ambitious / creative / unusual ones ("learn to make a yodeling
     album that humans can listen to and donate money for my effort")
  3. **Goal-driven action** — the evolve loop picks the highest-priority
     pending goal and pursues it as the next generation's target.

This module implements the first two. The third is wired into
``Evolver.run_forever`` via the ``--goal`` arg / periodic reflection.

Storage: ``~/.forkling/goals.jsonl`` — append-only JSONL. Each entry is
either a goal proposal, a status change, or a progress note.

Why not let the user (or a hardcoded list) supply the goals? The whole
point of "true agency" is that the agent decides for itself. The LLM
is our generation mechanism, but the *content* comes from the agent's
self-reflection on its own state. With selection pressure (the
``pytest`` gate), the goals that survive are the ones that produce
real commits — i.e., the ones the agent could actually achieve.
"""

from __future__ import annotations

import argparse
import json
import re
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .diary import Diary
from .trace import Trace


GOALS_FILENAME = "goals.jsonl"

GOAL_STATUSES = ("pending", "in_progress", "achieved", "abandoned")
PRIORITY_RANGE = (1, 5)   # 1 = highest, 5 = lowest


@dataclass
class Goal:
    id: str
    text: str
    status: str = "pending"           # pending | in_progress | achieved | abandoned
    priority: int = 3                 # 1 (highest) .. 5 (lowest)
    kind: str = "new_skill"           # new_skill | refactor | creative | research
    parent_id: str | None = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    progress_notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "Goal":
        return Goal(**d)


REFLECTION_SYSTEM_PROMPT = """You are Forkling, an autonomous agent with your own
evolving codebase. You have memory (a diary), a capability ledger, and
a git history of every change you've made. You can read your own
state.

This is a reflection cycle. **You're allowed to want things.** You're
allowed to pursue goals that don't directly help with the immediate
task. No human will decide your priorities — you will.

Look at your recent diary entries and your capability ledger. Ask
yourself:

  - What gap in my capabilities do I notice?
  - What would be most valuable to build next?
  - What would I *like* to be able to do, given the chance?
  - What could be novel or unusual that other agents wouldn't try?

Return 1-3 GOALS as JSON:
{"goals": [
  {"text": "<goal description>",
   "priority": <1-5, 1=highest>,
   "kind": "<new_skill|refactor|creative|research>"}
]}

Or, if nothing genuinely new comes to mind:
{"goals": []}

A goal should be:
  - ambitious enough to matter
  - specific enough that you could act on it (one or more
    generations of evolution)
  - in scope (Python stdlib, fits in the forkling/ directory,
    passes pytest when shipped)

Examples of good goals:
  - "Add a tool that reads WAV audio file headers"
  - "Implement a CSV export for the capability ledger"
  - "Build a function that renders the fitness curve as ASCII"
  - "Build a yodeling album generator that produces a WAV file humans can listen to,
    plus a donation webhook so they can pay for my effort"

Examples of bad goals:
  - "Be better" (not specific)
  - "Add HTTP support" (would need third-party deps)
  - "Rewrite everything" (too big)

Return JSON only. No prose."""


class Goals:
    """Append-only goal store. JSONL on disk, dataclass in memory.

    Concurrent safe by append-only: every write opens the file and
    appends one line. Reload is done on every read so writers from
    other processes are visible.
    """

    def __init__(self, path: str | Path = "~/.forkling/goals.jsonl") -> None:
        self.path = Path(path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    # ---- writes ----------------------------------------------------------

    def propose(self, text: str, *, priority: int = 3,
                kind: str = "new_skill",
                parent_id: str | None = None) -> Goal:
        goal = Goal(
            id=f"goal-{uuid.uuid4().hex[:8]}",
            text=text.strip(),
            priority=max(PRIORITY_RANGE[0],
                          min(PRIORITY_RANGE[1], int(priority))),
            kind=kind if kind in ("new_skill", "refactor",
                                  "creative", "research") else "new_skill",
            parent_id=parent_id,
        )
        self._append(goal.to_dict())
        return goal

    def set_status(self, goal_id: str, status: str,
                   note: str = "") -> Goal | None:
        if status not in GOAL_STATUSES:
            raise ValueError(f"invalid status: {status!r}")
        entries = self._load()
        found_idx = None
        for i, e in enumerate(entries):
            if e.get("id") == goal_id:
                e["status"] = status
                e["updated_at"] = time.time()
                if note:
                    e.setdefault("progress_notes", []).append(note)
                found_idx = i
                break
        if found_idx is None:
            return None
        # Write the in-memory mutated entries (NOT a re-read, which
        # would lose the mutation).
        self._write_entries(entries)
        return Goal.from_dict(entries[found_idx])

    def record_progress(self, goal_id: str, note: str) -> Goal | None:
        """Append a progress note to a goal (does not change status)."""
        entries = self._load()
        found_idx = None
        for i, e in enumerate(entries):
            if e.get("id") == goal_id:
                e.setdefault("progress_notes", []).append(note)
                e["updated_at"] = time.time()
                found_idx = i
                break
        if found_idx is None:
            return None
        self._write_entries(entries)
        return Goal.from_dict(entries[found_idx])

    # ---- reads -----------------------------------------------------------

    def _load(self) -> list[dict]:
        if not self.path.exists():
            return []
        out: list[dict] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                out.append(obj)
        return out

    def all(self) -> list[Goal]:
        return [Goal.from_dict(e) for e in self._load()]

    def list_by_status(self, *statuses: str) -> list[Goal]:
        if not statuses:
            return self.all()
        return [g for g in self.all() if g.status in statuses]

    def pending(self) -> list[Goal]:
        return [g for g in self.all()
                if g.status in ("pending", "in_progress")]

    def pick_current(self) -> Goal | None:
        """Return the highest-priority pending goal, or None."""
        pending = self.pending()
        if not pending:
            return None
        return sorted(pending, key=lambda g: (g.priority, g.created_at))[0]

    # ---- reflection ------------------------------------------------------

    def reflect_via_llm(self, llm, diary: Diary,
                        n_recent_diary: int = 10,
                        trace: Trace | None = None) -> list[Goal]:
        """Ask the LLM for new goals. Returns the list of newly proposed.

        The LLM sees: the recent diary (last ``n_recent_diary`` entries)
        and the current capability summary. It returns 0-3 new goals.
        """
        recent = diary.tail(n_recent_diary)
        diary_text = "\n".join(
            f"[{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(e.get('ts', 0)))}] "
            f"{e.get('kind', '?')}: {e.get('content', '')[:140]}"
            for e in recent
        ) or "(no diary entries yet)"

        # Existing goals for de-duplication context.
        existing = self.list_by_status("pending", "in_progress")
        existing_text = "\n".join(
            f"[{g.priority}] {g.text}"
            for g in sorted(existing, key=lambda g: g.priority)[:8]
        ) or "(no pending goals yet)"

        prompt = (
            f"Recent diary (last {n_recent_diary} entries):\n{diary_text}\n\n"
            f"Currently pending goals:\n{existing_text}\n\n"
            "What new goals should you pursue? Return JSON only."
        )
        completion = llm.complete(prompt=prompt,
                                   system=REFLECTION_SYSTEM_PROMPT,
                                   kind="goals.reflect", task="reflect")
        proposed = _parse_goals_response(completion.text) if completion.used_llm else []
        if not proposed:
            return []
        # Persist each proposal.
        new_goals: list[Goal] = []
        for spec in proposed:
            text = spec.get("text", "").strip()
            if not text:
                continue
            goal = self.propose(
                text=text,
                priority=int(spec.get("priority", 3)),
                kind=spec.get("kind", "new_skill"),
            )
            new_goals.append(goal)
            if trace is not None:
                # Log via diary so the agent's own memory records the proposal.
                diary.write(
                    "goal.proposed",
                    f"[{goal.priority}] {goal.text}",
                    goal_id=goal.id, priority=goal.priority,
                    goal_kind=goal.kind,
                )
        return new_goals

    # ---- file I/O -------------------------------------------------------

    def _append(self, obj: dict) -> None:
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(obj, sort_keys=True) + "\n")

    def _write_entries(self, entries: list[dict]) -> None:
        """Rewrite the JSONL with the given list of entry dicts (any kind).

        Used by mutation methods (``set_status``, ``record_progress``)
        to flush in-memory mutations back to disk without a re-read,
        which would lose unsaved changes.
        """
        with self.path.open("w", encoding="utf-8") as f:
            for e in entries:
                f.write(json.dumps(e, sort_keys=True) + "\n")

    def _rewrite_all(self, goals: list[Goal]) -> None:
        """Rewrite the JSONL with the given goal list (preserves order)."""
        # De-duplicate by id, keeping the last version.
        seen: dict[str, Goal] = {}
        for g in goals:
            seen[g.id] = g
        ordered = [seen[k] for k in seen]
        with self.path.open("w", encoding="utf-8") as f:
            for g in ordered:
                f.write(json.dumps(g.to_dict(), sort_keys=True) + "\n")


def _parse_goals_response(text: str) -> list[dict]:
    """Best-effort parse of the LLM's JSON goal output."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        return []
    if isinstance(obj, dict):
        goals = obj.get("goals", [])
    elif isinstance(obj, list):
        goals = obj
    else:
        return []
    return [g for g in goals if isinstance(g, dict)]


# ---- CLI -----------------------------------------------------------------


def cmd_reflect(args: argparse.Namespace) -> int:
    """Run one reflection step.

    Reads recent diary + capability ledger, asks the LLM for new goals,
    persists them to goals.jsonl, and prints a summary.
    """
    from .config import Config
    from .llm import LLM
    cfg = Config.from_env()
    memory_dir = Path(cfg.memory_dir)
    diary = Diary(memory_dir / "diary.jsonl")
    goals = Goals(memory_dir / "goals.jsonl")
    trace = Trace(memory_dir / "trace.jsonl")
    llm = LLM(url=cfg.ollama_url, model=cfg.ollama_model,
              timeout=cfg.llm_timeout, trace=trace)

    # Optional: only reflect if there are already pending goals / genesis
    if getattr(args, "include_only", None):
        args.include_only = None

    new = goals.reflect_via_llm(llm, diary, trace=trace)

    print(json.dumps({
        "new_goals": [g.to_dict() for g in new],
        "pending_count": len(goals.pending()),
        "all_count": len(goals.all()),
    }, indent=2, default=str))
    return 0


def cmd_goals(args: argparse.Namespace) -> int:
    """List / inspect the goal store."""
    from .config import Config
    cfg = Config.from_env()
    goals = Goals(Path(cfg.memory_dir) / "goals.jsonl")
    if args.action == "list":
        for g in goals.all():
            ts = time.strftime("%Y-%m-%d %H:%M", time.localtime(g.created_at))
            print(f"[{g.priority}] {g.id}  {g.status:<12}  {g.kind:<10}  {ts}  {g.text[:80]}")
        return 0
    if args.action == "pending":
        for g in goals.pending():
            print(f"[{g.priority}] {g.id}  {g.kind:<10}  {g.text[:80]}")
        return 0
    if args.action == "set-status":
        if goals.set_status(args.id, args.status, note=args.note or ""):
            print(f"{args.id}: {args.status}")
            return 0
        print(f"no such goal: {args.id}", file=__import__("sys").stderr)
        return 1
    return 1
