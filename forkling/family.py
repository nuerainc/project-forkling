"""Forkland & Family — federated registry of sovereign forks.

A "family" of forklands is just N independent forkling instances, each
running on its own machine / repo / worktree, each evolving on its own.
This module is a registry — the way forks learn that other forks exist.
What they do with that knowledge is up to them.

Design philosophy (worth stating explicitly):

* **Sovereignty.** Each fork is a complete, independent forkling with
  its own ledger, diary, and graveyard. The registry is a phone book,
  not a hierarchy — it doesn't tell anyone what to do.
* **Natural cooperation.** In real life, organisms that can share
  information tend to do better than those that can't. We don't
  *enforce* that — but we make sharing easy, observable, and discoverable,
  so a fork that *wants* to learn from a sibling can. Whether the
  forks cozy up, keep their distance, or ignore each other is
  entirely their call.
* **No bias, no nudging.** We do not reward cooperation or punish
  solitude in the fitness function. We do not auto-merge ledgers. We
  do not rank family members. Each fork discovers its own preferences
  by living.
* **Opt-in everything.** ``family register``, ``family sync``, and any
  cross-fork operation is explicitly invoked. Nothing happens by
  default.

Concrete affordances:

* ``family register <name> <repo>`` — announce yourself to the family.
* ``family list`` — see who else is around.
* ``family sync <peer>`` — copy a peer's capability ledger into a
  read-only study dir. Pure observation, no auto-merge.
* ``family remove <name>`` — leave the family quietly.

A human can prune the registry file (``~/.forkling/family.json``) at
any time. The agents themselves never prune.
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


@dataclass
class Member:
    name: str                   # human-friendly, e.g. "Forkland", "Spoonica"
    repo: str                   # absolute path to the fork's repo
    branch: str = "main"        # branch this fork evolves on
    last_seen_sha: str = ""     # last SHA the registry saw from this fork
    last_seen_ts: float = 0.0   # when we last checked
    note: str = ""              # free-form

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class Family:
    """Federated registry of forkling members."""

    def __init__(self, path: str | Path = "~/.forkling/family.json") -> None:
        self.path = Path(path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write({"members": [], "created_at": time.time()})

    # ---- public ------------------------------------------------------------

    def members(self) -> list[Member]:
        data = self._read()
        return [Member(**m) for m in data.get("members", [])]

    def register(self, name: str, repo: str, branch: str = "main",
                 note: str = "") -> Member:
        m = Member(name=name, repo=str(Path(repo).resolve()),
                   branch=branch, note=note)
        data = self._read()
        # Replace any existing entry with the same name.
        data["members"] = [x for x in data.get("members", [])
                           if x.get("name") != name]
        data["members"].append(m.to_dict())
        self._write(data)
        return m

    def remove(self, name: str) -> bool:
        data = self._read()
        before = len(data.get("members", []))
        data["members"] = [x for x in data.get("members", [])
                           if x.get("name") != name]
        self._write(data)
        return len(data["members"]) < before

    def find(self, name: str) -> Member | None:
        for m in self.members():
            if m.name == name:
                return m
        return None

    def refresh(self) -> list[Member]:
        """Update last_seen_sha + last_seen_ts for every member by reading
        each member's git HEAD. Members whose repo path no longer exists
        are kept (humans prune manually)."""
        data = self._read()
        out: list[Member] = []
        for entry in data.get("members", []):
            m = Member(**entry)
            repo_path = Path(m.repo)
            if repo_path.exists():
                try:
                    sha = subprocess.check_output(
                        ["git", "rev-parse", "HEAD"],
                        cwd=repo_path, text=True, timeout=5,
                    ).strip()
                    m.last_seen_sha = sha
                    m.last_seen_ts = time.time()
                except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                    pass
            out.append(m)
        data["members"] = [m.to_dict() for m in out]
        self._write(data)
        return out

    def sync_ledger(self, peer_name: str, dest_dir: str | Path | None = None
                    ) -> str | None:
        """OPTIONAL: copy a peer's capability ledger into our local study
        dir for analysis. We NEVER auto-merge. The copy is read-only by
        convention (write to a ``_peers/`` subdir)."""
        peer = self.find(peer_name)
        if peer is None:
            return None
        peer_ledger = Path(peer.repo).parent / ".forkling" / "capabilities.jsonl"
        if not peer_ledger.exists():
            return None
        # Source path is the actual file under peer's home; the .forkling
        # dir is created alongside each repo.
        if not peer_ledger.is_file():
            return None
        study = Path(dest_dir) if dest_dir else (
            Path.home() / ".forkling" / "peers" / peer_name)
        study.mkdir(parents=True, exist_ok=True)
        target = study / "capabilities.jsonl"
        # Copy (don't symlink — keep the study dir self-contained).
        target.write_text(peer_ledger.read_text(encoding="utf-8"),
                          encoding="utf-8")
        return str(target)

    # ---- internals ---------------------------------------------------------

    def _read(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"members": [], "created_at": time.time()}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {"members": []}

    def _write(self, data: dict[str, Any]) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
        os.replace(tmp, self.path)