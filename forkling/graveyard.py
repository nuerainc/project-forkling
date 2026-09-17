"""Patch graveyard.

Every rejected patch (LLM-proposed or rule-based) is recorded with its
reason. The next proposal prompt is augmented with a short excerpt of
recent failures so the model learns from its own mistakes — a primitive
form of negative-example memory.

The graveyard is intentionally public: it's plain JSONL at
``~/.forkling/graveyard.jsonl``. The agent can read its own failures,
humans can audit them, and future papers can analyse them.
"""

from __future__ import annotations

import json
import time
from pathlib import Path


class Graveyard:
    def __init__(self, path: str | Path = "~/.forkling/graveyard.jsonl") -> None:
        self.path = Path(path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    # ---- write -------------------------------------------------------------

    def record(self, *, path: str, old: str, new: str, reason: str,
               source: str = "") -> None:
        entry = {
            "ts": time.time(),
            "path": path,
            "old": old[:200],
            "new": new[:200],
            "reason": reason[:500],
            "source": source,  # "llm" or "rule-based"
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

    def recent(self, n: int = 10) -> list[dict]:
        return self.entries()[-n:]

    def as_prompt_excerpt(self, n: int = 5) -> str:
        """Return a short, prompt-friendly summary of recent failures."""
        recent = self.recent(n)
        if not recent:
            return ""
        lines = ["Recent rejected patches (avoid repeating these mistakes):"]
        for e in recent:
            lines.append(f"  - {e['path']}: {e['reason'][:120]}")
        return "\n".join(lines)

    def stats(self) -> dict:
        """Aggregate rejection statistics — useful for the fitness function."""
        from collections import Counter
        entries = self.entries()
        if not entries:
            return {"total": 0, "by_reason": {}, "by_path": {}, "by_source": {}}
        return {
            "total": len(entries),
            "by_reason": dict(Counter(e.get("reason", "")[:80] for e in entries)),
            "by_path": dict(Counter(e.get("path", "") for e in entries)),
            "by_source": dict(Counter(e.get("source", "") for e in entries)),
        }