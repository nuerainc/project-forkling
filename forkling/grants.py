"""Grant hunter.

Maintains a JSON database of grant programs with eligibility metadata.
Matches the project's profile against each program, ranks by fit, and
drafts a tailored 2-paragraph proposal.

This is the agent's "money module" — once the forkling loop has produced
enough evolutionary history, forkling can use it as evidence in
applications.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ProjectProfile:
    name: str = "forkling"
    one_liner: str = ("Self-contained, self-improving AI agent that "
                      "evolves via git-native Darwinian selection.")
    tags: list[str] = field(default_factory=lambda: [
        "open-source", "ai", "self-improving", "agent",
        "evolution", "version-control", "reproducibility",
    ])
    open_source: bool = True
    license: str = "MIT"
    stage: str = "early"
    why_fit: str = ("forkling turns git into an evolutionary substrate "
                    "for AI agents; every commit is a generation, the "
                    "test suite is the fitness function, and the entire "
                    "history is auditable.")
    use_of_funds: str = ("Cover hosting for CI, a public evolutionary "
                         "history dataset, and 1-2 months of focused "
                         "development on the phylogenetic replay module.")
    evidence: str = ("Public git log shows N self-improvement generations; "
                     "every change gated by pytest; runs offline on $15 "
                     "hardware; zero paid API dependencies.")
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------


def load_db(path: str | Path = "grants.json") -> list[dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        return []
    return json.loads(p.read_text(encoding="utf-8"))


def save_db(grants: list[dict], path: str | Path = "grants.json") -> None:
    Path(path).write_text(json.dumps(grants, indent=2, sort_keys=True),
                          encoding="utf-8")


def _score(grant: dict, profile: ProjectProfile) -> float:
    """0..1 fit score. Higher is better."""
    s = 0.0
    required = {t.lower() for t in grant.get("requires", [])}
    have = {t.lower() for t in profile.tags}
    if not required:
        s += 0.5
    else:
        s += 0.5 * len(required & have) / len(required)
    if profile.open_source and grant.get("open_source"):
        s += 0.3
    if profile.stage in grant.get("stages", []):
        s += 0.2
    # Bonus for amount range fit (sweet spot $5k-$30k for an MVP).
    amt = grant.get("typical_amount_usd", 0)
    if 5_000 <= amt <= 30_000:
        s += 0.05
    return min(1.0, s)


def match(profile: ProjectProfile | dict | None = None,
          grants: list[dict] | None = None,
          db_path: str | Path = "grants.json") -> list[dict]:
    """Score each grant's fit against the project profile."""
    if profile is None:
        profile = ProjectProfile()
    if isinstance(profile, dict):
        profile = ProjectProfile(**{k: v for k, v in profile.items()
                                   if k in ProjectProfile.__dataclass_fields__})
    if grants is None:
        grants = load_db(db_path)
    out = []
    for g in grants:
        out.append({**g, "_fit": _score(g, profile)})
    out.sort(key=lambda x: x["_fit"], reverse=True)
    return out


def draft(grant: dict, profile: ProjectProfile | None = None) -> str:
    """Draft a 2-paragraph tailored proposal for a grant."""
    if profile is None:
        profile = ProjectProfile()
    return (
        f"Subject: Application — {grant['name']}\n\n"
        f"Dear {grant.get('sponsor', 'Team')},\n\n"
        f"{profile.name} is {profile.one_liner} It fits your "
        f"program's focus on {', '.join(grant.get('focus', []))} because "
        f"{profile.why_fit}\n\n"
        f"We request ${grant.get('typical_amount', 'TBD')} to "
        f"{profile.use_of_funds} Evidence of impact: {profile.evidence}\n\n"
        f"Public repo: https://github.com/<your-org>/forkling\n"
        f"License: {profile.license} (open source from day 1).\n\n"
        f"Sincerely,\n"
        f"The {profile.name} maintainers\n"
    )