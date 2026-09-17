"""CLI entry: ``python -m forkling <command> ...``"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .agent import Agent
from .ancestor import Ancestry, PRECURSOR, Generation
from .capability import CapabilityLedger
from .config import Config
from .diary import Diary
from .evolution import Evolution
from .family import Family
from .graveyard import Graveyard
from .grants import ProjectProfile, draft as draft_grant, match as match_grants
from .inception import Inception, MIN_WORDS, _word_count
from .llm import LLM
from .memory import Memory
from .paper import render as render_paper, update as update_paper, append_status as append_paper_status
from .planner import Planner
from .replay import diff_replays, lineage as replay_lineage, replay as do_replay
from .self_improve import SelfImprover
from . import tools


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
            ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(e.get("ts", 0)))
            print(f"[{ts}] {e.get('content', '')}")
    elif args.action == "stats":
        print(json.dumps(diary.stats(), indent=2))
    elif args.action == "seeds":
        for e in diary.seeds(args.n):
            ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(e.get("ts", 0)))
            print(f"[{ts}] {e.get('content', '')}")
    elif args.action == "seed":
        # Plant a thought (inception). Optional --from records the seeder.
        thought = " ".join(args.thought)
        diary.write("seed", thought, source=getattr(args, "source", "human"))
        print(f"seeded: {thought}")
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


def cmd_schedule(args: argparse.Namespace) -> int:
    """Print drop-in scheduler commands (Windows Task Scheduler / cron)."""
    cfg = Config.from_env()
    repo = Path(args.repo).resolve() if args.repo else Path(cfg.repo_root).resolve()
    script = repo / "scripts" / "heartbeat.py"
    every = getattr(args, "every", 30)  # minutes
    python = Path(sys.executable)

    if sys.platform == "win32":
        # PowerShell snippet.
        ps = f"""# Run as Administrator in PowerShell
$action = New-ScheduledTaskAction -Execute "{python}" -Argument '"{script}" --repo "{repo}"'
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes {every})
Register-ScheduledTask -TaskName "forkland-heartbeat" -Action $action -Trigger $trigger -Description "forkland self-evolution ({every}-min cadence)"
"""
        print(ps)
    else:
        cron_line = (
            f"*/{every} * * * * cd {repo} && {python} {script} --repo {repo} "
            f">> {repo}/.forkling/heartbeat.log 2>&1"
        )
        print("# Add to your crontab with: crontab -e")
        print(cron_line)

    print(f"\n# cadence: every {every} minutes")
    print(f"# repo: {repo}")
    print(f"# script: {script}")
    return 0


def cmd_ancestor(args: argparse.Namespace) -> int:
    """Show forkland's lineage — precursor (Mavis) + code generations."""
    cfg = Config.from_env()
    repo = Path(args.repo).resolve() if getattr(args, "repo", None) else Path(cfg.repo_root).resolve()
    ancestry = Ancestry(Path(cfg.memory_dir) / "ancestry.json", repo=repo)

    if args.action == "list":
        # Rebuild from git so we always show the current state.
        for g in ancestry.rebuild_from_git():
            tag = "precursor" if g.kind == "precursor" else g.identifier[:7]
            ts = time.strftime("%Y-%m-%d", time.localtime(g.timestamp))
            print(f"gen {g.generation:>3}  [{g.kind:<9}] {tag:<10} {ts}  {g.summary}")
        return 0

    if args.action == "summary":
        # Persist the rebuild so `summary` shows up in diary stats too.
        ls = ancestry.rebuild_from_git()
        for g in ls:
            ancestry.append(g)  # idempotent append: ok if duplicates, otherwise noop
        print(ancestry.summary())
        return 0

    if args.action == "precursor":
        print(json.dumps(PRECURSOR, indent=2))
        return 0

    if args.action == "consult":
        # Ask the local LLM "how would the precursor have done this?"
        # with a system prompt that declares Mavis as the precursor.
        sys_prompt = (
            "You are Mavis, a foundation-model agent running in MiniMax Code. "
            "You are the precursor to forkland — you wrote its first version. "
            "Answer the user's task in the spirit of how you would have "
            "approached it before forkland existed. Be direct, research-flavored, "
            "and include one concrete suggestion."
        )
        llm = LLM(url=cfg.ollama_url, model=cfg.ollama_model, timeout=cfg.llm_timeout)
        completion = llm.complete(prompt=args.task, system=sys_prompt)
        print(f"[via {'ollama/' + completion.model if completion.used_llm else 'rule-based'}]")
        print(completion.text)
        return 0

    return 1


