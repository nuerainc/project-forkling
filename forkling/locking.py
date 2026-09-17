"""Heartbeat lock — prevent two heartbeats from racing.

Forkland's heartbeat is safe in isolation, but running it twice in
parallel on the same repo can cause:
* Two git commits that race
* A self-improve's `git checkout` racing with another commit
* Ledger writes from two processes interleaving

This module provides a small file-based lock. The lock is best-effort:
if it can't be acquired (another heartbeat is mid-flight), the new one
exits cleanly with a non-zero code so cron doesn't silently duplicate
work.

The lock is **per-repo**: each repo has its own ``.forkling/heartbeat.lock``
file. Multiple forkling instances in different repos can run heartbeats
simultaneously without contention.
"""

from __future__ import annotations

import os
import time
from pathlib import Path


LOCK_FILENAME = "heartbeat.lock"


class LockBusy(Exception):
    """Raised when the heartbeat lock is already held."""


class HeartbeatLock:
    def __init__(self, repo: str | Path, stale_seconds: int = 7200) -> None:
        self.repo = Path(repo).resolve()
        self.lock_path = self.repo / ".forkling" / LOCK_FILENAME
        self.stale_seconds = stale_seconds
        self._held = False

    def acquire(self) -> None:
        """Acquire the lock or raise ``LockBusy``."""
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        if self.lock_path.exists():
            try:
                age = time.time() - self.lock_path.stat().st_mtime
                if age < self.stale_seconds:
                    raise LockBusy(
                        f"heartbeat lock held by another process "
                        f"(age={age:.0f}s, path={self.lock_path})"
                    )
                # Lock is stale — take it over.
            except OSError:
                pass
        # Write our PID + timestamp atomically.
        payload = f"{os.getpid()}\n{time.time()}\n".encode()
        fd, tmp = tempfile_atomic(self.lock_path)
        try:
            os.write(fd, payload)
            os.fsync(fd)
        finally:
            os.close(fd)
        os.replace(tmp, self.lock_path)
        self._held = True

    def release(self) -> None:
        if not self._held:
            return
        try:
            self.lock_path.unlink()
        except OSError:
            pass
        self._held = False

    def __enter__(self) -> "HeartbeatLock":
        self.acquire()
        return self

    def __exit__(self, *exc) -> None:
        self.release()


def tempfile_atomic(target: Path):
    """Return (fd, tmp_name) for an atomic write next to target."""
    import tempfile
    fd, name = tempfile.mkstemp(prefix=".lock.", dir=str(target.parent))
    return fd, name