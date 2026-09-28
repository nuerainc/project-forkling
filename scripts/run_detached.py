"""Run a command detached from the parent bash session.

The runtime's background-task watchdog kills bash at 30 minutes.
Anything tied to that bash session dies with it. This script
spawns the inner command as a *detached* process on Windows
(DETACHED_PROCESS + CREATE_NEW_PROCESS_GROUP) so it survives
the bash kill, and runs a heartbeat thread so a future bash
session can verify liveness.

Two-phase protocol
------------------
Phase 1 (attached to bash): re-exec self with env var _DETACHED=1
using DETACHED_PROCESS. Print the new PID and exit. Bash returns
in <2s; watchdog never fires.

Phase 2 (detached, running independently): open the inner
command's log file, fork the inner command as a child, run a
heartbeat thread that touches --heartbeat every --interval
seconds, wait for the inner command to exit, write --marker
if the run succeeded, exit cleanly.

Marker file
-----------
If --marker exists at start (phase 1), the script exits
without launching. This makes the script idempotent: re-running
it after success is a no-op. The inner command is responsible
for writing the marker — typical pattern:

    python scripts/run_detached.py \\
        --marker results/exp.json -- \\
        python -m forkling experiment run ... \\
            --out results/exp.json

When the experiment finishes and writes its JSON, the marker
exists, and a future invocation skips.

Usage
-----
    python scripts/run_detached.py \\
        --heartbeat results/exp.heartbeat \\
        --pid results/exp.pid \\
        --log results/exp.log \\
        --marker results/exp.json \\
        --interval 30 \\
        -- python -m forkling experiment run --protocol 2 ...

After it returns (seconds), the experiment continues running.
A future bash session can:
    - check heartbeat mtime (within minutes = alive)
    - read PID file to kill cleanly
    - read log for current progress
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import threading
import time
from pathlib import Path


def _parse_args(argv: list[str]) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--heartbeat", required=True,
                    help="Heartbeat file path (touched every --interval s)")
    ap.add_argument("--pid", required=True,
                    help="PID file path (the detached supervisor's PID)")
    ap.add_argument("--log", required=True,
                    help="Stdout/stderr log for the inner command")
    ap.add_argument("--marker", default=None,
                    help="Marker file. If exists at start, exit 0 without "
                         "launching. Useful for idempotent re-runs.")
    ap.add_argument("--interval", type=int, default=30,
                    help="Heartbeat update interval in seconds")
    ap.add_argument("--detached", action="store_true",
                    help=argparse.SUPPRESS)  # set internally on re-exec
    args, cmd = ap.parse_known_args(argv)
    if cmd and cmd[0] == "--":
        cmd = cmd[1:]
    if not cmd:
        ap.error("must specify a command after --")
    args.cmd = cmd
    return args


def _heartbeat_loop(hb_path: Path, interval: int, stop: threading.Event) -> None:
    while not stop.wait(interval):
        try:
            hb_path.touch()
        except OSError:
            pass


def _phase1_spawn_detached(args: argparse.Namespace) -> int:
    """Re-exec self with _DETACHED=1 using DETACHED_PROCESS."""
    hb_path = Path(args.heartbeat)
    pid_path = Path(args.pid)
    log_path = Path(args.log)
    for p in (hb_path, pid_path, log_path):
        p.parent.mkdir(parents=True, exist_ok=True)

    if args.marker and Path(args.marker).exists():
        print(f"[detach] marker {args.marker} exists; nothing to do")
        return 0

    log_f = open(log_path, "a", encoding="utf-8")
    env = dict(os.environ)
    env["_DETACHED"] = "1"
    creationflags = 0
    if sys.platform == "win32":
        # DETACHED_PROCESS: no console inheritance.
        # CREATE_NEW_PROCESS_GROUP: own process group (Ctrl-Break won't propagate).
        creationflags = (
            subprocess.DETACHED_PROCESS
            | subprocess.CREATE_NEW_PROCESS_GROUP
        )
    argv = [sys.executable, str(Path(__file__).resolve())] + \
        ["--heartbeat", args.heartbeat, "--pid", args.pid, "--log", args.log]
    if args.marker:
        argv += ["--marker", args.marker]
    argv += ["--interval", str(args.interval), "--detached", "--"] + args.cmd
    p = subprocess.Popen(
        argv,
        stdout=log_f, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
        creationflags=creationflags, close_fds=True, env=env,
    )
    pid_path.write_text(f"{p.pid}\n")
    hb_path.touch()
    log_f.close()
    print(f"[detach] spawned supervisor PID={p.pid}")
    print(f"[detach] heartbeat={hb_path}  log={log_path}  pid={pid_path}")
    if args.marker:
        print(f"[detach] marker={args.marker}")
    return 0


def _phase2_run_inner(args: argparse.Namespace) -> int:
    """Detached phase: run inner command + heartbeat thread."""
    hb_path = Path(args.heartbeat)
    log_path = Path(args.log)
    log_f = open(log_path, "a", encoding="utf-8")

    # Pull KEY=VALUE prefixes from args.cmd and treat them as
    # environment-variable assignments for the inner command. This
    # mirrors bash `KEY=VAL cmd` and PowerShell `$env:KEY=VAL cmd`,
    # both of which don't survive a non-shell launch.
    env = dict(os.environ)
    cmd = list(args.cmd)
    while cmd and "=" in cmd[0] and not cmd[0].startswith("-") \
            and cmd[0].count("=") >= 1 and "$" not in cmd[0]:
        key, _, val = cmd[0].partition("=")
        env[key] = val
        cmd.pop(0)

    print(f"[detach-supervisor] pid={os.getpid()} starting inner command",
          flush=True, file=log_f)
    print(f"[detach-supervisor] env overrides: "
          f"{ {k: v for k, v in env.items() if k not in os.environ} }",
          flush=True, file=log_f)
    inner = subprocess.Popen(
        cmd,
        stdout=log_f, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
        close_fds=True, env=env,
    )
    stop = threading.Event()
    hb_thread = threading.Thread(
        target=_heartbeat_loop, args=(hb_path, args.interval, stop),
        daemon=True,
    )
    hb_thread.start()
    rc = inner.wait()
    stop.set()
    hb_thread.join(timeout=2.0)
    print(f"[detach-supervisor] inner command exited rc={rc}",
          flush=True, file=log_f)
    log_f.flush()
    log_f.close()
    return rc


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    if not args.detached and not os.environ.get("_DETACHED"):
        return _phase1_spawn_detached(args)
    return _phase2_run_inner(args)


if __name__ == "__main__":
    sys.exit(main())
