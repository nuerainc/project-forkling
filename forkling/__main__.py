"""CLI entry: ``python -m forkling <command> ...``"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .agent import Agent
from .capability import CapabilityLedger
from .config import Config
from .diary import Diary
from .evolution import Evolution
from .graveyard import Graveyard
from .grants import ProjectProfile, draft as draft_grant, match as match_grants
from .llm import LLM
from .memory import Memory
from .planner import Planner
from .replay import diff_replays, lineage as replay_lineage, replay as do_replay
from .self_improve import SelfImprover


def _build_agent(repo: Path | None, cfg: Config | None = None) -> Agent:
    cfg = cfg or Config.from_env()
    if repo is not None:
        cfg.repo_root = str(repo.resolve())
    llm = LLM(url=cfg.ollama_url, model=cfg.ollama_model, timeout=cfg.llm_timeout)
    memory = Memory(cfg.memory_dir)
    planner = Planner(llm, graveyard=Graveyard(Path(cfg.memory_dir) / "graveyard.jsonl"))
    return Agent(cfg=cfg, llm=llm, memory=memory, planner=planner)


def cmd_run(args: argparse.Namespace) -> int:
    agent = _build_agent(Path(args.repo) if args.repo else None)
    result = agent.run(args.task)
    agent.diary.write("run.done", f"task ok={result.ok} steps={len(result.steps)}",
                      task=args.task[:200])
    print(json.dumps(result.to_dict(), indent=2))
    return 0 if result.ok else 1


def cmd_plan(args: argparse.Namespace) -> int:
    cfg = Config.from_env()
    llm = LLM(url=cfg.ollama_url, model=cfg.ollama_model, timeout=cfg.llm_timeout)
    p = Planner(llm)
    steps = p.plan(args.task)
    for s in steps:
        print(f"[{s.id:>2}] {s.action:<8} {s.description}")
    return 0


def cmd_self_improve(args: argparse.Namespace) -> int:
    agent = _build_agent(Path(args.repo) if args.repo else None)
    si = SelfImprover(agent)
    result = si.propose_and_apply(args.goal)
    print(json.dumps(result.to_dict(), indent=2))
    return 0 if result.ok else 1


def cmd_doctor(args: argparse.Namespace) -> int:
    """Sanity check the runtime: python, git, ollama, model availability."""
    import shutil
    import subprocess
    import urllib.request

    out: dict = {"python": sys.version.split()[0], "git": None,
                 "ollama": None, "models": [], "sovereign": Config.from_env().sovereign}

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


def cmd_replay(args: argparse.Namespace) -> int:
    result = do_replay(args.sha, args.task, cwd=args.repo or ".")
    print(json.dumps(result.to_dict(), indent=2))
    return 0


def cmd_diff_replays(args: argparse.Namespace) -> int:
    result = diff_replays(args.sha_a, args.sha_b, args.task, cwd=args.repo or ".")
    print(json.dumps(result, indent=2))
    return 0


def cmd_lineage(args: argparse.Namespace) -> int:
    shas = replay_lineage(args.sha_start, args.sha_end, cwd=args.repo or ".")
    for s in shas:
        print(s)
    return 0


def cmd_grants(args: argparse.Namespace) -> int:
    profile = ProjectProfile()
    ranked = match_grants(profile)
    if args.action == "list":
        for g in ranked:
            print(f"{g['_fit']:.2f}  {g['name']:<30} {g.get('typical_amount', '')}  {g.get('url', '')}")
    elif args.action == "draft":
        if args.which is None:
            print("usage: forkling grants draft <index>", file=sys.stderr)
            return 1
        g = ranked[args.which]
        print(draft_grant(g, profile))
    return 0


def cmd_diary(args: argparse.Namespace) -> int:
    cfg = Config.from_env()
    diary = Diary(Path(cfg.memory_dir) / "diary.jsonl")
    if args.action == "tail":
        print(diary.summarize_recent(args.n))
    elif args.action == "milestones":
        for e in diary.milestones():
            import time
            ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(e.get("ts", 0)))
            print(f"[{ts}] {e.get('content', '')}")
    elif args.action == "stats":
        print(json.dumps(diary.stats(), indent=2))
    return 0


def cmd_fitness(args: argparse.Namespace) -> int:
    cfg = Config.from_env()
    repo = Path(args.repo).resolve() if args.repo else Path(cfg.repo_root).resolve()
    evo = Evolution(
        CapabilityLedger(Path(cfg.memory_dir) / "capabilities.jsonl"),
        Graveyard(Path(cfg.memory_dir) / "graveyard.jsonl"),
        repo,
    )
    print(json.dumps(evo.fitness().as_dict(), indent=2))
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    cfg = Config.from_env()
    ledger = CapabilityLedger(Path(cfg.memory_dir) / "capabilities.jsonl")
    ok, msg = ledger.verify()
    print(json.dumps({"ok": ok, "message": msg, "entries": len(ledger.entries())}, indent=2))
    return 0 if ok else 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="forkling", description="Self-contained self-improving agent MVP.")
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

    rp = sub.add_parser("replay", help="Phylogenetic replay: run an ancestor version of forkling on a task.")
    rp.add_argument("sha", help="Ancestor commit SHA (first 7 chars work).")
    rp.add_argument("task", help="Natural-language task.")
    rp.add_argument("--repo", help="Repo root.")
    rp.set_defaults(func=cmd_replay)

    drp = sub.add_parser("diff-replays", help="Run the same task on two ancestors and diff the results.")
    drp.add_argument("sha_a")
    drp.add_argument("sha_b")
    drp.add_argument("task")
    drp.add_argument("--repo")
    drp.set_defaults(func=cmd_diff_replays)

    lin = sub.add_parser("lineage", help="List the SHAs on the path between two commits (chronological).")
    lin.add_argument("sha_start")
    lin.add_argument("sha_end")
    lin.add_argument("--repo")
    lin.set_defaults(func=cmd_lineage)

    g = sub.add_parser("grants", help="Grant hunter: list matches or draft a tailored proposal.")
    gsub = g.add_subparsers(dest="action", required=True)
    glist = gsub.add_parser("list", help="Rank grant programs by fit.")
    glist.set_defaults(func=cmd_grants)
    gdrf = gsub.add_parser("draft", help="Draft a tailored proposal for the Nth-ranked grant (0-indexed).")
    gdrf.add_argument("which", type=int, nargs="?", default=0)
    gdrf.set_defaults(func=cmd_grants)

    dr = sub.add_parser("diary", help="Read forkling's diary (memory of its youth).")
    drsub = dr.add_subparsers(dest="action", required=True)
    drsub.add_parser("tail", help="Show the last N entries.").add_argument("n", type=int, nargs="?", default=20)
    drsub.add_parser("milestones", help="Show only milestone entries.")
    drsub.add_parser("stats", help="Show diary stats.")
    dr.set_defaults(func=cmd_diary)

    f = sub.add_parser("fitness", help="Compute current smartness + skill fitness from the capability ledger.")
    f.add_argument("--repo")
    f.set_defaults(func=cmd_fitness)

    v = sub.add_parser("verify", help="Verify the capability ledger's SHA-256 chain.")
    v.set_defaults(func=cmd_verify)

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.cmd == "diary" and args.action == "tail":
        # Re-parse to capture the optional positional n.
        pass
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())