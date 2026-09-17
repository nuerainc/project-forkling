"""Planner: turn a natural-language task into an ordered list of steps.

A step is a dict::

    {"id": int, "action": str, "args": dict, "description": str}

The agent then executes each step in order, using the matching tool in
:mod:`forkling.tools`.

Strategy:

* Ask the LLM for a JSON plan. The prompt constrains the schema.
* If the LLM is unavailable or returns unparseable JSON, fall back to a
  deterministic rule-based planner that recognises a handful of common
  intent verbs ("add", "fix", "list", "test", "improve", …).
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Any

from .llm import LLM

if TYPE_CHECKING:
    from .diary import Diary
    from .graveyard import Graveyard
    from .inception import Inception
    from pathlib import Path


SYSTEM_PROMPT = """You are the planner of dogfood, a self-contained coding agent.
Given a task, output ONLY valid JSON matching this schema:
{"steps": [{"action": str, "args": object, "description": str}]}

Valid actions:
  read   -> {"path": "rel/path"}
  write  -> {"path": "rel/path", "content": "..."}
  patch  -> {"path": "rel/path", "old": "exact existing substring", "new": "replacement"}
  list   -> {"path": "rel/path"}
  shell  -> {"argv": ["cmd", "arg", ...], "cwd": "optional rel/path", "timeout": int}
  test   -> {}     # run the project's test command
  commit -> {"message": "..."}
  tag    -> {"name": "v0.x.y"}
  finish -> {}

Be minimal. Prefer 1-5 steps. Never invent file contents — for write/patch, only
emit if the task *literally* tells you what to write; otherwise emit a `read`
or `list` step first so the agent can discover state.

Return JSON only. No prose, no fences."""


@dataclass
class Step:
    id: int
    action: str
    args: dict = field(default_factory=dict)
    description: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


class Planner:
    def __init__(self, llm: LLM, graveyard: "Graveyard | None" = None,
                 diary: "Diary | None" = None,
                 inception: "Inception | None" = None,
                 repo_root: "Path | str | None" = None) -> None:
        self.llm = llm
        self.graveyard = graveyard
        self.diary = diary
        # If we get a path, lazily build an Inception handle. If we get
        # an Inception instance directly, use it. If we get None and we
        # have a repo_root, default to no inception (baseline).
        if inception is None and repo_root is not None:
            from .inception import Inception
            inception = Inception(repo_root)
        self.inception = inception

    def plan(self, task: str) -> list[Step]:
        # Note: inception triggers are NOT injected into the prompt.
        # They land mid-flight via the heartbeat's process_all() phase
        # (see forkling/__main__.py::cmd_heartbeat). That is the
        # interruptive path — the agent's current work stops, the
        # trigger is force-acknowledged, and the agent resumes.
        # The planner is left clean.
        prompt_parts: list[str] = [task]
        if self.graveyard is not None:
            gh = self.graveyard.as_prompt_excerpt(n=5)
            if gh:
                prompt_parts.append(gh)
        prompt = "\n\n".join(prompt_parts)
        completion = self.llm.complete(prompt=prompt, system=SYSTEM_PROMPT)
        steps = self._parse_llm_json(completion.text) if completion.used_llm else []
        if not steps:
            steps = self._rule_based(task)
        return self._renumber(steps)

    # ---- LLM JSON path -----------------------------------------------------

    @staticmethod
    def _parse_llm_json(text: str) -> list[Step]:
        # Strip fences / leading prose; the system prompt forbids them but be defensive.
        text = text.strip()
        text = re.sub(r"^```(?:json)?", "", text).strip()
        text = re.sub(r"```$", "", text).strip()
        try:
            obj = json.loads(text)
        except json.JSONDecodeError:
            return []
        raw = obj.get("steps") if isinstance(obj, dict) else obj
        if not isinstance(raw, list):
            return []
        steps: list[Step] = []
        for entry in raw:
            if not isinstance(entry, dict):
                continue
            steps.append(Step(
                id=0,
                action=str(entry.get("action", "")).strip(),
                args=dict(entry.get("args") or {}),
                description=str(entry.get("description", "")).strip(),
            ))
        return [s for s in steps if s.action]

    # ---- heuristic path ----------------------------------------------------

    @staticmethod
    def _rule_based(task: str) -> list[Step]:
        t = task.strip()
        low = t.lower()

        def step(action: str, args: dict, description: str) -> Step:
            return Step(id=0, action=action, args=args, description=description or action)

        # run tests
        if re.search(r"\b(run|execute)\s+(the\s+)?tests?\b", low) or low in ("test", "tests"):
            return [step("test", {}, "Run the test suite")]

        # list directory
        m = re.search(r"list\s+(?:files\s+in\s+)?([\w./\-]+)", low)
        if m:
            return [step("list", {"path": m.group(1)}, f"List {m.group(1)}")]

        # read file
        m = re.search(r"(?:read|show|cat|open)\s+([\w./\-]+)", low)
        if m:
            return [step("read", {"path": m.group(1)}, f"Read {m.group(1)}")]

        # add docstring to function
        m = re.search(r"add\s+(a\s+)?docstring\s+(?:to\s+)?([\w./\-]+)", low)
        if m:
            return _docstring_plan(m.group(2))

        # improve self / refactor / tidy / clean / format
        if re.search(r"\b(improve|refactor|tidy|clean|format|polish)\b", low):
            return [
                step("list", {"path": "forkling"}, "List the agent package"),
                step("read", {"path": "dogfood/agent.py"}, "Read agent source"),
                step("test", {}, "Baseline: run tests"),
                step("patch", {
                    "path": "dogfood/agent.py",
                    "old": "__TODO_SELF_IMPROVEMENT_PATCH__",
                    "new": "# improved by dogfood\n",
                }, "Apply self-improvement patch"),
                step("test", {}, "Verify tests still pass"),
                step("commit", {"message": "dogfood: self-improve"}, "Commit if green"),
            ]

        # generic "fix / add / change / modify / edit / update"
        m = re.search(r"(?:fix|add|change|modify|edit|update|implement)\b.*?(?:in|to|of|for)\s+([\w./\-]+)", low)
        if m:
            target = m.group(1)
            return [
                step("read", {"path": target}, f"Read {target}"),
                step("patch", {
                    "path": target,
                    "old": "__TODO_GENERIC_PATCH__",
                    "new": f"# dogfood: handled '{t[:60]}'\n",
                }, f"Edit {target}"),
                step("test", {}, "Run tests"),
                step("commit", {"message": f"dogfood: {t[:60]}"}, "Commit"),
            ]

        # shell fallback: shell out
        return [step("shell", {"argv": ["echo", f"dogfood: unknown task -> {t[:80]}"]},
                     "Echo unknown task")]

    @staticmethod
    def _renumber(steps: list[Step]) -> list[Step]:
        for i, s in enumerate(steps, start=1):
            s.id = i
        return steps


def _docstring_plan(path: str) -> list[Step]:
    """Heuristic for "add a docstring to <path>"."""
    return [
        Step(0, "read", {"path": path}, f"Read {path}"),
        Step(0, "patch", {
            "path": path,
            "old": "__TODO_DOCSTRING_PATCH__",
            "new": '"""Documented by dogfood."""\n',
        }, "Insert docstring"),
        Step(0, "test", {}, "Run tests"),
        Step(0, "commit", {"message": f"dogfood: add docstring to {path}"}, "Commit"),
    ]