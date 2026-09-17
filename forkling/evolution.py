"""Multi-objective fitness + A/B evolutionary lineages.

Two axes of fitness:

* **smartness** — patch acceptance rate, plan efficiency, test pass rate.
  Captures *how well* the agent reasons about existing capabilities.
* **skill** — distinct capabilities exercised, file diversity (Shannon
  entropy), action-type diversity. Captures *how broad* the agent's
  reach is.

Together they answer the user's question: "does it get smarter and more
skilled too?"

A/B lineages
------------

The ``Lineage`` primitive lets you spawn N parallel agents in git
worktrees, each with its own environment (env vars) that subtly bias
selection pressure. After K generations, lineages are ranked by fitness
and the winner is fast-forward merged. This is "evolution in
production" with controlled experiments.

Example::

    evo = Evolution(ledger, graveyard, repo_root)
    evo.run_ab(["A: small files only",
                "B: large files only",
                "C: docstrings only"],
               generations=5)
"""

from __future__ import annotations

import math
import os
import shutil
import subprocess
import tempfile
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .capability import CapabilityLedger
from .graveyard import Graveyard


@dataclass
class Fitness:
    smartness: float
    skill: float
    acceptance_rate: float
    test_pass_rate: float
    distinct_actions: int
    file_diversity: float

    @property
    def total(self) -> float:
        return (self.smartness + self.skill) / 2

    def as_dict(self) -> dict[str, float | int]:
        return {
            "smartness": self.smartness,
            "skill": self.skill,
            "total": self.total,
            "acceptance_rate": self.acceptance_rate,
            "test_pass_rate": self.test_pass_rate,
            "distinct_actions": self.distinct_actions,
            "file_diversity": self.file_diversity,
        }


class Evolution:
    """Read-only fitness calculations over the ledger + graveyard."""

    # The 8 known actions the agent can take. Used to normalize action diversity.
    KNOWN_ACTIONS = ("read", "write", "patch", "list", "shell", "test",
                     "commit", "tag", "rollback", "finish")

    def __init__(self, ledger: CapabilityLedger, graveyard: Graveyard,
                 repo_root: Path) -> None:
        self.ledger = ledger
        self.graveyard = graveyard
        self.repo_root = Path(repo_root)

    # ---- fitness -----------------------------------------------------------

    def fitness(self) -> Fitness:
        caps = self.ledger.entries()
        patches = [c for c in caps if c.get("action") in ("patch", "write")]
        tests = [c for c in caps if c.get("action") == "test"]
        # Estimate rejection count from graveyard size.
        graveyard_size = len(self.graveyard.entries())
        acceptance = len(patches) / max(1, len(patches) + graveyard_size)
        test_pass = sum(1 for t in tests if t.get("ok")) / max(1, len(tests))

        actions = self.ledger.distinct_actions()
        targets = [c.get("target", "") for c in caps
                   if c.get("target") and c.get("ok")]
        file_div = self._shannon_norm(targets)

        action_score = min(1.0, len(actions) / max(1, len(self.KNOWN_ACTIONS)))
        skill = (action_score + file_div) / 2
        smartness = (acceptance + test_pass) / 2

        return Fitness(
            smartness=smartness,
            skill=skill,
            acceptance_rate=acceptance,
            test_pass_rate=test_pass,
            distinct_actions=len(actions),
            file_diversity=file_div,
        )

    @staticmethod
    def _shannon_norm(counts_input: list[str]) -> float:
        if not counts_input:
            return 0.0
        counts = Counter(counts_input)
        total = sum(counts.values())
        entropy = -sum((c / total) * math.log2(c / total) for c in counts.values())
        max_entropy = math.log2(max(1, len(counts)))
        return entropy / max_entropy if max_entropy > 0 else 0.0

    # ---- A/B lineages ------------------------------------------------------

    @dataclass
    class LineageResult:
        name: str
        generations: int
        fitness: Fitness
        env: dict[str, str] = field(default_factory=dict)
        worktree: str = ""
        sha_after: str = ""

    def run_ab(self, lineages: list[str], *,
               generations: int = 3, base_env: dict[str, str] | None = None
               ) -> list["Evolution.LineageResult"]:
        """Run multiple lineages in parallel worktrees, return ranked results.

        Each lineage is a label like ``"A: small files only"``. The label
        is converted into env vars (``FORKLING_LABEL="A"``,
        ``FORKLING_STRATEGY="small files only"``) so the agent's planning
        can read them as selective pressure.

        NOTE: this is intentionally minimal for the MVP. A full
        implementation would spawn async subprocesses; we run them
        sequentially to keep the dependency surface zero.
        """
        results: list[Evolution.LineageResult] = []
        base_env = dict(base_env or {})
        for label in lineages:
            name, _, strategy = label.partition(":")
            name = name.strip() or label.strip()
            strategy = strategy.strip()
            env = {**base_env,
                   "FORKLING_LABEL": name,
                   "FORKLING_STRATEGY": strategy}
            result = self._run_single_lineage(name, strategy, env, generations)
            results.append(result)
        # Rank by total fitness descending.
        results.sort(key=lambda r: r.fitness.total, reverse=True)
        return results

    def _run_single_lineage(self, name: str, strategy: str,
                            env: dict[str, str], generations: int
                            ) -> "Evolution.LineageResult":
        worktree = Path(tempfile.mkdtemp(prefix=f"forkling-{name}-"))
        try:
            subprocess.run(
                ["git", "worktree", "add", "--detach", str(worktree), "HEAD"],
                cwd=self.repo_root, check=True, capture_output=True,
                env={**os.environ, **{k: v for k, v in env.items()
                                       if k != "PYTHONPATH"}},
            )
            for _ in range(generations):
                subprocess.run(
                    ["python", "-m", "forkling", "self-improve",
                     "--goal", f"Improve something. Lineage {name}. Strategy: {strategy}"],
                    cwd=worktree, capture_output=True, text=True,
                    env={**os.environ, **env},
                    timeout=300,
                )
            # Capture the lineage's own ledger (if it created one) and compute fitness.
            lin_ledger = CapabilityLedger(worktree / ".forkling" / "capabilities.jsonl")
            lin_grave = Graveyard(worktree / ".forkling" / "graveyard.jsonl")
            sub_evo = Evolution(lin_ledger, lin_grave, worktree)
            fit = sub_evo.fitness()
            sha = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=worktree, text=True,
            ).strip()
            return Evolution.LineageResult(
                name=name, generations=generations, fitness=fit,
                env=env, worktree=str(worktree), sha_after=sha,
            )
        finally:
            subprocess.run(["git", "worktree", "remove", "--force", str(worktree)],
                           cwd=self.repo_root, capture_output=True)
            shutil.rmtree(worktree, ignore_errors=True)


# ---- helpers ---------------------------------------------------------------


def format_fitness_history(history: list[Fitness]) -> str:
    """Format a fitness trajectory for a commit message or paper."""
    if not history:
        return "(no history)"
    lines = ["smartness | skill | total"]
    for i, f in enumerate(history, 1):
        lines.append(f"  gen {i:>3}  {f.smartness:.3f} | {f.skill:.3f} | {f.total:.3f}")
    return "\n".join(lines)