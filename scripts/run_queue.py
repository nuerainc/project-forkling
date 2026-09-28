"""Run a queue of experiment stages sequentially, with per-stage heartbeats.

Why: the 4 GB box has one GPU and one Ollama model resident. Two
concurrent protocol-2 runs contend for VRAM and time out
(`qwen3:4b` already times out at infra=1.00). So stages MUST be
serial. This script enforces serial execution across a declared
queue so nothing has to be babysat.

Design:
  - Read a queue manifest (JSON): a list of stages, run in order.
  - Stage type "wait": poll for a marker file to appear (used to join
    a run that was already launched detached before this queue
    started). Times out rather than hanging forever.
  - Stage type "run": spawn the inner command, stream its output to
    the stage log, write a per-stage JSON heartbeat while it runs.
  - A stage whose marker already exists is SKIPPED (idempotent
    re-runs: safe to re-launch the queue after a crash).
  - Top-level queue heartbeat records which stage is current, how
    many are done, and the queue's own pid.

Every stage is pre-registered BEFORE it runs. The queue deliberately
STOPS at any stage whose pre-registration defines a data-dependent
gate (e.g. v10b calibration -> freeze rule), so the gate is applied
by a human/agent with the numbers in hand rather than auto-passed.

Heartbeat schema (per stage, and for the queue itself) is compatible
with scripts/check_smart.py: `phase`, `log_size`, `ckpt_size`,
`last_message`, plus `stage` and `stages_total` extras.

Usage:
  python scripts/run_queue.py --queue queue.json --queue-heartbeat \
      results/queue.heartbeat --queue-log results/queue.log
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path


SCHEMA_VERSION = 1
PING_TIMEOUT_S = 2.0
POLL_S = 5.0


def _parse_args(argv: list[str]) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--queue", required=True,
                    help="JSON manifest: list of stages")
    ap.add_argument("--queue-heartbeat", required=True)
    ap.add_argument("--queue-log", required=True)
    ap.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    ap.add_argument("--stop-after", default=None,
                    help="Stage name to stop after (inclusive). Used to "
                         "honour a pre-registered gate without editing "
                         "the manifest.")
    ap.add_argument("--detached", action="store_true",
                    help=argparse.SUPPRESS)
    args, cmd = ap.parse_known_args(argv)
    if cmd and cmd[0] == "--":
        cmd = cmd[1:]
    args.leftover = cmd
    return args


def _ping(url: str, timeout: float = PING_TIMEOUT_S) -> bool:
    if not url:
        return True
    try:
        req = urllib.request.Request(url.rstrip("/") + "/api/tags",
                                     method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return 200 <= r.status < 400
    except (urllib.error.URLError, OSError, TimeoutError):
        return False


def _size(p: Path) -> int:
    try:
        return p.stat().st_size
    except OSError:
        return -1


def _age_s(p: Path) -> float | None:
    try:
        return max(0.0, time.time() - p.stat().st_mtime)
    except OSError:
        return None


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(path)


def _repo() -> Path:
    return Path(__file__).resolve().parent.parent


def _resolve(p: str) -> Path:
    q = Path(p)
    return q if q.is_absolute() else _repo() / q


def _qhb(args: argparse.Namespace, stage: str, idx: int, total: int,
         phase: str, message: str, stage_hb: dict | None) -> None:
    data = {
        "schema_version": SCHEMA_VERSION,
        "timestamp": time.time(),
        "queue_pid": os.getpid(),
        "stage": stage,
        "stage_index": idx,
        "stages_total": total,
        "phase": phase,
        "last_message": message,
        "stage_heartbeat": stage_hb,
    }
    try:
        _write_json(Path(args.queue_heartbeat), data)
    except OSError:
        pass


def _run_stage(args: argparse.Namespace, stage: dict, idx: int,
               total: int, qlog) -> int:
    name = stage["name"]
    marker = _resolve(stage["marker"]) if stage.get("marker") else None
    ckpt = _resolve(stage["ckpt"]) if stage.get("ckpt") else None
    log = _resolve(stage["log"])
    hb = _resolve(stage["heartbeat"]) if stage.get("heartbeat") else None

    if marker and marker.exists():
        msg = f"skip {name}: marker already present"
        print(f"[queue] {msg}", flush=True, file=qlog)
        _qhb(args, name, idx, total, "skipped", msg, None)
        return 0

    cmd = stage["cmd"]
    if isinstance(cmd, str):
        cmd = cmd.split()
    env = dict(os.environ)
    for kv in stage.get("env", []):
        k, _, v = kv.partition("=")
        env[k] = v

    log.parent.mkdir(parents=True, exist_ok=True)
    stop = threading.Event()
    inner_box: list = [None]

    def _beat() -> None:
        last_ping = 0.0
        alive = None
        while not stop.wait(10.0):
            now = time.time()
            if now - last_ping >= 10.0:
                alive = _ping(args.ollama_url)
                last_ping = now
            inner = inner_box[0]
            running = inner is not None and inner.poll() is None
            ck_age = _age_s(ckpt) if ckpt else None
            if not running:
                msg = "inner not running"
            elif alive is False:
                msg = "inner alive but Ollama NOT responding"
            elif ckpt and ck_age is not None and ck_age > 180:
                msg = f"inner alive; checkpoint static for {ck_age:.0f}s"
            else:
                msg = "inner running; progress"
            if hb:
                _write_json(hb, {
                    "schema_version": SCHEMA_VERSION,
                    "timestamp": time.time(),
                    "stage": name,
                    "queue_pid": os.getpid(),
                    "inner_pid": inner.pid if inner else None,
                    "phase": "running" if running else "starting",
                    "log_path": str(log),
                    "log_size": _size(log),
                    "log_last_touched_age_s": _age_s(log),
                    "ckpt_path": str(ckpt) if ckpt else None,
                    "ckpt_size": _size(ckpt) if ckpt else None,
                    "ckpt_last_touched_age_s": ck_age,
                    "ollama_url": args.ollama_url,
                    "ollama_alive": alive,
                    "last_message": msg,
                })
            _qhb(args, name, idx, total, "running", msg, None)

    print(f"[queue] start {name}", flush=True, file=qlog)
    print(f"[queue] cmd: {' '.join(cmd)}", flush=True, file=qlog)
    lf = open(log, "a", encoding="utf-8")
    t = threading.Thread(target=_beat, daemon=True)
    t.start()
    inner = subprocess.Popen(cmd, stdout=lf, stderr=subprocess.STDOUT,
                             stdin=subprocess.DEVNULL, cwd=str(_repo()),
                             env=env)
    inner_box[0] = inner
    rc = inner.wait()
    stop.set()
    t.join(timeout=5.0)
    lf.close()
    print(f"[queue] done {name} rc={rc}", flush=True, file=qlog)

    if rc != 0:
        msg = f"{name} exited rc={rc}"
        _qhb(args, name, idx, total, f"failed-{rc}", msg, None)
        return rc
    if marker and not marker.exists():
        msg = f"{name} rc=0 but marker missing: {marker.name}"
        _qhb(args, name, idx, total, "incomplete", msg, None)
        print(f"[queue] WARN {msg}", flush=True, file=qlog)
        return 3
    msg = f"{name} complete"
    _qhb(args, name, idx, total, "complete", msg, None)
    return 0


def _wait_stage(args: argparse.Namespace, stage: dict, idx: int,
                total: int, qlog) -> int:
    """Poll for a marker that an already-detached run will produce."""
    name = stage["name"]
    marker = _resolve(stage["marker"])
    timeout_s = float(stage.get("timeout_s", 14400))
    print(f"[queue] waiting on {name} -> {marker.name} "
          f"(timeout {timeout_s:.0f}s)", flush=True, file=qlog)
    waited = 0.0
    while waited < timeout_s:
        if marker.exists():
            msg = f"{name} satisfied after {waited:.0f}s"
            print(f"[queue] {msg}", flush=True, file=qlog)
            _qhb(args, name, idx, total, "complete", msg, None)
            return 0
        stop = threading.Event()
        _qhb(args, name, idx, total, "waiting",
             f"waiting {waited:.0f}s / {timeout_s:.0f}s for "
             f"{marker.name}", None)
        stop.wait(POLL_S)
        waited += POLL_S
    msg = f"{name} TIMED OUT after {timeout_s:.0f}s"
    print(f"[queue] {msg}", flush=True, file=qlog)
    _qhb(args, name, idx, total, "timeout", msg, None)
    return 4


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    manifest = json.loads(_resolve(args.queue).read_text(encoding="utf-8"))
    stages = manifest["stages"]
    total = len(stages)

    qlog_path = Path(args.queue_log)
    qlog_path.parent.mkdir(parents=True, exist_ok=True)
    qlog = open(qlog_path, "a", encoding="utf-8")
    print(f"[queue] {total} stage(s) from {args.queue}", flush=True,
          file=qlog)

    rc_all = 0
    for i, stage in enumerate(stages, start=1):
        kind = stage.get("type", "run")
        if args.stop_after and stage["name"] == args.stop_after:
            print(f"[queue] stop-after reached at {stage['name']}; "
                  f"halting before next stage", flush=True, file=qlog)
            _qhb(args, stage["name"], i, total, "stopped",
                 "stop-after: gate requires human/agent review",
                 None)
            break
        if kind == "wait":
            rc = _wait_stage(args, stage, i, total, qlog)
        else:
            rc = _run_stage(args, stage, i, total, qlog)
        if rc != 0:
            print(f"[queue] ABORT at {stage['name']} rc={rc}; "
                  f"later stages not run", flush=True, file=qlog)
            rc_all = rc
            break

    qlog.close()
    return rc_all


if __name__ == "__main__":
    sys.exit(main())
