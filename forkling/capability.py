"""Append-only capability ledger.

Every action the agent takes is recorded as a SHA-256-chained entry:

    {ts, action, target, ok, agent_sha, sha_prev, sha_self}

The chain head is the agent's *fitness floor* — every improvement must add
new capabilities without breaking old ones. Verifiable: walking the chain
reproduces every sha_self, and a single tampered byte breaks the chain at
exactly one entry.

This is a research artifact, not a security primitive. The chain prevents
accidental rewrites of history (a real risk when an agent edits its own
source), not adversarial ones.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path


class CapabilityLedger:
    """Append-only, SHA-256-chained record of demonstrated capabilities."""

    ZERO = "0" * 64

    def __init__(self, path: str | Path = "~/.forkling/capabilities.jsonl") -> None:
        self.path = Path(path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._head = self._read_head()

    @property
    def head(self) -> str:
        return self._head

    # ---- write -------------------------------------------------------------

    def record(self, *, action: str, target: str, ok: bool,
               agent_sha: str = "", extra: dict | None = None) -> str:
        body = {
            "ts": time.time(),
            "action": action,
            "target": target,
            "ok": bool(ok),
            "agent_sha": agent_sha,
            "sha_prev": self._head,
            "extra": extra or {},
        }
        encoded = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
        sha_self = hashlib.sha256(self._head.encode("utf-8") + encoded).hexdigest()
        body["sha_self"] = sha_self
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(body, sort_keys=True) + "\n")
        self._head = sha_self
        return sha_self

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

    def distinct_actions(self) -> set[str]:
        return {e["action"] for e in self.entries() if e.get("ok")}

    def distinct_targets(self) -> set[str]:
        return {e["target"] for e in self.entries() if e.get("target") and e.get("ok")}

    def verified_ok_count(self) -> int:
        ok, _ = self.verify()
        return sum(1 for e in self.entries() if e.get("ok")) if ok else 0

    # ---- verify ------------------------------------------------------------

    def verify(self) -> tuple[bool, str]:
        prev = self.ZERO
        for entry in self.entries():
            if entry.get("sha_prev") != prev:
                return False, f"chain break at ts={entry.get('ts')}"
            material = {k: v for k, v in entry.items() if k != "sha_self"}
            encoded = json.dumps(material, sort_keys=True, separators=(",", ":")).encode("utf-8")
            expected = hashlib.sha256(prev.encode("utf-8") + encoded).hexdigest()
            if expected != entry.get("sha_self"):
                return False, f"hash mismatch at ts={entry.get('ts')}"
            prev = entry["sha_self"]
        return True, "ok"

    # ---- internals ---------------------------------------------------------

    def _read_head(self) -> str:
        if not self.path.exists():
            return self.ZERO
        last = ""
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                last = line
        if not last:
            return self.ZERO
        try:
            return json.loads(last)["sha_self"]
        except (json.JSONDecodeError, KeyError):
            return self.ZERO