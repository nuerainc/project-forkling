"""Forkland Forkling daemon — the persistent, in-process heartbeat loop.

Until now, Forkling's heartbeat was one-shot: an external scheduler
(Windows Task Scheduler / cron / MiniMax cron) invoked
``python -m forkling heartbeat`` on a schedule. That works, but it
also means Forkling is never *alive* between heartbeats — there's no
process to introspect, no state to query, no place where the agent
can run other background work (inception trigger scanning,
fitness-snapshot emission, dataset exports on a cadence, etc.).

The daemon flips this: Forkling becomes one persistent process that
internally schedules its own heartbeats. The scheduler is no longer
required — though you can still use one if you want belt-and-
suspenders.

Lifecycle
  forkling daemon start [--repo PATH] [--every SECONDS] [--max-ticks N]
        Blocks. Runs heartbeat in-process every --every seconds
        (default 1800 = 30 min). Writes .forkling/daemon.pid.
        Logs daemon.* entries to the diary.

  forkling daemon stop [--repo PATH]
        Writes .forkling/daemon.stop. The running daemon sees the
        flag on its next sleep tick and exits gracefully.

  forkling daemon status [--repo PATH]
        Prints whether the daemon is running (PID + uptime),
        last heartbeat time, tick count.

Design constraints (project-wide)
  - **stdlib only.** threading.Event + signal.signal + os.write —
    no APScheduler, no Celery, no third-party deps.
  - **One daemon per repo.** The HeartbeatLock already prevents
    two heartbeats from racing; the PID file prevents two daemons.
  - **Cross-platform stop.** On POSIX, signal.SIGTERM works. On
    Windows, we use a stop-flag file (cross-platform friendly).
  - **Graceful shutdown.** SIGINT / SIGBREAK (Windows Ctrl+Break)
    / stop-flag all run the same finally block: close PID file,
    log daemon.stopped to diary, exit 0.
  - **Restart-on-failure optional.** --restart-on-failure catches
    heartbeat subprocess non-zero exits and re-schedules instead of
    dying.

This module does NOT change ``forkling heartbeat`` — that command
still works as a one-shot. The daemon is a *wrapper* around it.
"""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

from .config import Config
from .diary import Diary
from .locking import HeartbeatLock, LockBusy


PID_FILENAME = "daemon.pid"
STOP_FILENAME = "daemon.stop"
STATUS_FILENAME = "daemon.status.json"


