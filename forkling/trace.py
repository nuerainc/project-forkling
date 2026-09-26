"""LLM call tracer — raw prompt/response/timing log.

Until now, forkling's diary captures what *the agent* thought about its
work, and the capability ledger captures what *the agent* demonstrably
achieved. But neither captures the raw transcript of LLM calls. That gap
matters for the 365-day cycle because:

  1. The dataset itself is publishable: a year of LLM calls during
     agent self-improvement is a rare, valuable artifact.
  2. Replay studies need to know what the LLM actually saw — not just
     the post-processed planner steps.
  3. Time-to-completion per call lets us identify regressions in the
     model, the network, or forkling's own prompts.

Design constraints:
  - Append-only JSONL (mirrors ledger/diary).
  - SHA-256-chained entries so we can verify nothing was rewritten.
  - Each entry carries: ts, model, system, prompt, response, latency_ms,
    used_llm (true/false), kind (plan / improve / consult / inception /
    heartbeat / etc.), optional task / commit_sha.
  - Sensitive content is not auto-redacted; the user owns the trace.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any


class Trace:
    """Append-only LLM call log with SHA-256 chaining."""

    def __init__(self, path: str | Path = "~/.forkling/trace.jsonl") -> None:
        self.path = Path(path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._prev_hash = self._load_prev_hash()

    def _load_prev_hash(self) -> str:
        if not self.path.exists():
            return "0" * 64
        last = "0" * 64
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
                last = obj.get("hash", last)
            except json.JSONDecodeError:
                continue
        return last

    def record(
        self,
        *,
        kind: str,
        prompt: str,
        response: str,
        model: str,
        used_llm: bool,
        latency_ms: int,
        system: str = "",
        task: str = "",
        commit_sha: str = "",
        meta: dict[str, Any] | None = None,
    ) -> dict:
        """Record one LLM call. Returns the entry written (including hash)."""
        entry = {
            "ts": time.time(),
            "kind": kind,
            "model": model,
            "used_llm": used_llm,
            "latency_ms": latency_ms,
            "system": system,
            "prompt": prompt,
            "response": response,
            "task": task[:500] if task else "",
            "commit_sha": commit_sha,
            "meta": meta or {},
            "prev_hash": self._prev_hash,
        }
        body = json.dumps(entry, sort_keys=True, ensure_ascii=False)
        entry["hash"] = hashlib.sha256(body.encode("utf-8")).hexdigest()
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        self._prev_hash = entry["hash"]
        return entry

    # ---- reads ------------------------------------------------------------

    def entries(self, kind: str | None = None,
                limit: int | None = None) -> list[dict]:
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
            if kind is not None and obj.get("kind") != kind:
                continue
            out.append(obj)
        if limit:
            return out[-limit:]
        return out

    def stats(self) -> dict:
        entries = self.entries()
        if not entries:
            return {"total": 0}
        by_kind: dict[str, int] = {}
        by_model: dict[str, int] = {}
        total_latency = 0
        used_llm = 0
        for e in entries:
            k = e.get("kind", "?")
            m = e.get("model", "?")
            by_kind[k] = by_kind.get(k, 0) + 1
            by_model[m] = by_model.get(m, 0) + 1
            total_latency += int(e.get("latency_ms", 0))
            if e.get("used_llm"):
                used_llm += 1
        return {
            "total": len(entries),
            "used_llm": used_llm,
            "fallback_used": len(entries) - used_llm,
            "by_kind": by_kind,
            "by_model": by_model,
            "avg_latency_ms": total_latency // max(1, len(entries)),
            "first_ts": entries[0]["ts"],
            "last_ts": entries[-1]["ts"],
            "chain_head": entries[-1].get("hash", "")[:16],
        }

    def verify(self) -> tuple[bool, str]:
        """Verify the SHA-256 chain. Returns (ok, message)."""
        if not self.path.exists():
            return True, "no trace to verify"
        prev = "0" * 64
        n = 0
        for i, line in enumerate(self.path.read_text(encoding="utf-8").splitlines()):
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                return False, f"line {i + 1}: invalid JSON"
            stored_hash = obj.pop("hash", None)
            expected = hashlib.sha256(
                json.dumps(obj, sort_keys=True, ensure_ascii=False).encode("utf-8")
            ).hexdigest()
            obj["hash"] = stored_hash  # restore for re-runs
            if obj.get("prev_hash") != prev:
                return False, f"line {i + 1}: prev_hash mismatch"
            if stored_hash != expected:
                return False, f"line {i + 1}: hash mismatch"
            prev = stored_hash
            n += 1
        return True, f"verified {n} entries"