def cmd_inception(args: argparse.Namespace) -> int:
    """Inception triggers: ambient intrusive thoughts for the agent."""
    cfg = Config.from_env()
    repo = Path(args.repo).resolve() if getattr(args, "repo", None) else Path(cfg.repo_root).resolve()
    inc = Inception(repo)

    if args.action == "list":
        if not inc.exists():
            print(f"(no inception_triggers/ folder at {repo})")
            return 0
        for t in inc.list():
            tags = ",".join(t.tags) if t.tags else "-"
            wc = _word_count(t.thought)
            print(f"{t.id:<12} [{tags}] {wc} words  by={t.planted_by}")
            print(f"  tag: {t.git_tag or '(none)'}")
            print(f"  file: {t.source_file}")
        return 0

    if args.action == "plant":
        thought = args.thought if isinstance(args.thought, str) else " ".join(args.thought)
        try:
            t = inc.plant(
                thought,
                tags=args.tags,
                planted_by=getattr(args, "planted_by", "human"),
                tag_with_git=not getattr(args, "no_tag", False),
            )
        except ValueError as e:
            print(f"FAIL: {e}", file=sys.stderr)
            return 1
        print(f"OK planted {t.id} ({_word_count(t.thought)} words) at {t.source_file}")
        if t.git_tag:
            print(f"  tagged {t.git_tag}")
        return 0

    if args.action == "validate":
        path = Path(args.file)
        if not path.is_file():
            print(f"not a file: {path}", file=sys.stderr)
            return 1
        try:
            obj = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"✗ invalid JSON: {e}", file=sys.stderr)
            return 1
        ok, msg = inc.validate(obj)
        if ok:
            wc = _word_count(obj.get("thought", ""))
            print(f"✓ valid ({wc} words)")
            return 0
        print(f"✗ {msg}", file=sys.stderr)
        return 1

    if args.action == "remove":
        if inc.remove(args.id):
            print(f"removed {args.id}")
            return 0
        print(f"no such trigger: {args.id}", file=sys.stderr)
        return 1

    if args.action == "show":
        # Dump the ambient block (what the agent sees in its prompt).
        print(inc.ambient_block())
        return 0

    if args.action == "stage":
        if inc.stage(args.id):
            print(f"staged {args.id}")
            return 0
        print(f"no such pending trigger: {args.id}", file=sys.stderr)
        return 1

    if args.action == "unstage":
        if inc.unstage(args.id):
            print(f"unstaged {args.id}")
            return 0
        print(f"no such staged trigger: {args.id}", file=sys.stderr)
        return 1

    if args.action == "staged":
        for t in inc.staged():
            tags = ",".join(t.tags) if t.tags else "-"
            print(f"{t.id:<12} [{tags}] {t.planted_by}")
        return 0

    return 1


def cmd_family(args: argparse.Namespace) -> int:
    cfg = Config.from_env()
    fam = Family(Path(cfg.memory_dir) / "family.json")
    if args.action == "list":
        for m in fam.refresh():
            seen = m.last_seen_sha[:7] if m.last_seen_sha else "?"
            ts = time.strftime("%Y-%m-%d %H:%M", time.localtime(m.last_seen_ts)) if m.last_seen_ts else "never"
            print(f"{m.name:<14} {m.repo}")
            print(f"  branch={m.branch:<8} head={seen}  last_seen={ts}")
            if m.note:
                print(f"  note: {m.note}")
        return 0
    if args.action == "register":
        m = fam.register(name=args.name, repo=args.repo,
                         branch=getattr(args, "branch", "main"),
                         note=getattr(args, "note", ""))
        print(f"registered {m.name} -> {m.repo}")
        return 0
    if args.action == "remove":
        if fam.remove(args.name):
            print(f"removed {args.name}")
            return 0
        print(f"no such member: {args.name}", file=sys.stderr)
        return 1
    if args.action == "sync":
        target = fam.sync_ledger(args.peer)
        if target:
            print(f"copied {args.peer}'s ledger -> {target}")
            return 0
        print(f"could not sync with {args.peer} (peer unknown or ledger missing)",
              file=sys.stderr)
        return 1
    return 1


