#!/usr/bin/env python
"""forkland heartbeat — one autonomous beat.

Runs the agent's three maintenance beats:

  1. self-improve    (propose a tiny safe change, test, ship or roll back)
  2. paper append    (add a status block to paper/paper.md)
  3. ledger verify   (verify the SHA-256 chain)

Zero MiniMax dependency — this script is plain Python + Ollama + git.
Schedule with cron, Windows Task Scheduler, or `mavis cron create`.

Usage::

    python scripts/heartbeat.py                  # default repo (cwd)
    python scripts/heartbeat.py --repo /path
    python scripts/heartbeat.py --skip-improve   # just verify + paper

Exit codes::

    0  every step succeeded
    1  at least one step failed (see heartbeat.log)
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--repo", help="Repo root (defaults to cwd).")
    p.add_argument("--skip-improve", action="store_true",
                   help="Skip the self-improve step (useful for tests).")
    p.add_argument("--memory-dir", default=None,
                   help="forkland memory dir (default ~/.forkling).")
    args = p.parse_args()

    repo = Path(args.repo).resolve() if args.repo else Path.cwd().resolve()
    log_dir = repo / ".forkling"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "heartbeat.log"

    steps = []

    def run(name: str, *cmd: str, timeout: int = 60) -> None:
        r = subprocess.run(list(cmd), cwd=repo, capture_output=True,
                           text=True, timeout=timeout)
        steps.append({"name": name, "ok": r.returncode == 0,
                      "tail": (r.stdout + r.stderr)[-400:],
                      "rc": r.returncode})

    # 1. self-improve (the heavy step).
    if not args.skip_improve:
        run("self-improve", "python", "-m", "forkling", "self-improve",
            "--repo", str(repo), timeout=900)

    # 2. paper append.
    run("paper.append", "python", "-m", "forkling", "paper", "append",
        "--path", "paper/paper.md", timeout=60)

    # 3. ledger verify.
    run("verify", "python", "-m", "forkling", "verify", timeout=30)

    out = {
        "ran_at": time.time(),
        "repo": str(repo),
        "steps": steps,
    }
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(out) + "\n")

    summary = {s["name"]: s["ok"] for s in steps}
    print(json.dumps(out, indent=2))
    return 0 if all(s["ok"] for s in steps) else 1


if __name__ == "__main__":
    raise SystemExit(main())