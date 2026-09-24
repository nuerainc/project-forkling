"""Forkland Forkling evolution loop — continuous natural selection.

Real natural selection doesn't wait between generations. An organism
under selection pressure is *always* either being tested, mutating, or
dying. There's no clock interval. The "tick" is a generation.

This module is the natural-selection model. The loop is dead simple:

  while not stop:
    generation += 1
    pick a target file (rotate)
    call SelfImprover.propose_and_apply()   # propose + test + commit/rollback
    # NO SLEEP. The LLM call IS the throttle.

That's it. No subprocess, no heartbeat cadence, no idle waiting. The
agent runs as fast as the LLM (variation) + pytest (selection) allow.
Every ``propose_and_apply`` call is one generation.

Substrate is unchanged: every successful generation is a real git
commit. Every failed generation is a real rollback to the previous
SHA. The ledger records both. The diary captures both.

Why this is different from the heartbeat model:
  - heartbeat = one attempt every N minutes, idle between
  - evolve    = one attempt back-to-back, no idle

Selection pressure:
  - LLM proposes (variation)
  - pytest -q gates (selection)
  - commits land or rollbacks happen (survival / death)
  - capability ledger grows with each accepted generation

Comparison to DGM:
  - DGM edits a single in-memory Python source and benchmarks it
  - this loop edits the working tree (real commits) and gates on the
    agent's own test suite (no benchmark gaming)

The rate at which the loop runs is set entirely by variation (LLM
response time) and selection (pytest run time). With qwen3:4b on a
local machine that's typically 30-90 seconds per generation.
"""

from __future__ import annotations

import argparse
import os
import signal
import sys
import threading
import time
from pathlib import Path

from .config import Config
from .diary import Diary
from .goals import Goals
from .self_improve import SelfImprover


PID_FILENAME = "evolve.pid"
STOP_FILENAME = "evolve.stop"
STATUS_FILENAME = "evolve.status.json"