def cmd_paper(args: argparse.Namespace) -> int:
    cfg = Config.from_env()
    paper_path = getattr(args, "path", None) or "paper/paper.md"
    if args.action == "render":
        print(render_paper(cfg.memory_dir))
        return 0
    if args.action == "update":
        out = update_paper(cfg.memory_dir, paper_path)
        print(f"wrote {out}")
        return 0
    if args.action == "append":
        out = append_paper_status(cfg.memory_dir, paper_path)
        print(f"appended status to {out}")
        return 0
    return 1


def cmd_heartbeat(args: argparse.Namespace) -> int:
    """Run one heartbeat: self-improve + paper update + grants list + diary rollup.

    Designed to be invoked on a schedule (cron / Task Scheduler / Mavis cron).
    Zero MiniMax dependency — runs entirely on the local machine.
    Acquires a per-repo lock so concurrent heartbeats don't race.
    """
    from .locking import HeartbeatLock, LockBusy
    cfg = Config.from_env()
    repo = Path(args.repo).resolve() if args.repo else Path(cfg.repo_root).resolve()
    log_path = repo / ".forkling" / "heartbeat.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        lock = HeartbeatLock(repo)
        lock.acquire()
    except LockBusy as e:
        out = {"ran_at": time.time(), "skipped": str(e), "steps": []}
        with log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(out) + "\n")
        print(json.dumps(out, indent=2))
        return 1

    try:
        steps = []
        # Refuse to run on detached HEAD (would orphan any commit).
        try:
            if tools.git_is_detached(repo):
                out = {"ran_at": time.time(), "skipped": "HEAD is detached",
                       "steps": []}
                with log_path.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(out) + "\n")
                print(json.dumps(out, indent=2))
                return 1
        except tools.ToolError:
            pass

        # Phase 0: HARD STOP for any pending inception triggers.
        # The agent's current work pauses. Each trigger is force-
        # acknowledged (response generated, logged to diary) before
        # the heartbeat proceeds. This is the "dead-center" interrupt
        # the user wanted — the second a trigger lands, it triggers.
        cfg = Config.from_env()
        inc = Inception(repo)
        diary = Diary(Path(cfg.memory_dir) / "diary.jsonl")
        llm = LLM(url=cfg.ollama_url, model=cfg.ollama_model, timeout=cfg.llm_timeout)
        pending = inc.pending_count()
        triggered_responses: list[dict] = []
        if pending > 0:
            diary.write("inception.interrupt",
                        f"hard stop: {pending} trigger(s) found",
                        count=pending)
            triggered_responses = inc.process_all(llm, diary=diary)
            diary.write("inception.recovered",
                        f"processed {len(triggered_responses)} trigger(s); resuming work",
                        count=len(triggered_responses))
            steps.append(("inception.processed",
                          0,
                          f"{len(triggered_responses)} acknowledged; "
                          f"dairy 'inception.recovered' logged"))

        import subprocess
        # 1. Self-improve (the actual evolution step).
        if not args.skip_improve:
            r = subprocess.run(
                ["python", "-m", "forkling", "self-improve", "--repo", str(repo)],
                cwd=repo, capture_output=True, text=True, timeout=900,
            )
            steps.append(("self-improve", r.returncode, (r.stdout + r.stderr)[-300:]))
        # 2. Append a paper status block.
        r = subprocess.run(
            ["python", "-m", "forkling", "paper", "append"],
            cwd=repo, capture_output=True, text=True, timeout=60,
        )
        steps.append(("paper.append", r.returncode, (r.stdout + r.stderr)[-200:]))
        # 3. Verify the ledger.
        r = subprocess.run(
            ["python", "-m", "forkling", "verify"],
            cwd=repo, capture_output=True, text=True, timeout=30,
        )
        steps.append(("verify", r.returncode, (r.stdout + r.stderr)[-200:]))

        out = {
            "ran_at": time.time(),
            "inception_triggered": triggered_responses,
            "steps": [{"name": n, "ok": c == 0, "tail": t} for n, c, t in steps],
        }
        with log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(out) + "\n")
        print(json.dumps(out, indent=2))
        return 0 if all(c == 0 for _, c, _ in steps) else 1
    finally:
        lock.release()


