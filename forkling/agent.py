"""The agent: Plan → Act → Reflect, with auto-rollback on failure.

This module is the orchestrator. It does not call the LLM directly — it asks
the :class:`Planner` for steps, then walks them one by one. Each step's outcome
is appended to a structured log that becomes the :class:`Result` returned to
the caller.
"""

from __future__ import annotations

import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .capability import CapabilityLedger
from .config import Config
from .diary import Diary
from .graveyard import Graveyard
from .llm import LLM
from .memory import Memory
from .planner import Planner, Step
from . import tools


@dataclass
class StepRecord:
    id: int
    action: str
    description: str
    ok: bool
    output: str = ""
    error: str = ""


@dataclass
class Result:
    task: str
    ok: bool
    steps: list[StepRecord] = field(default_factory=list)
    final_sha: str = ""
    used_llm: bool = False
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "task": self.task,
            "ok": self.ok,
            "used_llm": self.used_llm,
            "final_sha": self.final_sha,
            "note": self.note,
            "steps": [
                {
                    "id": s.id, "action": s.action, "description": s.description,
                    "ok": s.ok, "output": s.output, "error": s.error,
                }
                for s in self.steps
            ],
        }


class Agent:
    def __init__(self, cfg: Config, llm: LLM, memory: Memory, planner: Planner,
                 ledger: CapabilityLedger | None = None,
                 graveyard: Graveyard | None = None,
                 diary: Diary | None = None) -> None:
        self.cfg = cfg
        self.llm = llm
        self.memory = memory
        self.planner = planner
        # New: capability ledger, graveyard, diary. Auto-created if not passed.
        state_dir = Path(cfg.memory_dir)
        self.ledger = ledger or CapabilityLedger(state_dir / "capabilities.jsonl")
        self.graveyard = graveyard or Graveyard(state_dir / "graveyard.jsonl")
        self.diary = diary or Diary(state_dir / "diary.jsonl")
        self.root = Path(cfg.repo_root).resolve()
        self.diary.write("boot", f"forkling booted in {self.root}", repo=str(self.root))

    # ---- public ------------------------------------------------------------

    def run(self, task: str) -> Result:
        self.memory.log("run.start", task=task[:200])
        self.diary.write("run.start", task[:300], ts_kind="run")
        steps = self._plan(task)
        result = Result(task=task, ok=True, used_llm=bool(steps and self._last_plan_used_llm))

        # Snapshot sha before any work, so we can roll back at the end if needed.
        try:
            pre_sha = tools.git_current_sha(self.root)
        except tools.ToolError:
            pre_sha = ""

        # Execute the plan, step by step.
        for step in steps:
            rec = self._execute(step)
            result.steps.append(rec)
            self.ledger.record(action=step.action, target=str(step.args.get("path", "")),
                               ok=rec.ok, agent_sha=pre_sha)
            if not rec.ok and step.action != "finish":
                # Record failure in graveyard so future prompts can avoid it.
                self.graveyard.record(
                    path=str(step.args.get("path", "")),
                    old=str(step.args.get("old", "")),
                    new=str(step.args.get("new", "")),
                    reason=rec.error[:500],
                    source=self._last_plan_used_llm and "llm" or "rule-based",
                )
                self.diary.write("step.failed",
                                 f"{step.action}: {rec.error[:200]}",
                                 step_id=step.id)
                if step.action == "test":
                    result.note = "test failed; will roll back if a self-change was attempted"
                if step.action in {"patch", "write"} and pre_sha:
                    self.memory.log("rollback.start", reason=rec.error, sha=pre_sha)
                    self.diary.write("rollback.start", f"reverting to {pre_sha[:7]}", sha=pre_sha)
                    rb = tools.git_checkout(pre_sha, cwd=self.root)
                    if rb.ok:
                        result.steps.append(self._record_rollback(step.id + 1, rb, pre_sha))
                        self.diary.write("rollback.done", f"reverted to {pre_sha[:7]}")
                    else:
                        result.steps.append(self._record_rollback(step.id + 1, rb, pre_sha,
                                                                   note=f"checkout failed: {rb.stderr}"))
                        self.diary.write("rollback.failed", rb.stderr[:200])
                result.ok = False
                break

        # Always try to record final sha for traceability.
        try:
            result.final_sha = tools.git_current_sha(self.root)
        except tools.ToolError:
            pass

        self.memory.record_run(task, result.ok, result.final_sha, len(result.steps))
        self.memory.log("run.end", ok=result.ok, steps=len(result.steps))
        return result

    # ---- internals ---------------------------------------------------------

    _last_plan_used_llm: bool = False

    def _plan(self, task: str) -> list[Step]:
        # The planner always uses the LLM, with rule-based fallback inside .complete().
        # We approximate `used_llm` by re-asking once to peek — cheap, and the
        # result is also useful for the caller.
        peek = self.llm.complete(prompt=task[:200], system=None,
                                  kind="plan.peek", task=task[:500])
        Agent._last_plan_used_llm = peek.used_llm
        return self.planner.plan(task)

    def _execute(self, step: Step) -> StepRecord:
        rec = StepRecord(id=step.id, action=step.action, description=step.description, ok=True)
        try:
            out = self._dispatch(step)
            rec.output = out if isinstance(out, str) else str(out)
        except tools.ToolError as e:
            rec.ok = False
            rec.error = str(e)
        except Exception as e:  # last-resort safety net
            rec.ok = False
            rec.error = f"{e.__class__.__name__}: {e}\n{traceback.format_exc(limit=2)}"
        return rec

    def _dispatch(self, step: Step) -> str:
        a = step.action
        args = step.args or {}
        if a == "read":
            return tools.read_file(self._safe(args["path"]))
        if a == "write":
            tools.write_file(self._safe(args["path"]), str(args.get("content", "")))
            return f"wrote {args['path']} ({len(args.get('content', ''))} bytes)"
        if a == "patch":
            tools.apply_patch(self._safe(args["path"]), str(args["old"]), str(args["new"]))
            return f"patched {args['path']}"
        if a == "list":
            return "\n".join(tools.list_dir(self._safe(args["path"])))
        if a == "shell":
            argv = list(args.get("argv") or [])
            if not argv:
                raise tools.ToolError("shell step needs argv")
            cwd = args.get("cwd")
            timeout = int(args.get("timeout", 60))
            res = tools.run_shell(argv, cwd=self._safe(cwd) if cwd else self.root, timeout=timeout)
            return f"exit={res.returncode}\nstdout: {res.stdout[:4000]}\nstderr: {res.stderr[:2000]}"
        if a == "test":
            cmd = self.cfg.test_command.split()
            res = tools.run_shell(cmd, cwd=self.root, timeout=600)
            ok = res.ok
            snippet = (res.stdout + res.stderr)[-2000:]
            if not ok:
                raise tools.ToolError(f"tests failed:\n{snippet}")
            return f"exit={res.returncode}\n{snippet}"
        if a == "commit":
            res = tools.git_commit(str(args.get("message", "dogfood: change")), cwd=self.root)
            if not res.ok:
                raise tools.ToolError(f"commit failed: {res.stderr or res.stdout}")
            return res.stdout.strip() or "committed"
        if a == "tag":
            res = tools.git_tag(str(args["name"]), cwd=self.root)
            if not res.ok:
                raise tools.ToolError(f"tag failed: {res.stderr or res.stdout}")
            return f"tagged {args['name']}"
        if a == "rollback":
            sha = str(args["sha"])
            res = tools.git_checkout(sha, cwd=self.root)
            if not res.ok:
                raise tools.ToolError(f"checkout failed: {res.stderr}")
            return f"checked out {sha}"
        if a == "finish":
            return "finished"
        raise tools.ToolError(f"unknown action: {a}")

    def _record_rollback(self, step_id: int, rb: tools.ShellResult, sha: str,
                         note: str = "") -> StepRecord:
        ok = rb.ok
        return StepRecord(
            id=step_id, action="rollback",
            description=f"git checkout {sha[:7]}",
            ok=ok,
            output=f"exit={rb.returncode}",
            error="" if ok else (note or rb.stderr or rb.stdout),
        )

    def _safe(self, rel: str) -> Path:
        return tools.safe_path(self.root, rel)