class Evolver:
    """Continuous natural-selection loop. No idle waiting.

    True agency: every ``reflect_every`` generations, the loop pauses
    briefly to ask the LLM "what should you do next?" — the LLM
    reads the diary + ledger and proposes its own goals. Pending
    goals drive the text of the next generations, so the agent's
    work is *goal-directed*, not just "patch random files".

    Self-reflection is also wired into the loop cadence so a quiet
    substrate naturally produces reflection cycles ("what should I
    want?") instead of inert noops.
    """

    def __init__(self, cfg: Config, repo: Path, *,
                 max_attempts: int | None = None,
                 model: str | None = None,
                 reflect_every: int | None = None) -> None:
        self.cfg = cfg
        self.repo = repo
        self.max_attempts = max_attempts
        # Per-fork model override; falls back to cfg.ollama_model.
        self.model_override = model
        if model:
            # Also patch the live Config so every LLM client we build
            # below uses this model.
            self.cfg.ollama_model = model
        # Self-reflection: every N generations, ask the LLM what to
        # pursue. Default 5; lower for high-cadence small models.
        # Accept None from the CLI and fall back to the documented default.
        if reflect_every is None:
            reflect_every = 5
        self.reflect_every = max(1, int(reflect_every))

        # Goals state — lives alongside the diary.
        self._goals_path = Path(cfg.memory_dir) / "goals.jsonl"
        self._goals = Goals(self._goals_path)

        self._stop_event = threading.Event()
        self._started_at = time.time()

        self.attempt_count = 0
        self.committed_count = 0
        self.rolled_back_count = 0
        self.noop_count = 0
        self.last_target: str | None = None
        self.last_outcome: str | None = None

        self.state_dir = repo / ".forkling"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.pid_path = self.state_dir / PID_FILENAME
        self.stop_path = self.state_dir / STOP_FILENAME
        self.status_path = self.state_dir / STATUS_FILENAME

        # Lazy: built on first iteration.
        self._improver: SelfImprover | None = None

    # ---- entry point -------------------------------------------------------

    def run_forever(self) -> int:
        """Block until SIGINT / stop-flag / max_attempts. Returns 0 on exit."""
        self._write_pidfile()
        self._log("evolve.started",
                  f"max_attempts={self.max_attempts} repo={self.repo} "
                  f"reflect_every={self.reflect_every}")
        self._install_signal_handlers()

        try:
            while not self._should_stop():
                if (self.max_attempts is not None
                        and self.attempt_count >= self.max_attempts):
                    self._log("evolve.max_attempts_reached",
                              f"exiting after {self.attempt_count} generations")
                    break
                # Periodic self-reflection. Generates the agent's own
                # goals. Silent no-op if nothing new comes up.
                if (self.reflect_every > 0
                        and self.attempt_count > 0
                        and self.attempt_count % self.reflect_every == 0):
                    self._reflect_cycle()
                # ONE generation. No sleep after.
                self.run_one_generation()
                self._write_status()
                # Loop immediately. NO SLEEP.
        finally:
            self._remove_pidfile()
            self._remove_stop_flag()
            self._log("evolve.stopped",
                      f"attempts={self.attempt_count} "
                      f"committed={self.committed_count} "
                      f"rolled_back={self.rolled_back_count} "
                      f"noop={self.noop_count} "
                      f"goals={len(self._goals.all())}")
        return 0

    def run_one_generation(self) -> tuple[str, str]:
        """Run ONE generation. Returns (outcome, target_relative_path).

        Outcomes: "committed" | "rolled_back" | "noop" | "error"

        If there's a pending goal, the prompt is augmented with the
        goal text so the LLM works toward it instead of producing
        arbitrary patches.
        """
        self.attempt_count += 1
        gen = self.attempt_count
        current_goal = self._goals.pick_current()
        goal_block = ""
        if current_goal is not None:
            goal_block = (f"\n\nYou have a pending goal "
                          f"[{current_goal.priority}] {current_goal.text}."
                          f" Try to make progress on this goal this "
                          f"generation (a small patch toward it, or a "
                          f"new module that enables it).")
            self._goals.set_status(current_goal.id, "in_progress")
        prompt_goal = (f"Generation #{gen}. Make ONE tiny safe improvement "
                       f"to the next file or a brand-new module that grows "
                       f"your capabilities. Smallest change you can find. "
                       f"If you can't find one, say noop."
                       f"{goal_block}")
        try:
            improver = self._get_improver()
            result = improver.propose_and_apply(goal=prompt_goal)
        except Exception as e:
            self.last_outcome = "error"
            self.last_target = None
            self._log("evolve.generation.error",
                      f"gen={gen} err={e.__class__.__name__}: {e}")
            return ("error", "")

        # Extract the target that was picked.
        target = ""
        try:
            target = str(self._get_improver_target() or "")
        except Exception:
            target = ""
        self.last_target = target

        if result.committed:
            self.committed_count += 1
            self.last_outcome = "committed"
            self._log("evolve.generation.committed",
                      f"gen={gen} target={target} "
                      f"sha={result.after_sha[:7]} "
                      f"summary={result.patch_summary[:80]} "
                      f"kind={result.kind}")
            # Record goal progress if we had one.
            if current_goal is not None:
                progress = f"committed {result.kind}: {result.patch_summary}"
                self._goals.record_progress(current_goal.id, progress)
                # Mark the goal as achieved if the new file is the goal.
                if (result.kind == "new_file"
                        and result.new_skill
                        and result.new_skill in current_goal.text.lower()):
                    self._goals.set_status(current_goal.id, "achieved",
                                            note=result.patch_summary)
            return ("committed", target)
        if result.rolled_back:
            self.rolled_back_count += 1
            self.last_outcome = "rolled_back"
            self._log("evolve.generation.rolled_back",
                      f"gen={gen} target={target} "
                      f"reason={result.note[:120]}")
            if current_goal is not None:
                self._goals.record_progress(
                    current_goal.id,
                    f"rolled_back: {result.note[:120]}")
            return ("rolled_back", target)
        # No change proposed — LLM said "noop" or no patch found.
        self.noop_count += 1
        self.last_outcome = "noop"
        self._log("evolve.generation.noop",
                  f"gen={gen} target={target} note={result.note[:120]}")
        return ("noop", target)

    def _reflect_cycle(self) -> None:
        """One self-reflection step. Proposes new goals from the diary."""
        try:
            improver = self._get_improver()
            agent = improver.agent
            memory_dir = Path(self.cfg.memory_dir)
            diary = Diary(memory_dir / "diary.jsonl")
            from .trace import Trace
            trace = Trace(memory_dir / "trace.jsonl")
            new_goals = self._goals.reflect_via_llm(
                agent.llm, diary, trace=trace)
            for g in new_goals:
                self._log("goal.proposed",
                          f"[p={g.priority}] {g.text}",
                          goal_id=g.id, priority=g.priority)
        except Exception as e:
            self._log("evolve.reflect.error",
                      f"{e.__class__.__name__}: {e}")

    # ---- stop control ------------------------------------------------------

    def request_stop(self) -> None:
        self._stop_event.set()
        try:
            self.stop_path.touch(exist_ok=True)
        except OSError:
            pass

    # ---- internals ---------------------------------------------------------

    def _get_improver(self) -> SelfImprover:
        if self._improver is None:
            from .agent import Agent
            from .capability import CapabilityLedger
            from .graveyard import Graveyard
            from .llm import LLM
            from .memory import Memory
            from .planner import Planner
            from .trace import Trace
            memory_dir = Path(self.cfg.memory_dir)
            trace = Trace(memory_dir / "trace.jsonl")
            llm = LLM(url=self.cfg.ollama_url,
                      model=self.cfg.ollama_model,
                      timeout=self.cfg.llm_timeout,
                      trace=trace)
            memory = Memory(str(memory_dir))
            graveyard = Graveyard(memory_dir / "graveyard.jsonl")
            planner = Planner(llm, graveyard=graveyard)
            agent = Agent(cfg=self.cfg, llm=llm, memory=memory,
                          planner=planner)
            self._improver = SelfImprover(agent)
        return self._improver

    def _get_improver_target(self) -> Path | None:
        """Best-effort: return the path the improver just edited."""
        # SelfImprover stores it as agent.state. We use _pick_target's
        # logic: cycle through forkling/*.py by attempt_count.
        pkg = self.repo / "forkling"
        targets = sorted(p for p in pkg.glob("*.py")
                         if p.name != "__init__.py")
        if not targets:
            return None
        # Note: SelfImprover._pick_target may use SAFE_FILES (a subset)
        # not the full glob. Best effort — we use the same rotation.
        idx = (self.attempt_count - 1) % len(targets)
        return targets[idx]

    def _should_stop(self) -> bool:
        return (self._stop_event.is_set()
                or self.stop_path.exists())

    def _install_signal_handlers(self) -> None:
        def _handler(signum, frame):
            self._log("evolve.signal",
                      f"received signal {signum}; exiting after current gen")
            self._stop_event.set()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                signal.signal(sig, _handler)
            except (ValueError, OSError):
                pass
        if hasattr(signal, "SIGBREAK"):
            try:
                signal.signal(signal.SIGBREAK, _handler)  # type: ignore[attr-defined]
            except (ValueError, OSError):
                pass

    def _write_pidfile(self) -> None:
        try:
            self.pid_path.write_text(str(os.getpid()), encoding="utf-8")
        except OSError as e:
            print(f"evolve: failed to write pidfile: {e}", file=sys.stderr)

    def _remove_pidfile(self) -> None:
        try:
            if self.pid_path.exists():
                self.pid_path.unlink()
        except OSError:
            pass

    def _remove_stop_flag(self) -> None:
        try:
            if self.stop_path.exists():
                self.stop_path.unlink()
        except OSError:
            pass

    def _write_status(self) -> None:
        import json
        payload = {
            "pid": os.getpid(),
            "started_at": self._started_at,
            "attempt_count": self.attempt_count,
            "committed_count": self.committed_count,
            "rolled_back_count": self.rolled_back_count,
            "noop_count": self.noop_count,
            "last_target": self.last_target,
            "last_outcome": self.last_outcome,
            "repo": str(self.repo),
        }
        try:
            self.status_path.write_text(json.dumps(payload, indent=2),
                                        encoding="utf-8")
        except OSError:
            pass

    def _log(self, kind: str, content: str) -> None:
        try:
            memory_dir = Path(self.cfg.memory_dir)
            Diary(memory_dir / "diary.jsonl").write(kind, content)
        except Exception as e:
            print(f"evolve: diary write failed ({e}); {kind}: {content}",
                  file=sys.stderr)
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{ts}] [{kind}] {content}", file=sys.stderr)


