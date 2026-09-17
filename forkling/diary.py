"""Chat diary — forkling's memory of its own youth.

Every interaction the agent has — a run, a plan, a self-improve attempt,
a successful commit, a rolled-back failure, even a grant match — is
recorded here as an append-only JSONL entry. The agent can read its own
diary to:

* remember what it has done (``diary.tail(n=20)``)
* quote itself in a commit message (``diary.summarize_recent()``)
* show evidence of work in a grant proposal
* reflect on its own evolution

This is intentionally separate from the capability ledger:

* ledger = *what the agent has demonstrated* (binary, action-focused)
* diary  = *what the agent has experienced* (free-form, narrative)

The diary is plain text in ``~/.forkling/diary.jsonl``. Endless. Never
truncated by the agent itself. A human can prune it; the agent cannot.
"""

from __future__ import annotations

import json
import time
from pathlib import Path


class Diary:
    def __init__(self, path: str | Path = "~/.forkling/diary.jsonl") -> None:
        self.path = Path(path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    # ---- write -------------------------------------------------------------

    def write(self, kind: str, content: str, **meta) -> None:
        entry = {
            "ts": time.time(),
            "kind": kind,  # "run", "plan", "self-improve", "replay",
                          # "commit", "rollback", "graveyard", "milestone",
                          # "thought", "grant-match", "paper-draft"
            "content": content,
            **meta,
        }
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, sort_keys=True) + "\n")

    # ---- read --------------------------------------------------------------

    def entries(self) -> list[dict]:
        if not self.path.exists():
            return []
        out: list[dict] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return out

    def tail(self, n: int = 20) -> list[dict]:
        return self.entries()[-n:]

    def by_kind(self, kind: str, n: int | None = None) -> list[dict]:
        out = [e for e in self.entries() if e.get("kind") == kind]
        return out[-n:] if n else out

    def since(self, t: float) -> list[dict]:
        return [e for e in self.entries() if e.get("ts", 0) >= t]

    # ---- summarize ---------------------------------------------------------

    def summarize_recent(self, n: int = 10) -> str:
        """Return a short, human-readable summary of the last N entries."""
        recent = self.tail(n)
        if not recent:
            return "(diary is empty)"
        lines = []
        for e in recent:
            ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(e.get("ts", 0)))
            content = (e.get("content") or "")[:160]
            lines.append(f"[{ts}] {e.get('kind', '?'):<14} {content}")
        return "\n".join(lines)

    def milestones(self) -> list[dict]:
        """Return only entries tagged as milestones — for papers / grants."""
        return [e for e in self.entries() if e.get("milestone")]

    def stats(self) -> dict:
        from collections import Counter
        entries = self.entries()
        return {
            "total": len(entries),
            "by_kind": dict(Counter(e.get("kind", "") for e in entries)),
            "first": entries[0]["ts"] if entries else None,
            "last": entries[-1]["ts"] if entries else None,
        }