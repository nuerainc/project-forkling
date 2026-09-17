"""Phylogenetic replay — run an ancestor version of the agent.

``python -m forkling replay <old-sha> <task>`` checks out the ancestor
code into a temporary git worktree, runs *that* version of forkling on
the task, and reports the result.

Use cases:

* "Would my grandfather have solved this faster?"
* "Did adding capability X actually help?"
* "How does the plan shape differ across generations?"

Every replay is itself recorded in the capability ledger (action=
"replay"), making the agent's introspection auditable.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path

from . import tools


@dataclass
class ReplayResult:
    ancestor: str
    task: str
    returncode: int = -1
    stdout_tail: str = ""
    stderr_tail: str = ""
    steps_executed: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


def replay(ancestor_sha: str, task: str, *,
           cwd: str | Path = ".", timeout: int = 600) -> ReplayResult:
    """Run an ancestor forkling on a task in a temporary worktree."""
    root = tools.find_repo_root(cwd) or Path(cwd)
    worktree = Path(tempfile.mkdtemp(prefix="forkling-replay-"))
    try:
        subprocess.run(
            ["git", "worktree", "add", "--detach", str(worktree), ancestor_sha],
            cwd=root, check=True, capture_output=True, text=True,
        )
        result = subprocess.run(
            ["python", "-m", "forkling", "run", task],
            cwd=worktree, capture_output=True, text=True, timeout=timeout,
        )
        steps = 0
        try:
            payload = json.loads(result.stdout)
            steps = len(payload.get("steps", []))
        except (json.JSONDecodeError, ValueError):
            pass
        return ReplayResult(
            ancestor=ancestor_sha,
            task=task,
            returncode=result.returncode,
            stdout_tail=result.stdout[-2000:],
            stderr_tail=result.stderr[-2000:],
            steps_executed=steps,
        )
    finally:
        subprocess.run(["git", "worktree", "remove", "--force", str(worktree)],
                       cwd=root, capture_output=True)
        shutil.rmtree(worktree, ignore_errors=True)


def diff_replays(sha_a: str, sha_b: str, task: str, *,
                 cwd: str | Path = ".") -> dict:
    """Run the same task on two ancestors and return both results."""
    a = replay(sha_a, task, cwd=cwd)
    b = replay(sha_b, task, cwd=cwd)
    return {
        "task": task,
        "ancestor_a": a.to_dict(),
        "ancestor_b": b.to_dict(),
        "delta_steps": b.steps_executed - a.steps_executed,
        "delta_returncode": b.returncode - a.returncode,
    }


def lineage(sha_start: str, sha_end: str, *,
            cwd: str | Path = ".") -> list[str]:
    """List the SHAs on the path from sha_start (exclusive) to sha_end (inclusive).

    Uses ``git rev-list`` so it's exact and matches git's idea of ancestry.
    """
    root = tools.find_repo_root(cwd) or Path(cwd)
    out = subprocess.check_output(
        ["git", "rev-list", "--reverse", f"^{sha_start}", sha_end],
        cwd=root, text=True,
    )
    return [s.strip() for s in out.splitlines() if s.strip()]