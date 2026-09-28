"""Run a command detached, with a smart JSON heartbeat.

Companion to scripts/run_detached.py: same two-phase protocol
(bash-friendly spawn + detached supervision), but the heartbeat
file is a JSON blob with liveness + progress signals so a future
check_run call can distinguish:

  - actively making progress (log_size growing, ckpt_size growing,
    ollama_alive=True)
  - mid-call (log_size static, ollama_alive=True) — Ollama slow
    but responsive
  - hung on Ollama (log_size static, ollama_alive=False)
  - crashed (heartbeat not updating at all)

The supervisor's heartbeat thread writes the JSON blob at every
--interval seconds. check_run parses the JSON and renders a
human-readable status.

Args (in addition to run_detached.py's):
  --ckpt PATH        Path to a checkpoint JSONL the inner command
                     writes (its mtime + size are reported).
  --ollama-url URL   Ollama endpoint to ping (default
                     http://127.0.0.1:11434). Pass "" to disable.

Heartbeat JSON schema:
  {
    "schema_version": 1,
    "timestamp": <unix-epoch-seconds>,
    "supervisor_pid": <int>,
    "inner_pid": <int or null>,
    "phase": "starting" | "running" | "complete" | "complete-<rc>",
    "log_path": "<absolute>",
    "log_size": <int>,
    "log_last_touched_age_s": <float>,
    "ckpt_path": "<absolute or null>",
    "ckpt_size": <int or null>,
    "ckpt_last_touched_age_s": <float or null>,
    "ollama_url": "<url or null>",
    "ollama_alive": <bool or null>,
    "ollama_check_age_s": <float or null>,
    "last_message": "<human-readable one-liner>"
  }
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
DEFAULT_OLLAMA = "http://127.0.0.1:11434"
PING_TIMEOUT_S = 2.0


def _parse_args(argv: list[str]) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--heartbeat", required=True)
    ap.add_argument("--pid", required=True)
    ap.add_argument("--log", required=True)
    ap.add_argument("--marker", default=None)
    ap.add_argument("--interval", type=int, default=10)
    ap.add_argument("--ckpt", default=None,
                    help="Checkpoint JSONL the inner command writes (optional)")
    ap.add_argument("--ollama-url", default=DEFAULT_OLLAMA,
                    help="Ollama endpoint to ping (default: "
                         f"{DEFAULT_OLLAMA}; pass '' to disable)")
    ap.add_argument("--detached", action="store_true",
                    help=argparse.SUPPRESS)
    args, cmd = ap.parse_known_args(argv)
    if cmd and cmd[0] == "--":
        cmd = cmd[1:]
    if not cmd:
        ap.error("must specify a command after --")
    args.cmd = cmd
    if args.ollama_url == "":
        args.ollama_url = None
    return args


def _file_size(p: Path) -> int:
    try:
        return p.stat().st_size
    except OSError:
        return -1


def _file_age_s(p: Path) -> float | None:
    try:
        return max(0.0, time.time() - p.stat().st_mtime)
    except OSError:
        return None


def _ping_ollama(url: str, timeout: float = PING_TIMEOUT_S) -> bool:
    try:
        req = urllib.request.Request(url + "/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return 200 <= r.status < 400
    except (urllib.error.URLError, OSError, TimeoutError):
        return False


def _detect_inner_pid(inner: subprocess.Popen | None) -> int | None:
    if inner is None:
        return None
    try:
        return inner.pid
    except Exception:
        return None


def _phase_for(inner: subprocess.Popen | None) -> str:
    if inner is None:
        return "starting"
    rc = inner.poll()
    if rc is None:
        return "running"
    return f"complete-{rc}" if rc != 0 else "complete"


def _build_heartbeat(args: argparse.Namespace,
                     inner: subprocess.Popen | None,
                     log_path: Path,
                     ckpt_path: Path | None,
                     last_ollama_check: float | None,
                     last_ollama_alive: bool | None,
                     last_message: str) -> dict:
    now = time.time()
    return {
        "schema_version": SCHEMA_VERSION,
        "timestamp": now,
        "supervisor_pid": os.getpid(),
        "inner_pid": _detect_inner_pid(inner),
        "phase": _phase_for(inner),
        "log_path": str(log_path.resolve()),
        "log_size": _file_size(log_path),
        "log_last_touched_age_s": _file_age_s(log_path),
        "ckpt_path": str(ckpt_path.resolve()) if ckpt_path else None,
        "ckpt_size": _file_size(ckpt_path) if ckpt_path else None,
        "ckpt_last_touched_age_s": _file_age_s(ckpt_path) if ckpt_path else None,
        "ollama_url": args.ollama_url,
        "ollama_alive": last_ollama_alive,
        "ollama_check_age_s": (
            max(0.0, now - last_ollama_check)
            if last_ollama_check is not None else None
        ),
        "last_message": last_message,
    }


def _write_heartbeat(path: Path, data: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(path)


def _heartbeat_loop(args: argparse.Namespace,
                    inner: subprocess.Popen | None,
                    log_path: Path,
                    ckpt_path: Path | None,
                    hb_path: Path,
                    stop: threading.Event,
                    last_message_holder: list) -> None:
    last_ollama_check: float | None = None
    last_ollama_alive: bool | None = None
    last_message = "supervisor started"
    while not stop.wait(args.interval):
        now = time.time()
        if args.ollama_url and (
            last_ollama_check is None
            or (now - last_ollama_check) >= args.interval
        ):
            last_ollama_alive = _ping_ollama(args.ollama_url)
            last_ollama_check = now
        inner_alive = inner is not None and inner.poll() is None
        ckpt_age = _file_age_s(ckpt_path) if ckpt_path else None
        if inner_alive:
            if args.ollama_url and last_ollama_alive is False:
                last_message = ("inner command alive but Ollama is "
                                "NOT responding")
            elif ckpt_path and ckpt_age is not None and ckpt_age > args.interval * 6:
                last_message = (f"inner command alive; checkpoint "
                                f"hasn't grown in {ckpt_age:.0f}s")
            else:
                last_message = "inner command running; heartbeat fresh"
        else:
            last_message = "inner command not running"
        last_message_holder[0] = last_message
        hb = _build_heartbeat(args, inner, log_path, ckpt_path,
                              last_ollama_check, last_ollama_alive,
                              last_message)
        try:
            _write_heartbeat(hb_path, hb)
        except OSError:
            pass


def _phase1_spawn_detached(args: argparse.Namespace) -> int:
    hb_path = Path(args.heartbeat)
    pid_path = Path(args.pid)
    log_path = Path(args.log)
    for p in (hb_path, pid_path, log_path):
        p.parent.mkdir(parents=True, exist_ok=True)

    if args.marker and Path(args.marker).exists():
        print(f"[smart-detach] marker {args.marker} exists; nothing to do")
        return 0

    log_f = open(log_path, "a", encoding="utf-8")
    env = dict(os.environ)
    env["_DETACHED"] = "1"
    creationflags = 0
    if sys.platform == "win32":
        creationflags = (subprocess.DETACHED_PROCESS
                         | subprocess.CREATE_NEW_PROCESS_GROUP)
    argv = [sys.executable, str(Path(__file__).resolve())] + \
        ["--heartbeat", args.heartbeat, "--pid", args.pid, "--log", args.log]
    if args.marker:
        argv += ["--marker", args.marker]
    if args.ckpt:
        argv += ["--ckpt", args.ckpt]
    argv += ["--ollama-url", args.ollama_url if args.ollama_url else ""]
    argv += ["--interval", str(args.interval), "--detached", "--"] + args.cmd
    p = subprocess.Popen(
        argv,
        stdout=log_f, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
        creationflags=creationflags, close_fds=True, env=env,
    )
    pid_path.write_text(f"{p.pid}\n")
    log_f.close()
    print(f"[smart-detach] spawned supervisor PID={p.pid}")
    print(f"[smart-detach] heartbeat={hb_path}  log={log_path}  pid={pid_path}")
    if args.ckpt:
        print(f"[smart-detach] ckpt={args.ckpt}")
    if args.ollama_url:
        print(f"[smart-detach] ollama={args.ollama_url} (ping every {args.interval}s)")
    else:
        print(f"[smart-detach] ollama ping disabled")
    return 0


def _phase2_run_inner(args: argparse.Namespace) -> int:
    hb_path = Path(args.heartbeat)
    log_path = Path(args.log)
    ckpt_path = Path(args.ckpt) if args.ckpt else None
    log_f = open(log_path, "a", encoding="utf-8")
    print(f"[smart-detach-supervisor] pid={os.getpid()} starting inner command",
          flush=True, file=log_f)

    env = dict(os.environ)
    cmd = list(args.cmd)
    while cmd and "=" in cmd[0] and not cmd[0].startswith("-") \
            and cmd[0].count("=") >= 1 and "$" not in cmd[0]:
        key, _, val = cmd[0].partition("=")
        env[key] = val
        cmd.pop(0)

    inner = subprocess.Popen(
        cmd,
        stdout=log_f, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
        close_fds=True, env=env,
    )
    print(f"[smart-detach-supervisor] inner PID={inner.pid}",
          flush=True, file=log_f)

    last_message_holder: list = [""]
    stop = threading.Event()
    hb_thread = threading.Thread(
        target=_heartbeat_loop,
        args=(args, inner, log_path, ckpt_path, hb_path, stop,
              last_message_holder),
        daemon=True,
    )
    hb_thread.start()

    rc = inner.wait()
    stop.set()
    hb_thread.join(timeout=5.0)

    final = _build_heartbeat(args, inner, log_path, ckpt_path,
                             time.time(), last_ollama_alive,
                             last_message_holder[0])
    try:
        _write_heartbeat(hb_path, final)
    except OSError:
        pass

    print(f"[smart-detach-supervisor] inner command exited rc={rc}",
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
