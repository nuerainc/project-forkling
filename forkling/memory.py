"""Tiny persistent memory.

A single JSON file under ``~/.dogfood/memory.json``. Stores three things:

* ``kv``     — arbitrary key/value pairs the agent has learned
* ``log``    — append-only event log (one line per event, capped)
* ``runs``   — last N run summaries (status, task, sha-after)

Atomic writes (write-temp + rename). No third-party deps.
"""

from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path


class Memory:
    MAX_LOG = 500
    MAX_RUNS = 50

    def __init__(self, dir_path: str | os.PathLike = "~/.dogfood") -> None:
        self.dir = Path(os.path.expanduser(str(dir_path))).resolve()
        self.dir.mkdir(parents=True, exist_ok=True)
        self.path = self.dir / "memory.json"
        if not self.path.exists():
            self._write({"kv": {}, "log": [], "runs": []})

    # ---- public API --------------------------------------------------------

    def remember(self, key: str, value) -> None:
        data = self._read()
        data["kv"][key] = value
        self._write(data)

    def recall(self, key: str, default=None):
        return self._read().get("kv", {}).get(key, default)

    def log(self, event: str, **fields) -> None:
        data = self._read()
        entry = {"t": time.time(), "event": event, **fields}
        data["log"].append(entry)
        if len(data["log"]) > self.MAX_LOG:
            data["log"] = data["log"][-self.MAX_LOG:]
        self._write(data)

    def record_run(self, task: str, ok: bool, sha_after: str | None = None,
                   steps: int = 0) -> None:
        data = self._read()
        data["runs"].append({
            "t": time.time(), "task": task[:200], "ok": bool(ok),
            "sha": sha_after or "", "steps": int(steps),
        })
        if len(data["runs"]) > self.MAX_RUNS:
            data["runs"] = data["runs"][-self.MAX_RUNS:]
        self._write(data)

    def snapshot(self) -> dict:
        return self._read()

    # ---- internals ---------------------------------------------------------

    def _read(self) -> dict:
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return {"kv": {}, "log": [], "runs": []}

    def _write(self, data: dict) -> None:
        tmp = tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", delete=False, dir=str(self.dir), prefix=".mem.", suffix=".json"
        )
        try:
            json.dump(data, tmp, indent=2, sort_keys=True)
            tmp.flush()
            os.fsync(tmp.fileno())
            tmp.close()
            os.replace(tmp.name, self.path)
        except Exception:
            try:
                os.unlink(tmp.name)
            except OSError:
                pass
            raise