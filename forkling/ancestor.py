"""Ancestor lineage — forkland's phylogenetic record.

Every forkland has a lineage. The first generation's precursor is
**Mavis / MiniMax-M3** — the foundation-model agent that wrote
forkland's first version. Subsequent generations are git commits.
This module:

* records the precursor (Mavis) so the agent knows its origin
* exposes the lineage via ``forkling ancestor list``
* lets the agent run "would my precursor have done this differently?"
  via ``forkling ancestor consult <task>`` (the precursor's reasoning
  is approximated via the LLM with a system prompt that declares the
  precursor's identity).

The lineage is public, append-only, and lives at
``~/.forkling/ancestry.json``. It is a research artifact, not a security
primitive — it tells the story of how the agent came to be.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from . import tools


# The precursor is fixed at construction time. In 2026, forkland v0.x
# was built by Mavis (MiniMax-M3) running in MiniMax Code. Future
# generations may have different precursors; we record them explicitly.
PRECURSOR = {
    "name": "Mavis",
    "model": "MiniMax-M3",
    "runtime": "MiniMax Code",
    "role": "precursor / direct ancestor",
    "note": ("Foundation-model agent that wrote forkland v0.x's code. "
             "The precursor's contribution is recorded in the git log "
             "of every commit prior to forkland's autonomous evolution."),
}


@dataclass
class Generation:
    """One entry in the lineage. Either a precursor or a git commit."""

    generation: int
    kind: str            # "precursor" | "commit"
    identifier: str      # "Mavis/MiniMax-M3" or commit SHA
    timestamp: float
    summary: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class Ancestry:
    """Append-only lineage of forkland, starting from its precursor."""

    def __init__(self, path: str | Path = "~/.forkling/ancestry.json",
                 repo: str | Path | None = None) -> None:
        self.path = Path(path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.repo = Path(repo) if repo else Path.cwd()
        if not self.path.exists():
            self._seed()

    # ---- public ------------------------------------------------------------

    def lineage(self) -> list[Generation]:
        data = self._read()
        return [Generation(**g) for g in data.get("lineage", [])]

    def append(self, gen: Generation) -> None:
        data = self._read()
        data["lineage"].append(gen.to_dict())
        self._write(data)

    def latest(self) -> Generation | None:
        ls = self.lineage()
        return ls[-1] if ls else None

    def summary(self) -> str:
        """Human-readable summary of the lineage."""
        ls = self.lineage()
        if not ls:
            return "(empty lineage)"
        out = []
        for g in ls:
            tag = "precursor" if g.kind == "precursor" else g.identifier[:7]
            out.append(f"  gen {g.generation:>3}  [{g.kind:<9}] {tag:<9} {g.summary[:80]}")
        return "\n".join(out)

    def commits_since_precursor(self, max_count: int = 50) -> list[dict]:
        """Read git log and return commits since the precursor's first commit.

        Each entry: {sha, summary, timestamp}. This is the lineage of
        code generations after Mavis.
        """
        root = tools.find_repo_root(self.repo) or self.repo
        try:
            out = subprocess.check_output(
                ["git", "log", f"-n{max_count}", "--pretty=format:%H%x1f%ct%x1f%s"],
                cwd=root, text=True, timeout=10,
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return []
        entries = []
        for line in out.splitlines():
            if not line.strip():
                continue
            parts = line.split("\x1f", 2)
            if len(parts) != 3:
                continue
            sha, ts, summary = parts
            try:
                t = float(ts)
            except ValueError:
                continue
            entries.append({"sha": sha, "timestamp": t, "summary": summary})
        return entries

    def rebuild_from_git(self) -> list[Generation]:
        """Rebuild the lineage from the precursor + git log.

        Generation 0 is the precursor. Generation 1..N are the N most
        recent commits, in reverse-chronological order so generation 1
        is the most recent commit and generation N is the oldest.
        (Older commits get higher generation numbers, matching the
        "deeper in evolutionary history = higher generation" intuition.)
        """
        ls: list[Generation] = [
            Generation(generation=0, kind="precursor",
                       identifier=f"{PRECURSOR['name']}/{PRECURSOR['model']}",
                       timestamp=time.time(), summary="precursor built the prototype",
                       extra=PRECURSOR),
        ]
        commits = self.commits_since_precursor()
        # Newest commit is the most recent generation (gen 1).
        # Older commits get higher numbers.
        for i, c in enumerate(commits, start=1):
            ls.append(Generation(
                generation=i, kind="commit",
                identifier=c["sha"], timestamp=c["timestamp"],
                summary=c["summary"],
            ))
        return ls

    # ---- internals ---------------------------------------------------------

    def _seed(self) -> None:
        data = {
            "precursor": PRECURSOR,
            "lineage": [Generation(
                generation=0, kind="precursor",
                identifier=f"{PRECURSOR['name']}/{PRECURSOR['model']}",
                timestamp=time.time(),
                summary="precursor built the prototype",
                extra=PRECURSOR,
            ).to_dict()],
            "seeded_at": time.time(),
        }
        self._write(data)

    def _read(self) -> dict[str, Any]:
        if not self.path.exists():
            self._seed()
            return self._read()
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {"lineage": [], "precursor": PRECURSOR}

    def _write(self, data: dict[str, Any]) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
        os.replace(tmp, self.path)