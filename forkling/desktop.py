"""Forkland Forkling desktop companion.

A small Tk UI that shows the agent's runtime health at a glance:
  - heartbeat status (GREEN / YELLOW / RED) + last heartbeat time
  - project clock: day, stage, cycle progress
  - ledger / diary / graveyard / family / trace counts
  - last N diary entries (so you can see what Forkland has been doing)
  - last N LLM calls (so you can see if the model is actually firing)
  - action buttons: run heartbeat, plant trigger, view paper,
    export dataset, verify ledger, refresh

Design constraints (project-wide):
  - **stdlib only.** Tk is in the stdlib on Windows / macOS / Linux.
  - **No write operations unless the user clicks a button.** Read-only
    by default; the auto-refresh only re-reads state.
  - **Survives sovereign mode.** If Tk is not available (headless
    server, CI runner), the ``forkling desktop`` command should print
    a helpful message and exit 0 — never crash the agent.

This module deliberately does NOT call LLM.complete() or any tools
that mutate state. It is purely a *viewer* + a few safe action
triggers. The user retains authority over the agent's edits.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

try:
    import tkinter as tk
    from tkinter import messagebox, scrolledtext, ttk
except ImportError:  # Python built without Tk (headless Linux, Pi images)
    tk = messagebox = scrolledtext = ttk = None

from .capability import CapabilityLedger
from .clock import Clock
from .config import Config
from .diary import Diary
from .evolution import Evolution
from .family import Family
from .graveyard import Graveyard
from .trace import Trace


# Heartbeat status thresholds (seconds since last run).
GREEN_MAX = 30 * 60      # < 30 min: GREEN
YELLOW_MAX = 2 * 60 * 60  # < 2 h:    YELLOW
# >= 2 h:                          RED


def _status_color(seconds_since: float | None) -> tuple[str, str]:
    """Returns (label, color) for the heartbeat status."""
    if seconds_since is None:
        return "NEVER", "#666666"
    if seconds_since < GREEN_MAX:
        return "GREEN", "#2e7d32"
    if seconds_since < YELLOW_MAX:
        return "YELLOW", "#f9a825"
    return "RED", "#c62828"


def _format_age(seconds: float | None) -> str:
    if seconds is None:
        return "never"
    if seconds < 60:
        return f"{int(seconds)}s ago"
    if seconds < 3600:
        return f"{int(seconds // 60)}m ago"
    if seconds < 86400:
        return f"{seconds / 3600:.1f}h ago"
    return f"{seconds / 86400:.1f}d ago"


def collect_status(cfg: Config, repo: Path) -> dict:
    """Snapshot the current state of Forkland Forkling for the UI.

    Pure read; safe to call on every refresh tick.
    """
    memory_dir = Path(cfg.memory_dir)

    # Last heartbeat (look for the heartbeat log or the most recent
    # self-improve/heartbeat-originated diary entry).
    last_heartbeat_ts: float | None = None
    heartbeat_log = repo / ".forkling" / "heartbeat.log"
    if heartbeat_log.exists():
        try:
            for line in reversed(heartbeat_log.read_text(
                    encoding="utf-8").splitlines()):
                if not line.strip():
                    continue
                try:
                    obj = json.loads(line)
                    last_heartbeat_ts = obj.get("ran_at")
                    break
                except json.JSONDecodeError:
                    continue
        except OSError:
            pass

    # Diary / ledger / graveyard counts.
    diary = Diary(memory_dir / "diary.jsonl")
    ledger = CapabilityLedger(memory_dir / "capabilities.jsonl")
    graveyard = Graveyard(memory_dir / "graveyard.jsonl")
    family = Family(memory_dir / "family.json")
    trace = Trace(memory_dir / "trace.jsonl")

    diary_entries = diary.entries()
    diary_recent = diary_entries[-5:][::-1]

    trace_recent = trace.entries(limit=5)[::-1]
    trace_stats = trace.stats() if trace.path.exists() else {"total": 0}

    family_members = family.refresh() if family.path.exists() else []

    # Clock.
    clock = Clock.from_env()
    clock_dict = clock.as_dict()

    # Fitness snapshot.
    try:
        fit = Evolution(ledger, graveyard, repo).fitness().as_dict()
    except Exception as e:
        fit = {"error": str(e)}

    seconds_since = (time.time() - last_heartbeat_ts) if last_heartbeat_ts else None
    status_label, status_color = _status_color(seconds_since)

    return {
        "status_label": status_label,
        "status_color": status_color,
        "seconds_since_heartbeat": seconds_since,
        "last_heartbeat_age": _format_age(seconds_since),
        "clock": clock_dict,
        "ledger_count": len(ledger.entries()),
        "diary_count": len(diary_entries),
        "graveyard_count": len(graveyard.entries()),
        "family_count": len(family_members),
        "family_members": [
            {"name": m.name, "last_seen": _format_age(
                (time.time() - m.last_seen_ts) if m.last_seen_ts else None)}
            for m in family_members
        ],
        "diary_recent": [
            {"ts": e.get("ts"), "kind": e.get("kind", "?"),
             "content": (e.get("content") or "")[:120]}
            for e in diary_recent
        ],
        "trace_stats": trace_stats,
        "trace_recent": [
            {"ts": e.get("ts"), "kind": e.get("kind", "?"),
             "model": e.get("model", "?"),
             "used_llm": e.get("used_llm"),
             "latency_ms": e.get("latency_ms", 0),
             "task": (e.get("task") or "")[:60]}
            for e in trace_recent
        ],
        "fitness": fit,
    }


def launch(cfg: Config, repo: Path, refresh_seconds: int = 15) -> int:
    """Launch the desktop UI. Returns 0 on graceful exit, 1 on error."""
    if tk is None:
        print("forkling desktop: tkinter is not installed in this Python.")
        print("On a headless server, run `forkling doctor` and `forkling fitness` instead.")
        return 0
    try:
        root = tk.Tk()
    except tk.TclError as e:
        # Headless: no display. Print a friendly message and exit 0.
        print(f"forkling desktop: no display available ({e.__class__.__name__}: {e})")
        print("This command requires a graphical display (X11 / Wayland / Windows desktop).")
        print("On a headless server, run `forkling doctor` and `forkling fitness` instead.")
        return 0
    except Exception as e:  # pragma: no cover — defensive
        print(f"forkling desktop: failed to launch ({e.__class__.__name__}: {e})",
              file=sys.stderr)
        return 1

    app = _DesktopApp(root, cfg=cfg, repo=repo,
                      refresh_seconds=refresh_seconds)
    app.refresh()
    app.start_auto_refresh()
    root.mainloop()
    return 0


class _DesktopApp:
    """The Tk application. Keep the rendering logic close to the data."""

    def __init__(self, root: tk.Tk, *, cfg: Config, repo: Path,
                 refresh_seconds: int = 15) -> None:
        self.root = root
        self.cfg = cfg
        self.repo = repo
        self.refresh_seconds = refresh_seconds
        self._snapshot: dict = {}

        self.root.title(f"Forkland Forkling — {repo.name}")
        self.root.geometry("720x820")
        self.root.minsize(640, 720)

        # Apply a clean ttk theme.
        style = ttk.Style()
        if "vista" in style.theme_names():
            style.theme_use("vista")  # Windows-native
        elif "clam" in style.theme_names():
            style.theme_use("clam")

        self._build()

    # ---- build ------------------------------------------------------------

    def _build(self) -> None:
        outer = ttk.Frame(self.root, padding=10)
        outer.pack(fill="both", expand=True)

        # Status bar.
        top = ttk.Frame(outer)
        top.pack(fill="x")
        ttk.Label(top, text="🍴 Forkland Forkling",
                  font=("Segoe UI", 16, "bold")).pack(side="left")
        self.stage_label = ttk.Label(top, text="stage ?",
                                     font=("Segoe UI", 11))
        self.stage_label.pack(side="right")

        # Status indicator row.
        status_row = ttk.Frame(outer)
        status_row.pack(fill="x", pady=(8, 4))
        self.status_dot = tk.Label(status_row, text="●", font=("Segoe UI", 18),
                                   fg="#666")
        self.status_dot.pack(side="left")
        self.status_text = ttk.Label(status_row, text="loading…",
                                     font=("Segoe UI", 11))
        self.status_text.pack(side="left", padx=(6, 0))

        # Clock + counts.
        meta = ttk.LabelFrame(outer, text="Status", padding=8)
        meta.pack(fill="x", pady=4)
        self.meta_text = tk.Text(meta, height=6, wrap="word",
                                 font=("Consolas", 10),
                                 background=meta.cget("background"),
                                 relief="flat", borderwidth=0)
        self.meta_text.pack(fill="x")
        self.meta_text.configure(state="disabled")

        # Recent diary.
        diary_frame = ttk.LabelFrame(outer, text="Recent diary", padding=8)
        diary_frame.pack(fill="both", expand=True, pady=4)
        self.diary_text = scrolledtext.ScrolledText(
            diary_frame, height=8, wrap="word",
            font=("Consolas", 9), state="disabled",
        )
        self.diary_text.pack(fill="both", expand=True)

        # Recent LLM calls.
        trace_frame = ttk.LabelFrame(outer, text="Recent LLM calls",
                                     padding=8)
        trace_frame.pack(fill="both", expand=True, pady=4)
        self.trace_text = scrolledtext.ScrolledText(
            trace_frame, height=6, wrap="word",
            font=("Consolas", 9), state="disabled",
        )
        self.trace_text.pack(fill="both", expand=True)

        # Action buttons.
        buttons = ttk.Frame(outer)
        buttons.pack(fill="x", pady=(8, 0))
        ttk.Button(buttons, text="Run heartbeat now",
                   command=self.action_heartbeat).pack(side="left", padx=2)
        ttk.Button(buttons, text="Refresh",
                   command=self.refresh).pack(side="left", padx=2)
        ttk.Button(buttons, text="View paper",
                   command=self.action_view_paper).pack(side="left", padx=2)
        ttk.Button(buttons, text="Export dataset",
                   command=self.action_export).pack(side="left", padx=2)
        ttk.Button(buttons, text="Verify ledger",
                   command=self.action_verify).pack(side="left", padx=2)

    # ---- data refresh ------------------------------------------------------

    def refresh(self) -> None:
        """Re-read state from disk and redraw."""
        try:
            self._snapshot = collect_status(self.cfg, self.repo)
        except Exception as e:
            self._set_status("ERROR", "#c62828")
            self.status_text.configure(
                text=f"failed to read state: {e.__class__.__name__}: {e}")
            return
        self._render()

    def _render(self) -> None:
        s = self._snapshot

        # Top-right stage label.
        clock = s["clock"]
        self.stage_label.configure(
            text=f"day {clock['day_index']}/{clock['cycle_days']}  "
                 f"({clock['cycle_progress']*100:.1f}%)  {clock['stage']}")

        # Status indicator.
        self._set_status(s["status_label"], s["status_color"])
        age = s["last_heartbeat_age"]
        self.status_text.configure(
            text=f" heartbeat  ·  last run {age}"
                 + (f"  ·  {clock['stage_description']}" if clock else "")
        )

        # Meta block.
        lines = [
            f"Stage:       {clock['stage']} — {clock['stage_description']}",
            f"Day:         {clock['day_index']} of {clock['cycle_days']}  "
            f"({clock['cycle_progress']*100:.2f}% of cycle)",
            f"Anchor:      {clock['t0_iso']}",
            f"Ledger:      {s['ledger_count']} capability entries",
            f"Diary:       {s['diary_count']} entries  ·  "
            f"Graveyard: {s['graveyard_count']} rejected patches",
            f"Family:      {s['family_count']} members  ·  "
            f"Trace: {s['trace_stats'].get('total', 0)} LLM calls "
            f"({s['trace_stats'].get('used_llm', 0)} LLM, "
            f"{s['trace_stats'].get('fallback_used', 0)} fallback)",
        ]
        fit = s["fitness"]
        if "error" not in fit:
            lines.append(
                f"Fitness:     smartness={fit.get('smartness', 0):.3f}  "
                f"skill={fit.get('skill', 0):.3f}  "
                f"total={fit.get('total', 0):.3f}"
            )
        if s["family_members"]:
            names = ", ".join(m["name"] for m in s["family_members"])
            lines.append(f"Family members: {names}")

        self._set_widget_text(self.meta_text, "\n".join(lines))

        # Diary block.
        diary_lines = []
        for e in s["diary_recent"]:
            ts = time.strftime("%Y-%m-%d %H:%M:%S",
                               time.localtime(e.get("ts") or 0))
            diary_lines.append(
                f"[{ts}] {e['kind']:<18} {e['content']}")
        if not diary_lines:
            diary_lines = ["(diary is empty)"]
        self._set_widget_text(self.diary_text, "\n".join(diary_lines))

        # Trace block.
        trace_lines = []
        for e in s["trace_recent"]:
            ts = time.strftime("%Y-%m-%d %H:%M:%S",
                               time.localtime(e.get("ts") or 0))
            tag = "LLM" if e.get("used_llm") else "fallback"
            trace_lines.append(
                f"[{ts}] {e['kind']:<18} {e['model']:<14} "
                f"{tag:<9} {e.get('latency_ms', 0):>5}ms  {e['task']}"
            )
        if not trace_lines:
            trace_lines = ["(no LLM calls recorded yet)"]
        self._set_widget_text(self.trace_text, "\n".join(trace_lines))

    def _set_widget_text(self, widget: tk.Text, text: str) -> None:
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", text)
        widget.configure(state="disabled")

    def _set_status(self, label: str, color: str) -> None:
        self.status_dot.configure(fg=color, text="●")
        self.status_text.configure(text=f"{label}")

    # ---- auto-refresh ------------------------------------------------------

    def start_auto_refresh(self) -> None:
        self.root.after(self.refresh_seconds * 1000, self._tick)

    def _tick(self) -> None:
        self.refresh()
        self.root.after(self.refresh_seconds * 1000, self._tick)

    # ---- actions -----------------------------------------------------------

    def action_heartbeat(self) -> None:
        if not messagebox.askyesno(
                "Run heartbeat?",
                "This will run `forkling heartbeat --repo " + str(self.repo)
                + "`.\nIt may take several minutes and call the local LLM.\n\n"
                "Proceed?"):
            return
        self.status_text.configure(text=" heartbeat running…")
        self.root.update_idletasks()
        try:
            r = subprocess.run(
                [sys.executable, "-m", "forkling", "heartbeat",
                 "--repo", str(self.repo), "--skip-improve"],
                capture_output=True, text=True, timeout=900,
            )
            ok = r.returncode == 0
            messagebox.showinfo(
                "Heartbeat done",
                f"exit={r.returncode}\n\n"
                f"stdout (tail):\n{r.stdout[-400:]}\n\n"
                f"stderr (tail):\n{r.stderr[-200:]}",
            )
        except Exception as e:
            ok = False
            messagebox.showerror(
                "Heartbeat failed",
                f"{e.__class__.__name__}: {e}")
        self.refresh()

    def action_view_paper(self) -> None:
        paper = self.repo / "paper" / "paper.md"
        if not paper.exists():
            messagebox.showinfo("No paper yet",
                                "paper/paper.md does not exist yet.")
            return
        try:
            if sys.platform == "win32":
                os.startfile(str(paper))  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(paper)])
            else:
                subprocess.Popen(["xdg-open", str(paper)])
        except Exception as e:
            messagebox.showerror("Could not open paper",
                                 f"{e.__class__.__name__}: {e}")

    def action_export(self) -> None:
        try:
            r = subprocess.run(
                [sys.executable, "-m", "forkling", "export-dataset"],
                cwd=str(self.repo), capture_output=True, text=True,
                timeout=60,
            )
            messagebox.showinfo(
                "Dataset export",
                f"exit={r.returncode}\n\n{r.stdout[-300:]}\n{r.stderr[-200:]}",
            )
        except Exception as e:
            messagebox.showerror("Export failed",
                                 f"{e.__class__.__name__}: {e}")
        self.refresh()

    def action_verify(self) -> None:
        try:
            r = subprocess.run(
                [sys.executable, "-m", "forkling", "verify"],
                cwd=str(self.repo), capture_output=True, text=True,
                timeout=30,
            )
            messagebox.showinfo(
                "Ledger verify",
                f"exit={r.returncode}\n\n{r.stdout[-400:]}",
            )
        except Exception as e:
            messagebox.showerror("Verify failed",
                                 f"{e.__class__.__name__}: {e}")


# Late import so the module loads even on systems without `os.startfile`.
import os  # noqa: E402
