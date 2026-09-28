"""Check on a detached run's liveness and progress.

Reads the heartbeat file mtime to determine whether the
supervisor is still alive. If the heartbeat is stale, the
supervisor or its inner command has crashed; read the log
for diagnosis.

Usage:
    python scripts/check_run.py --heartbeat PATH [--pid PATH] [--log PATH]

Prints:
  - PID (if --pid given)
  - heartbeat age in seconds
  - "alive" if heartbeat is fresh (< 2 minutes)
  - "stale" if heartbeat older than 2 minutes
  - last few lines of the log (if --log given)
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

FRESH_S = 120  # 2 minutes; heartbeat interval is 30s by default


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--heartbeat", required=True)
    ap.add_argument("--pid", default=None)
    ap.add_argument("--log", default=None)
    ap.add_argument("--log-tail", type=int, default=20)
    ap.add_argument("--fresh-s", type=int, default=FRESH_S)
    args = ap.parse_args()

    hb = Path(args.heartbeat)
    if not hb.exists():
        print(f"[check] heartbeat {hb} does NOT exist")
        return 1
    age = time.time() - hb.stat().st_mtime
    status = "alive" if age < args.fresh_s else "stale"
    print(f"[check] heartbeat={hb}  age={age:.0f}s  status={status}")
    if args.pid:
        pid_path = Path(args.pid)
        if pid_path.exists():
            print(f"[check] pid={pid_path.read_text().strip()}")
        else:
            print(f"[check] pid file {pid_path} missing")
    if args.log:
        log_path = Path(args.log)
        if log_path.exists():
            print(f"[check] log tail ({args.log_tail} lines):")
            lines = log_path.read_text(errors="replace").splitlines()
            for line in lines[-args.log_tail:]:
                print(f"  {line}")
        else:
            print(f"[check] log {log_path} missing")
    return 0


if __name__ == "__main__":
    sys.exit(main())
