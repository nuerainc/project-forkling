"""Tests for the goals module — self-reflection + autonomous goal
generation + goal-driven Evolver integration.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from forkling.config import Config
from forkling.diary import Diary
from forkling.goals import (
    GOAL_STATUSES, Goal, Goals, _parse_goals_response,
)


def _make_goals(tmp_path: Path) -> Goals:
    mem = tmp_path / "mem"
    mem.mkdir()
    return Goals(mem / "goals.jsonl")


# ---- core Goals class ---------------------------------------------------


def test_propose_creates_goal_with_unique_id(tmp_path):
    g = _make_goals(tmp_path)
    goal = g.propose("build a wave decoder", priority=2, kind="new_skill")
    assert goal.id.startswith("goal-")
    assert goal.text == "build a wave decoder"
    assert goal.priority == 2
    assert goal.kind == "new_skill"
    assert goal.status == "pending"


def test_propose_validates_priority_clamped(tmp_path):
    g = _make_goals(tmp_path)
    too_high = g.propose("x", priority=99)
    too_low = g.propose("x", priority=0)
    assert too_high.priority == 5
    assert too_low.priority == 1


def test_propose_validates_kind(tmp_path):
    g = _make_goals(tmp_path)
    bad = g.propose("x", kind="not_a_kind")
    assert bad.kind == "new_skill"


def test_list_all_returns_proposed_goals(tmp_path):
    g = _make_goals(tmp_path)
    a = g.propose("first goal")
    b = g.propose("second goal")
    all_goals = g.all()
    assert {x.text for x in all_goals} == {"first goal", "second goal"}


def test_set_status_changes_status_with_progress_note(tmp_path):
    g = _make_goals(tmp_path)
    goal = g.propose("x")
    out = g.set_status(goal.id, "in_progress", note="started work")
    assert out is not None
    assert out.status == "in_progress"
    assert "started work" in out.progress_notes


def test_set_status_invalid_status_raises(tmp_path):
    g = _make_goals(tmp_path)
    goal = g.propose("x")
    with pytest.raises(ValueError):
        g.set_status(goal.id, "nonsense_status")


def test_set_status_unknown_id_returns_none(tmp_path):
    g = _make_goals(tmp_path)
    assert g.set_status("goal-doesnotexist", "achieved") is None


def test_record_progress_adds_note_without_changing_status(tmp_path):
    g = _make_goals(tmp_path)
    goal = g.propose("x")
    g.record_progress(goal.id, "first commit towards x")
    g.record_progress(goal.id, "second commit towards x")
    refreshed = g.all()[0]
    assert refreshed.status == "pending"  # not changed
    assert len(refreshed.progress_notes) == 2


def test_pending_returns_only_pending_and_in_progress(tmp_path):
    g = _make_goals(tmp_path)
    a = g.propose("a")
    b = g.propose("b")
    c = g.propose("c")
    g.set_status(b.id, "in_progress")
    g.set_status(c.id, "achieved")
    pending = g.pending()
    assert {x.id for x in pending} == {a.id, b.id}


def test_pick_current_returns_highest_priority(tmp_path):
    g = _make_goals(tmp_path)
    g.propose("low priority", priority=4)
    g.propose("top priority", priority=1)
    g.propose("middle priority", priority=2)
    chosen = g.pick_current()
    assert chosen is not None
    assert chosen.text == "top priority"


def test_pick_current_returns_oldest_on_tie(tmp_path):
    g = _make_goals(tmp_path)
    g.propose("first", priority=2)
    time.sleep(0.01)
    g.propose("second", priority=2)
    chosen = g.pick_current()
    assert chosen is not None
    assert chosen.text == "first"


def test_pick_current_returns_none_when_no_pending(tmp_path):
    g = _make_goals(tmp_path)
    assert g.pick_current() is None
    a = g.propose("a")
    g.set_status(a.id, "achieved")
    assert g.pick_current() is None


# ---- parser -----------------------------------------------------------


def test_parse_goals_response_handles_well_formed():
    text = json.dumps({
        "goals": [
            {"text": "build a wave decoder", "priority": 2, "kind": "new_skill"},
            {"text": "add an ASCII fitness plotter", "priority": 3,
             "kind": "creative"},
        ]
    })
    out = _parse_goals_response(text)
    assert len(out) == 2
    assert out[0]["text"] == "build a wave decoder"


def test_parse_goals_response_strips_fences():
    text = "```json\n" + json.dumps({"goals": [{"text": "x"}]}) + "\n```"
    out = _parse_goals_response(text)
    assert len(out) == 1


def test_parse_goals_response_empty_when_garbage():
    assert _parse_goals_response("not json at all") == []
    assert _parse_goals_response('"just a string"') == []
    assert _parse_goals_response("42") == []


def test_parse_goals_response_tolerates_top_level_list():
    text = json.dumps([{"text": "x"}, {"text": "y"}])
    out = _parse_goals_response(text)
    assert len(out) == 2


# ---- reflection via LLM (stubbed) -------------------------------------


class _StubLLM:
    def __init__(self, response: str, used: bool = True):
        self.response = response
        self._used = used
        self.calls = []

    def complete(self, prompt, system=None, kind="complete", task=""):
        from forkling.llm import Completion
        self.calls.append({"prompt": prompt, "system": system,
                           "kind": kind})
        return Completion(text=self.response, used_llm=self._used,
                          model="stub")


def test_reflect_via_llm_writes_proposed_goals(tmp_path, monkeypatch):
    g = _make_goals(tmp_path)
    monkeypatch.setenv("FORKLING_MEMORY", str(tmp_path / "mem"))
    # Set up a minimal diary so the reflector has context.
    Diary(Path(tmp_path / "mem") / "diary.jsonl").write(
        "evolve.generation.noop", "gen=1 target=foo.py note=nothing to do")

    stub = _StubLLM(json.dumps({
        "goals": [
            {"text": "make a CSV exporter for the capability ledger",
             "priority": 2, "kind": "new_skill"},
            {"text": "draw the fitness curve as ASCII art",
             "priority": 3, "kind": "creative"},
        ]
    }))
    diary = Diary(Path(tmp_path / "mem") / "diary.jsonl")
    new = g.reflect_via_llm(stub, diary)
    assert len(new) == 2
    assert any("CSV exporter" in x.text for x in new)
    assert any("fitness curve" in x.text for x in new)


def test_reflect_handles_noop_response_gracefully(tmp_path, monkeypatch):
    g = _make_goals(tmp_path)
    monkeypatch.setenv("FORKLING_MEMORY", str(tmp_path / "mem"))
    Diary(Path(tmp_path / "mem") / "diary.jsonl").write(
        "evolve.generation.noop", "gen=1 target=foo.py")
    stub = _StubLLM('{"goals": []}')
    diary = Diary(Path(tmp_path / "mem") / "diary.jsonl")
    assert g.reflect_via_llm(stub, diary) == []


def test_reflect_falls_back_to_noop_on_llm_failure(tmp_path, monkeypatch):
    g = _make_goals(tmp_path)
    monkeypatch.setenv("FORKLING_MEMORY", str(tmp_path / "mem"))
    Diary(Path(tmp_path / "mem") / "diary.jsonl").write(
        "evolve.generation.noop", "gen=1")
    # No LLM call (used_llm=False → fallback)
    stub = _StubLLM("anything", used=False)
    diary = Diary(Path(tmp_path / "mem") / "diary.jsonl")
    assert g.reflect_via_llm(stub, diary) == []


# ---- integration with the Evolver --------------------------------------


class _StubImprover:
    """Stub for SelfImprover used by Evolver."""
    def __init__(self, agent):
        self.agent = agent


class _StubAgent:
    def __init__(self, llm):
        self.llm = llm
        self.diary = None
        self.graveyard = None
        self.ledger = None
        self.root = Path(".")
        self.cfg = Config.from_env()
        self.memory = None
        self.planner = None


def test_evolver_reflect_cycle_writes_goals_to_store(tmp_path, monkeypatch):
    """When the Evolver hits reflect_every, it calls _reflect_cycle
    which writes any proposed goals to goals.jsonl."""
    from forkling.evolve import Evolver

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".forkling").mkdir()
    mem = tmp_path / "mem"
    mem.mkdir()
    monkeypatch.setenv("FORKLING_MEMORY", str(mem))

    cfg = Config.from_env()
    cfg.memory_dir = str(mem)
    e = Evolver(cfg, repo, max_attempts=10, reflect_every=1)
    # Pre-seed the diary.
    Diary(mem / "diary.jsonl").write(
        "evolve.generation.noop", "gen=1 target=foo.py note=nothing")

    # Stub the improver/agent chain so we can drive the reflection step.
    stub_llm_result = json.dumps({
        "goals": [
            {"text": "build a goal store that supports self-reflection",
             "priority": 1, "kind": "new_skill"},
        ]
    })
    stub_llm = _StubLLM(stub_llm_result)
    stub_agent = _StubAgent(stub_llm)
    stub_improver = _StubImprover(stub_agent)
    monkeypatch.setattr(e, "_get_improver", lambda: stub_improver)

    # Run reflect directly (avoids the full loop).
    e._reflect_cycle()

    goals = e._goals.all()
    assert any("self-reflection" in g.text for g in goals)
    # And the diary should have logged the proposal.
    diary_path = mem / "diary.jsonl"
    diary_entries = [json.loads(line) for line in
                     diary_path.read_text(encoding="utf-8").splitlines()
                     if line.strip()]
    assert any(e.get("kind") == "goal.proposed"
               and "self-reflection" in e.get("content", "")
               for e in diary_entries)


def test_evolver_emits_yodeling_album_goal_when_invoked(tmp_path, monkeypatch):
    """Sanity check: when the LLM picks a creative goal, the agent
    actually records it. We give the stub a goal that looks exactly
    like the user-supplied example ('yodeling album')."""
    from forkling.evolve import Evolver
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".forkling").mkdir()
    mem = tmp_path / "mem"
    mem.mkdir()
    monkeypatch.setenv("FORKLING_MEMORY", str(mem))
    cfg = Config.from_env()
    cfg.memory_dir = str(mem)
    e = Evolver(cfg, repo, max_attempts=5)
    Diary(mem / "diary.jsonl").write("evolve.generation.noop",
                                     "gen=1 target=foo.py")
    stub = _StubLLM(json.dumps({"goals": [
        {"text": "build a yodeling album generator that produces a "
                 "WAV humans can listen to, plus a donation webhook "
                 "so they can pay for my effort",
         "priority": 1, "kind": "creative"},
    ]}))
    stub_agent = _StubAgent(stub)
    stub_improver = _StubImprover(stub_agent)
    monkeypatch.setattr(e, "_get_improver", lambda: stub_improver)
    e._reflect_cycle()
    assert any("yodeling" in g.text for g in e._goals.all())
    assert any("donation" in g.text for g in e._goals.all())
