"""Read a smart-detached heartbeat JSON and render human status.

Companion to scripts/run_smart_detached.py.

Reads the heartbeat JSON file (which that script writes every
--interval seconds) and renders a one-screen status report:
  - phase (starting / running / complete-N / complete)
  - supervisor PID, inner PID
  - log file size + last-touched age
  - checkpoint file size + last-touched age (if --ckpt was used)
  - Ollama alive + last-check age (if --ollama-url was set)
  - last_message

Calls a run "stalled" if heartbeat is fresh but log/ckpt haven't
grown AND Ollama is unreachable (i.e., the supervisor is alive
but the inner command is hung on Ollama).

Usage:
    python scripts/check_smart.py --heartbeat PATH [--fresh-s SECONDS]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path


FRESH_S = 30  # 3x the default --interval of 10s; tune to taste


def _age_str(secs: float | None) -> str:
    if secs is None:
        return "n/a"
    if secs < 1:
        return "just now"
    if secs < 60:
        return f"{secs:.0f}s ago"
    if secs < 3600:
        return f"{secs/60:.1f}min ago"
    return f"{secs/3600:.1f}h ago"


def _size_str(n: int | None) -> str:
    if n is None or n < 0:
        return "n/a"
    if n < 1024:
        return f"{n} B"
    if n < 1024 * 1024:
        return f"{n/1024:.1f} KB"
    return f"{n/1024/1024:.1f} MB"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--heartbeat", required=True)
    ap.add_argument("--fresh-s", type=int, default=FRESH_S,
                    help="Heartbeat age (seconds) above which we declare "
                         "the supervisor dead (default 30)")
    ap.add_argument("--log-tail", type=int, default=8)
    ap.add_argument("--show-raw", action="store_true",
                    help="Print the raw heartbeat JSON in addition to summary")
    args = ap.parse_args()

    hb_path = Path(args.heartbeat)
    if not hb_path.exists():
        print(f"[check] heartbeat {hb_path} does NOT exist")
        return 1
    try:
        hb = json.loads(hb_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        print(f"[check] heartbeat {hb_path} not parseable: {e}")
        return 1

    now = time.time()
    hb_age = now - hb.get("timestamp", 0)
    supervisor_alive = hb_age < args.fresh_s
    inner_phase = hb.get("phase", "?")
    inner_alive = inner_phase == "running"
    ollama_alive = hb.get("ollama_alive")

    print(f"=== {hb_path.name}  (smart-detached run) ===")
    print(f"  schema_version: {hb.get('schema_version', '?')}")
    print(f"  supervisor heartbeat age: {hb_age:.0f}s "
          f"({'alive' if supervisor_alive else 'STALE'})")
    print(f"  supervisor_pid: {hb.get('supervisor_pid', '?')}")
    print(f"  inner_pid: {hb.get('inner_pid', '?')}")
    print(f"  phase: {inner_phase}")
    print(f"  last_message: {hb.get('last_message', '?')}")
    print()
    print(f"  log: {hb.get('log_path', '?')}")
    print(f"    size: {_size_str(hb.get('log_size'))}")
    print(f"    last touched: {_age_str(hb.get('log_last_touched_age_s'))}")
    print()
    ckpt = hb.get("ckpt_path")
    if ckpt:
        print(f"  ckpt: {ckpt}")
        print(f"    size: {_size_str(hb.get('ckpt_size'))}")
        print(f"    last touched: "
              f"{_age_str(hb.get('ckpt_last_touched_age_s'))}")
    else:
        print(f"  ckpt: (not tracked)")
    print()
    if hb.get("ollama_url"):
        ollama_status = (
            "ALIVE" if ollama_alive
            else "DEAD" if ollama_alive is False
            else "unknown"
        )
        print(f"  ollama: {hb.get('ollama_url')}  status: {ollama_status}  "
              f"last check: {_age_str(hb.get('ollama_check_age_s'))}")
    else:
        print(f"  ollama: (ping disabled)")

    # Verdict
    print()
    print(f"  === verdict ===")
    if not supervisor_alive:
        print(f"    STALE supervisor (heartbeat {hb_age:.0f}s old; "
              f"threshold {args.fresh_s}s)")
        print(f"    -> process tree is dead or wedged")
    elif inner_phase == "complete":
        print(f"    COMPLETE (phase={inner_phase})")
    elif inner_phase.startswith("complete-"):
        rc = inner_phase.split("-", 1)[1]
        print(f"    INNER EXITED with rc={rc}")
    elif inner_alive and ollama_alive is False:
        print(f"    STALLED: inner running, Ollama NOT responding")
    elif inner_alive:
        print(f"    HEALTHY: inner running, Ollama responsive")
    else:
        print(f"    UNKNOWN state: phase={inner_phase}")

    if args.show_raw:
        print()
        print("--- raw heartbeat ---")
        print(json.dumps(hb, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