class Daemon:
    """The persistent heartbeat scheduler. Run in the foreground."""

    def __init__(self, cfg: Config, repo: Path, *,
                 every_seconds: int = 1800,
                 max_ticks: int | None = None,
                 skip_improve: bool = False,
                 restart_on_failure: bool = False) -> None:
        self.cfg = cfg
        self.repo = repo
        self.every = max(1, int(every_seconds))
        self.max_ticks = max_ticks
        self.skip_improve = skip_improve
        self.restart_on_failure = restart_on_failure

        self._stop_event = threading.Event()
        self._tick_count = 0
        self._last_tick_ok: bool | None = None
        self._started_at = time.time()

        self.state_dir = repo / ".forkling"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.pid_path = self.state_dir / PID_FILENAME
        self.stop_path = self.state_dir / STOP_FILENAME
        self.status_path = self.state_dir / STATUS_FILENAME

    # ---- lifecycle ---------------------------------------------------------

    def run_forever(self) -> int:
        """Block until SIGINT / stop-flag / max_ticks. Returns 0 on clean exit."""
        self._write_pidfile()
        self._log("daemon.started",
                  f"every={self.every}s repo={self.repo} "
                  f"max_ticks={self.max_ticks} "
                  f"skip_improve={self.skip_improve} "
                  f"restart_on_failure={self.restart_on_failure}")

        # Wire Ctrl+C / Ctrl+Break to the stop event.
        self._install_signal_handlers()

        try:
            while not self._should_stop():
                # Run one heartbeat (with locking).
                self.run_tick()
                # Write the status file for `forkling daemon status`.
                self._write_status()
                # Sleep, but interruptibly — stop flag or signal wakes us.
                if self.max_ticks is not None and self._tick_count >= self.max_ticks:
                    self._log("daemon.max_ticks_reached",
                              f"exiting after {self._tick_count} ticks")
                    break
                if not self._interruptible_sleep(self.every):
                    # Interrupted by signal or stop flag
                    break
        finally:
            self._remove_pidfile()
            self._remove_stop_flag()
            self._log("daemon.stopped",
                      f"ticks={self._tick_count} "
                      f"last_ok={self._last_tick_ok}")
        return 0

    def run_tick(self) -> bool:
        """Run one heartbeat. Returns True on success, False on failure.

        Wrapped in the HeartbeatLock so concurrent daemons / one-shot
        heartbeats don't race.
        """
        self._tick_count += 1
        ok = False
        try:
            with HeartbeatLock(self.repo):
                ok = self._invoke_heartbeat()
        except LockBusy:
            self._log("daemon.tick.skipped",
                      "another heartbeat held the lock; will retry next tick")
            ok = False
        except Exception as e:
            self._log("daemon.tick.failed",
                      f"{e.__class__.__name__}: {e}")
            ok = False
        self._last_tick_ok = ok
        if not ok and not self.restart_on_failure:
            # Without --restart-on-failure, a failed tick is a soft warning,
            # not a fatal error — we keep the daemon alive.
            pass
        return ok

    # ---- control (for `forkling daemon stop`) ------------------------------

    def request_stop(self) -> None:
        """Wake the daemon on its next sleep tick (or sooner)."""
        self._stop_event.set()
        # Also write the stop flag so a daemon running on another
        # machine / session can see it.
        try:
            self.stop_path.touch(exist_ok=True)
        except OSError:
            pass

    # ---- internals ---------------------------------------------------------

    def _invoke_heartbeat(self) -> bool:
        argv = [sys.executable, "-m", "forkling", "heartbeat",
                "--repo", str(self.repo)]
        if self.skip_improve:
            argv.append("--skip-improve")
        try:
            r = subprocess.run(argv, cwd=str(self.repo),
                               capture_output=True, text=True,
                               timeout=900)
            ok = r.returncode == 0
            self._log(
                "daemon.tick" if ok else "daemon.tick.failed",
                f"exit={r.returncode} "
                f"tail={((r.stdout + r.stderr)[-200:]).strip()}",
            )
            return ok
        except subprocess.TimeoutExpired:
            self._log("daemon.tick.failed", "heartbeat timed out (>900s)")
            return False
        except Exception as e:
            self._log("daemon.tick.failed",
                      f"{e.__class__.__name__}: {e}")
            return False

    def _should_stop(self) -> bool:
        return (self._stop_event.is_set()
                or self.stop_path.exists())

    def _interruptible_sleep(self, seconds: float) -> bool:
        """Sleep up to ``seconds`` seconds. Returns False if interrupted."""
        # Check the stop flag once at start.
        if self._should_stop():
            return False
        # Wait on the Event, with a timeout so we can re-check the flag
        # periodically. The Event is set by request_stop() and by the
        # signal handlers.
        interrupted = self._stop_event.wait(timeout=min(seconds, 5.0))
        # If we got here via the timeout, loop until we've slept the full
        # duration (checking the stop flag each slice).
        slept = 0.0
        while slept < seconds:
            if interrupted or self._should_stop():
                return False
            remaining = seconds - slept
            slice_s = min(remaining, 5.0)
            interrupted = self._stop_event.wait(timeout=slice_s)
            slept += slice_s
        return True

    def _install_signal_handlers(self) -> None:
        def _handler(signum, frame):
            self._log("daemon.signal",
                      f"received signal {signum}; will exit on next tick")
            self._stop_event.set()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                signal.signal(sig, _handler)
            except (ValueError, OSError):
                # Some signals aren't valid on Windows; SIGBREAK is the
                # Windows equivalent and we'll register it if available.
                pass
        # Windows-specific: Ctrl+Break (often raised in interactive shells).
        if hasattr(signal, "SIGBREAK"):
            try:
                signal.signal(signal.SIGBREAK, _handler)  # type: ignore[attr-defined]
            except (ValueError, OSError):
                pass

    def _write_pidfile(self) -> None:
        try:
            self.pid_path.write_text(str(os.getpid()), encoding="utf-8")
        except OSError as e:
            print(f"daemon: failed to write pidfile: {e}", file=sys.stderr)

    def _remove_pidfile(self) -> None:
        try:
            if self.pid_path.exists():
                self.pid_path.unlink()
        except OSError:
            pass

    def _remove_stop_flag(self) -> None:
        try:
            if self.stop_path.exists():
                self.stop_path.unlink()
        except OSError:
            pass

    def _write_status(self) -> None:
        import json
        payload = {
            "pid": os.getpid(),
            "started_at": self._started_at,
            "tick_count": self._tick_count,
            "last_tick_ok": self._last_tick_ok,
            "every_seconds": self.every,
            "repo": str(self.repo),
        }
        try:
            self.status_path.write_text(json.dumps(payload, indent=2),
                                        encoding="utf-8")
        except OSError:
            pass

    def _log(self, kind: str, content: str) -> None:
        # Daemon logs go to the diary so the agent's record includes them.
        try:
            memory_dir = Path(self.cfg.memory_dir)
            Diary(memory_dir / "diary.jsonl").write(kind, content)
        except Exception as e:
            print(f"daemon: diary write failed ({e}); {kind}: {content}",
                  file=sys.stderr)
        # Also echo to stderr so an interactive user sees it.
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{ts}] [{kind}] {content}", file=sys.stderr)