import time  # for ancestor formatting


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
    drsub.add_parser("seeds", help="Show planted seeds (inception thoughts).").add_argument("n", type=int, nargs="?", default=10)
    ssub = drsub.add_parser("seed", help="Plant a thought the agent will reflect on during planning.")
    ssub.add_argument("thought", nargs="+", help="The thought to plant.")
    ssub.add_argument("--source", default="human", help="Who/what is planting the seed.")
    dr.set_defaults(func=cmd_diary)

    f = sub.add_parser("fitness", help="Compute current smartness + skill fitness from the capability ledger.")
    f.add_argument("--repo")
    f.set_defaults(func=cmd_fitness)

    v = sub.add_parser("verify", help="Verify the capability ledger's SHA-256 chain.")
    v.set_defaults(func=cmd_verify)

    an = sub.add_parser("ancestor", help="Show forkland's lineage (precursor + generations).")
    ansub = an.add_subparsers(dest="action", required=True)
    ansub.add_parser("list", help="List all generations.").add_argument("--repo")
    ansub.add_parser("summary", help="One-line summary per generation.").add_argument("--repo")
    ansub.add_parser("precursor", help="Show the precursor record (Mavis/MiniMax-M3).")
    cns = ansub.add_parser("consult", help="Ask 'how would the precursor have done this?'")
    cns.add_argument("task", help="Natural-language task.")
    an.set_defaults(func=cmd_ancestor)

    fam = sub.add_parser("family", help="Forkland & Family: federated registry of sovereign forks.")
    famsub = fam.add_subparsers(dest="action", required=True)
    famsub.add_parser("list", help="List all family members.")
    freg = famsub.add_parser("register", help="Register a new family member.")
    freg.add_argument("name", help="Name, e.g. 'Forkland' or 'Spoonica'.")
    freg.add_argument("repo", help="Absolute path to the fork's repo.")
    freg.add_argument("--branch", default="main")
    freg.add_argument("--note", default="")
    frm = famsub.add_parser("remove", help="Remove a family member from the registry.")
    frm.add_argument("name")
    fsyn = famsub.add_parser("sync", help="Opt-in: copy a peer's ledger for study (never auto-merge).")
    fsyn.add_argument("peer", help="Name of the family member.")
    fam.set_defaults(func=cmd_family)

    pap = sub.add_parser("paper", help="forkland drafts its own paper sections.")
    papsub = pap.add_subparsers(dest="action", required=True)
    papsub.add_parser("render", help="Render the full paper to stdout.")
    papup = papsub.add_parser("update", help="Render and write paper/paper.md.")
    papup.add_argument("--path", default=None)
    papap = papsub.add_parser("append", help="Append a status block to the paper.")
    papap.add_argument("--path", default=None)
    pap.set_defaults(func=cmd_paper)

    hb = sub.add_parser("heartbeat", help="One autonomous beat: self-improve + paper update + verify.")
    hb.add_argument("--repo", help="Repo root (defaults to cwd).")
    hb.add_argument("--skip-improve", action="store_true",
                    help="Skip the self-improve step (useful for tests).")
    hb.set_defaults(func=cmd_heartbeat)

    sch = sub.add_parser("schedule", help="Print drop-in scheduler commands for this OS.")
    sch.add_argument("--repo", help="Repo root.")
    sch.add_argument("--every", type=int, default=30, help="Cadence in minutes.")
    sch.set_defaults(func=cmd_schedule)

    inc = sub.add_parser("inception", help="Inception triggers — ambient intrusive thoughts.")
    incsub = inc.add_subparsers(dest="action", required=True)
    incsub.add_parser("list", help="List all triggers in inception_triggers/.").add_argument("--repo")
    ipl = incsub.add_parser("plant", help="Plant a new trigger (must be >= 50 words).")
    ipl.add_argument("thought", nargs="+", help="The thought (>= 50 words).")
    ipl.add_argument("--tags", nargs="*", default=[], help="Tags for organization.")
    ipl.add_argument("--planted-by", default="human")
    ipl.add_argument("--no-tag", action="store_true", help="Skip creating a git tag.")
    ipl.add_argument("--repo")
    ival = incsub.add_parser("validate", help="Validate a trigger JSON file.")
    ival.add_argument("file", help="Path to trigger JSON file.")
    irm = incsub.add_parser("remove", help="Remove a trigger by id.")
    irm.add_argument("id", help="Trigger id, e.g. 'trg-001'.")
    incsub.add_parser("show", help="Print the ambient block the agent sees (no label).").add_argument("--repo")
    isg = incsub.add_parser("stage", help="Move a trigger to staging/ so the agent won't see it.")
    isg.add_argument("id")
    ius = incsub.add_parser("unstage", help="Move a staged trigger back into the active folder.")
    ius.add_argument("id")
    incsub.add_parser("staged", help="List staged triggers.")
    inc.set_defaults(func=cmd_inception)

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.cmd == "diary" and args.action == "tail":
        # Re-parse to capture the optional positional n.
        pass
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())