# ---- static helpers used by the CLI --------------------------------------

def is_running(repo: Path) -> bool:
    p = repo / ".forkling" / PID_FILENAME
    if not p.exists():
        return False
    try:
        pid = int(p.read_text(encoding="utf-8").strip())
    except (ValueError, OSError):
        return False
    return _pid_alive(pid)


def read_status(repo: Path) -> dict | None:
    import json
    p = repo / ".forkling" / STATUS_FILENAME
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def request_stop(repo: Path) -> bool:
    if not is_running(repo):
        return False
    stop = repo / ".forkling" / STOP_FILENAME
    try:
        stop.touch(exist_ok=True)
    except OSError:
        return False
    pid_path = repo / ".forkling" / PID_FILENAME
    try:
        pid = int(pid_path.read_text(encoding="utf-8").strip())
        if _pid_alive(pid):
            try:
                os.kill(pid, signal.SIGTERM)
            except (OSError, ValueError):
                pass
    except (OSError, ValueError):
        pass
    return True


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if sys.platform == "win32":
        try:
            import ctypes
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            PROCESS_QUERY_LIMITED = 0x1000
            STILL_ACTIVE = 259
            handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED, False, pid)
            if not handle:
                return False
            try:
                exit_code = ctypes.c_ulong()
                ok = kernel32.GetExitCodeProcess(handle,
                                                 ctypes.byref(exit_code))
                return bool(ok) and exit_code.value == STILL_ACTIVE
            finally:
                kernel32.CloseHandle(handle)
        except Exception:
            return False
    else:
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False