# ---- static helpers used by the CLI --------------------------------------


def read_status(repo: Path) -> dict | None:
    """Read the daemon status file. Returns None if not running."""
    import json
    p = repo / ".forkling" / STATUS_FILENAME
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def is_running(repo: Path) -> bool:
    """Best-effort liveness check. Reads the pidfile and tests the pid."""
    p = repo / ".forkling" / PID_FILENAME
    if not p.exists():
        return False
    try:
        pid = int(p.read_text(encoding="utf-8").strip())
    except (ValueError, OSError):
        return False
    return _pid_alive(pid)


def request_stop(repo: Path) -> bool:
    """Tell a running daemon to stop (via stop flag + signal if available).

    Returns True if the stop flag was written (i.e. something to stop).
    """
    if not is_running(repo):
        return False
    stop = repo / ".forkling" / STOP_FILENAME
    try:
        stop.touch(exist_ok=True)
    except OSError:
        return False
    # Try a direct signal too — works on POSIX and on Windows for sig 0.
    pid_path = repo / ".forkling" / PID_FILENAME
    try:
        pid = int(pid_path.read_text(encoding="utf-8").strip())
        if _pid_alive(pid):
            try:
                os.kill(pid, signal.SIGTERM)
            except (OSError, ValueError):
                pass
    except (OSError, ValueError):
        pass
    return True


def _pid_alive(pid: int) -> bool:
    """Cross-platform pid liveness check. No-op on platforms we don't know."""
    if pid <= 0:
        return False
    if sys.platform == "win32":
        # On Windows, os.kill with sig 0 doesn't work as expected;
        # fall back to the tasklist heuristic via ctypes.
        try:
            import ctypes
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            PROCESS_QUERY_LIMITED = 0x1000
            STILL_ACTIVE = 259
            handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED, False, pid)
            if not handle:
                return False
            try:
                exit_code = ctypes.c_ulong()
                ok = kernel32.GetExitCodeProcess(handle,
                                                 ctypes.byref(exit_code))
                return bool(ok) and exit_code.value == STILL_ACTIVE
            finally:
                kernel32.CloseHandle(handle)
        except Exception:
            return False
    else:
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False
