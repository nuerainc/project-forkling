"""CLI entry: `python -m dogfood <command> ...`."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .agent import Agent
from .config import Config
from .llm import LLM
from .memory import Memory
from .planner import Planner
from .self_improve import SelfImprover


def _build_agent(repo: Path | None) -> Agent:
    cfg = Config.from_env()
    if repo is not None:
        cfg.repo_root = str(repo.resolve())
    llm = LLM(url=cfg.ollama_url, model=cfg.ollama_model, timeout=cfg.llm_timeout)
    memory = Memory(cfg.memory_dir)
    planner = Planner(llm)
    return Agent(cfg=cfg, llm=llm, memory=memory, planner=planner)


def cmd_run(args: argparse.Namespace) -> int:
    agent = _build_agent(Path(args.repo) if args.repo else Path.cwd())
    result = agent.run(args.task)
    print(json.dumps(result.to_dict(), indent=2))
    return 0 if result.ok else 1


def cmd_plan(args: argparse.Namespace) -> int:
    from .planner import Planner as P
    cfg = Config.from_env()
    llm = LLM(url=cfg.ollama_url, model=cfg.ollama_model, timeout=cfg.llm_timeout)
    p = P(llm)
    steps = p.plan(args.task)
    for s in steps:
        print(f"[{s.id:>2}] {s.action:<8} {s.description}")
    return 0


def cmd_self_improve(args: argparse.Namespace) -> int:
    agent = _build_agent(Path(args.repo) if args.repo else Path.cwd())
    si = SelfImprover(agent)
    result = si.propose_and_apply(args.goal)
    print(json.dumps(result.to_dict(), indent=2))
    return 0 if result.ok else 1


def cmd_doctor(args: argparse.Namespace) -> int:
    """Sanity check the runtime: python, git, ollama, model availability."""
    import shutil
    import subprocess
    import urllib.request

    out: dict = {"python": sys.version.split()[0], "git": None, "ollama": None, "models": []}

    git = shutil.which("git")
    if git:
        try:
            v = subprocess.check_output([git, "--version"], text=True, timeout=5).strip()
            out["git"] = v
        except Exception as e:
            out["git"] = f"error: {e}"

    cfg = Config.from_env()
    try:
        req = urllib.request.urlopen(cfg.ollama_url + "/api/tags", timeout=2)
        if req.status == 200:
            data = json.loads(req.read().decode("utf-8"))
            out["ollama"] = "reachable"
            out["models"] = [m["name"] for m in data.get("models", [])]
    except Exception as e:
        out["ollama"] = f"unreachable: {e.__class__.__name__}"

    print(json.dumps(out, indent=2))
    ok = bool(out["git"]) and out["python"] >= "3"
    return 0 if ok else 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="dogfood", description="Self-contained self-improving agent MVP.")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="Plan and execute a one-shot task in the repo.")
    r.add_argument("task", help="Natural-language task description.")
    r.add_argument("--repo", help="Repo root (defaults to cwd).")
    r.set_defaults(func=cmd_run)

    pl = sub.add_parser("plan", help="Show the plan for a task without executing it.")
    pl.add_argument("task")
    pl.set_defaults(func=cmd_plan)

    si = sub.add_parser("self-improve", help="Agent reads itself, proposes a tiny safe change, tests, commits or rolls back.")
    si.add_argument("--goal", default="Improve one small thing in this repo. Pick the smallest, safest, most boring improvement you can find.")
    si.add_argument("--repo", help="Repo root (defaults to cwd).")
    si.set_defaults(func=cmd_self_improve)

    d = sub.add_parser("doctor", help="Check python/git/ollama availability.")
    d.set_defaults(func=cmd_doctor)

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())