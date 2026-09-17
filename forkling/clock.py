"""Project clock — forkland's internal sense of time.

The 365-day research cycle has a fixed t=0 anchor: 2026-09-16 21:00 MDT
(when the user said "today, 9pm, the project clock starts now"). Every
artifact in forkland that wants to talk about "how far along we are" —
ROADMAP.md, paper stage selection, grant stage tagging, fitness
trajectories — defers to this module.

The clock is sovereign: each fork can pin its own t=0 (via FORKLING_T0
epoch seconds, or FORKLING_T0_ISO as a fallback). This is critical for
Spoonica (the baseline), which started running alone after a delay and
needs its own t=0 so its diary timestamps make sense.

Why a clock at all? Two reasons:
  1. Without an anchor, "day 30 of the project" is a string in a doc;
     we cannot auto-fire paper milestones, dataset snapshots, grant
     deadlines, or heart-of-the-year retrospectives.
  2. Each fork can publish its own clock-timeline; comparing clocks
     across family members is the cleanest possible ablation.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


# Default project t=0 anchor. 2026-09-16 21:00 MDT (UTC-6 in MDT).
# UTC: 2026-09-17 03:00:00 UTC.
DEFAULT_T0_UTC = "2026-09-17T03:00:00+00:00"
DEFAULT_T0_EPOCH = int(datetime.fromisoformat(DEFAULT_T0_UTC).timestamp())

# Total cycle length in days. This is THE reference number for the
# year-1 prospectus and every stage gate.
CYCLE_DAYS = 365


@dataclass
class Clock:
    """Project clock for one fork."""

    t0_epoch: float
    fork_name: str
    note: str = ""

    @classmethod
    def from_env(cls, fork_name: str = "forkland") -> "Clock":
        """Build a clock from env-overridable inputs.

        Precedence: FORKLING_T0 (epoch seconds) > FORKLING_T0_ISO (ISO 8601)
        > the hard-coded default anchor above.
        """
        raw_epoch = os.environ.get("FORKLING_T0")
        if raw_epoch:
            try:
                t0 = float(raw_epoch)
                return cls(t0_epoch=t0, fork_name=fork_name,
                           note=f"from FORKLING_T0 env")
            except ValueError:
                pass
        raw_iso = os.environ.get("FORKLING_T0_ISO", DEFAULT_T0_UTC)
        try:
            t0 = datetime.fromisoformat(raw_iso).timestamp()
        except ValueError:
            t0 = DEFAULT_T0_EPOCH
        return cls(t0_epoch=t0, fork_name=fork_name,
                   note=f"t0_anchor={raw_iso}")

    @classmethod
    def from_file(cls, path: str | Path) -> "Clock":
        """Load a clock from disk (if the fork has persisted one)."""
        p = Path(path).expanduser()
        if not p.exists():
            return cls.from_env()
        try:
            obj = json.loads(p.read_text(encoding="utf-8"))
            return cls(
                t0_epoch=float(obj["t0_epoch"]),
                fork_name=obj.get("fork_name", "forkland"),
                note=obj.get("note", ""),
            )
        except (json.JSONDecodeError, KeyError, ValueError):
            return cls.from_env()

    def save(self, path: str | Path) -> None:
        p = Path(path).expanduser()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")

    # ---- queries ----------------------------------------------------------

    def now_epoch(self) -> float:
        return time.time()

    def now_iso(self) -> str:
        return datetime.fromtimestamp(self.now_epoch(), tz=timezone.utc).isoformat()

    def day_index(self, at: float | None = None) -> int:
        """0-indexed day since t=0 (so day 0 = the day t=0 fell on)."""
        at = at if at is not None else self.now_epoch()
        return int((at - self.t0_epoch) // 86400)

    def day_number(self, at: float | None = None) -> int:
        """1-indexed day since t=0 (so day 1 = the first full day after t=0)."""
        return self.day_index(at) + 1

    def days_into_cycle(self, at: float | None = None) -> int:
        """Days elapsed into the 365-day cycle (clamped 0..365)."""
        return max(0, min(CYCLE_DAYS, self.day_index(at)))

    def days_remaining(self, at: float | None = None) -> int:
        return max(0, CYCLE_DAYS - self.day_index(at))

    def cycle_progress(self, at: float | None = None) -> float:
        """Float 0.0..1.0 — how far we are through the 365-day cycle."""
        return self.days_into_cycle(at) / CYCLE_DAYS

    def stage(self, at: float | None = None) -> str:
        """The current paper stage for the 365-day cycle."""
        d = self.day_index(at)
        if d < 7:
            return "stage-0-isolation"
        if d < 30:
            return "stage-1-first-month"
        if d < 60:
            return "stage-2-baseline-arrives"
        if d < 90:
            return "stage-3-family-grows"
        if d < 180:
            return "stage-4-mid-year"
        if d < 270:
            return "stage-5-late-year"
        if d < CYCLE_DAYS:
            return "stage-6-closing"
        return "stage-7-retrospective"

    def stage_description(self, at: float | None = None) -> str:
        idx = self.day_index(at)
        stages = [
            (7, "Isolation: Forkland alone, observe baseline behavior"),
            (30, "First solo month: write the first paper; observe the LLM"),
            (60, "Baseline arrives: Spoonica enters; A/B starts"),
            (90, "Family grows: Sporklyn arrives; cross-fork data begins"),
            (180, "Mid-year: cross-fork paper; first half-year dataset export"),
            (270, "Late year: Knifling + family-wide experiment; pre-archive work"),
            (365, "Closing: lock the year-1 dataset; retrospective draft begins"),
            (10**9, "Retrospective: year-end paper; reset for year 2"),
        ]
        for bound, desc in stages:
            if idx < bound:
                return desc
        return stages[-1][1]

    # ---- human formatting ------------------------------------------------

    def fmt_age(self, at: float | None = None) -> str:
        d = self.day_index(at)
        h = int(((at - self.t0_epoch) % 86400) // 3600) if at else 0
        if d == 0:
            return f"day 0 (t+{h}h)"
        return f"day {d} (t+{d * 24 + h}h)"

    def as_dict(self, at: float | None = None) -> dict:
        at = at if at is not None else self.now_epoch()
        return {
            "fork_name": self.fork_name,
            "t0_epoch": self.t0_epoch,
            "t0_iso": datetime.fromtimestamp(self.t0_epoch, tz=timezone.utc).isoformat(),
            "now_epoch": at,
            "now_iso": datetime.fromtimestamp(at, tz=timezone.utc).isoformat(),
            "day_index": self.day_index(at),
            "day_number": self.day_number(at),
            "days_into_cycle": self.days_into_cycle(at),
            "days_remaining": self.days_remaining(at),
            "cycle_progress": round(self.cycle_progress(at), 4),
            "stage": self.stage(at),
            "stage_description": self.stage_description(at),
            "age": self.fmt_age(at),
            "cycle_days": CYCLE_DAYS,
            "note": self.note,
        }