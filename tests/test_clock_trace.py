"""Tests for the project clock + LLM trace logger + dataset export.

These are the three new artifacts that ship with the 365-day cycle:
  - forkling/clock.py
  - forkling/trace.py
  - forkling/export-dataset  (CLI command, not a separate module)
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from forkling.clock import CYCLE_DAYS, Clock
from forkling.trace import Trace


# ---- clock -----------------------------------------------------------------


def test_clock_defaults_match_year_anchor():
    """The default t=0 anchor is 2026-09-16 21:00 MDT (= 2026-09-17 03:00 UTC)."""
    c = Clock.from_env(fork_name="forkling")
    assert c.fork_name == "forkling"
    assert c.t0_epoch > 0
    # Anchor year should be 2026
    import datetime as _dt
    iso = _dt.datetime.fromtimestamp(c.t0_epoch, tz=_dt.timezone.utc).isoformat()
    assert iso.startswith("2026-09-17T03:00:00")


def test_clock_env_override_t0_epoch(monkeypatch):
    monkeypatch.setenv("FORKLING_T0", "1700000000")  # 2023-11-14 UTC
    c = Clock.from_env()
    assert c.t0_epoch == 1700000000.0


def test_clock_env_override_t0_iso(monkeypatch):
    monkeypatch.delenv("FORKLING_T0", raising=False)
    monkeypatch.setenv("FORKLING_T0_ISO", "2027-01-01T00:00:00+00:00")
    c = Clock.from_env()
    import datetime as _dt
    iso = _dt.datetime.fromtimestamp(c.t0_epoch, tz=_dt.timezone.utc).isoformat()
    assert iso.startswith("2027-01-01T00:00:00")


def test_clock_day_index_and_stage():
    """Day index is 0 on t=0 day, 1 the day after, etc. Stage gate at day 7."""
    c = Clock(t0_epoch=1_000_000.0, fork_name="x")
    # Exactly t=0 -> day 0 (isolation)
    assert c.day_index(1_000_000.0) == 0
    assert c.stage(1_000_000.0) == "stage-0-isolation"
    # Day 6 -> still isolation
    assert c.day_index(1_000_000.0 + 6 * 86400) == 6
    assert c.stage(1_000_000.0 + 6 * 86400) == "stage-0-isolation"
    # Day 7 -> first-month
    assert c.day_index(1_000_000.0 + 7 * 86400) == 7
    assert c.stage(1_000_000.0 + 7 * 86400) == "stage-1-first-month"
    # Day 29 -> still first-month
    assert c.stage(1_000_000.0 + 29 * 86400) == "stage-1-first-month"
    # Day 30 -> baseline-arrives
    assert c.stage(1_000_000.0 + 30 * 86400) == "stage-2-baseline-arrives"
    # Day 365+ -> retrospective
    assert c.stage(1_000_000.0 + 365 * 86400) == "stage-7-retrospective"


def test_clock_progress_clamped():
    c = Clock(t0_epoch=1_000_000.0, fork_name="x")
    assert c.days_into_cycle(1_000_000.0) == 0
    assert c.days_into_cycle(1_000_000.0 + CYCLE_DAYS * 86400) == CYCLE_DAYS
    # Far past -> still clamped at 365
    assert c.days_into_cycle(1_000_000.0 + 1000 * 86400) == CYCLE_DAYS


def test_clock_save_and_load(tmp_path):
    c = Clock(t0_epoch=1_234_567.0, fork_name="Spoonica",
              note="baseline fork")
    path = tmp_path / "clock.json"
    c.save(path)
    assert path.exists()
    loaded = Clock.from_file(path)
    assert loaded.t0_epoch == 1_234_567.0
    assert loaded.fork_name == "Spoonica"
    assert loaded.note == "baseline fork"


def test_clock_as_dict_has_stage():
    c = Clock.from_env()
    d = c.as_dict()
    assert d["fork_name"] == "forkling"
    assert "stage" in d
    assert "cycle_progress" in d
    assert "day_index" in d


# ---- trace -----------------------------------------------------------------


def test_trace_record_and_stats(tmp_path):
    t = Trace(tmp_path / "trace.jsonl")
    t.record(kind="plan", prompt="hi", response="hello", model="qwen3:4b",
             used_llm=True, latency_ms=120, task="greet")
    t.record(kind="plan", prompt="bye", response="see ya", model="qwen3:4b",
             used_llm=True, latency_ms=80, task="bye")
    t.record(kind="inception.respond", prompt="...", response="ack",
             model="rule-based", used_llm=False, latency_ms=0, task="trg-001")
    stats = t.stats()
    assert stats["total"] == 3
    assert stats["used_llm"] == 2
    assert stats["fallback_used"] == 1
    assert stats["by_kind"]["plan"] == 2
    assert stats["by_kind"]["inception.respond"] == 1
    assert stats["by_model"]["qwen3:4b"] == 2
    assert stats["avg_latency_ms"] >= 0


def test_trace_chain_verifies(tmp_path):
    t = Trace(tmp_path / "trace.jsonl")
    for i in range(5):
        t.record(kind="plan", prompt=f"p{i}", response=f"r{i}",
                 model="m", used_llm=True, latency_ms=10 * i)
    ok, msg = t.verify()
    assert ok, msg
    assert "5 entries" in msg


def test_trace_chain_detects_tampering(tmp_path):
    t = Trace(tmp_path / "trace.jsonl")
    t.record(kind="plan", prompt="a", response="1", model="m",
             used_llm=True, latency_ms=10)
    t.record(kind="plan", prompt="b", response="2", model="m",
             used_llm=True, latency_ms=20)
    # Tamper with the first entry's response
    lines = (tmp_path / "trace.jsonl").read_text(encoding="utf-8").splitlines()
    obj = json.loads(lines[0])
    obj["response"] = "TAMPERED"
    lines[0] = json.dumps(obj)
    (tmp_path / "trace.jsonl").write_text("\n".join(lines) + "\n",
                                         encoding="utf-8")
    ok, msg = Trace(tmp_path / "trace.jsonl").verify()
    assert not ok
    assert "hash mismatch" in msg


def test_trace_entries_filter_by_kind(tmp_path):
    t = Trace(tmp_path / "trace.jsonl")
    t.record(kind="plan", prompt="p1", response="r1", model="m",
             used_llm=True, latency_ms=10)
    t.record(kind="improve.propose", prompt="p2", response="r2", model="m",
             used_llm=True, latency_ms=20)
    t.record(kind="plan", prompt="p3", response="r3", model="m",
             used_llm=True, latency_ms=30)
    plans = t.entries(kind="plan")
    assert len(plans) == 2
    improves = t.entries(kind="improve.propose")
    assert len(improves) == 1
    # Limit honored
    assert len(t.entries(kind="plan", limit=1)) == 1


# ---- LLM auto-trace wiring -------------------------------------------------


def test_llm_records_to_attached_trace(tmp_path):
    """When a Trace is attached, every complete() call logs an entry."""
    from forkling.llm import LLM
    trace = Trace(tmp_path / "trace.jsonl")
    llm = LLM(url="http://127.0.0.1:1", model="nope", timeout=1, trace=trace)
    llm.complete(prompt="hello", system=None, kind="plan", task="hi")
    # Rule-based fallback path should still write to the trace.
    assert trace.stats()["total"] == 1
    last = trace.entries(limit=1)[0]
    assert last["kind"] == "plan"
    assert last["used_llm"] is False
    assert last["task"] == "hi"
    assert last["prompt"] == "hello"


def test_llm_without_trace_does_not_break():
    """LLM without an attached trace still works (no file written)."""
    from forkling.llm import LLM
    llm = LLM(url="http://127.0.0.1:1", model="nope", timeout=1)
    c = llm.complete(prompt="hi")
    assert c.text  # rule-based fallback text
    assert not c.used_llm


# ---- CLI smoke tests -------------------------------------------------------


def test_clock_cli_runs(tmp_path, monkeypatch):
    monkeypatch.setenv("FORKLING_MEMORY", str(tmp_path / "mem"))
    from forkling.__main__ import main
    rc = main(["clock"])
    assert rc == 0


def test_clock_cli_save(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("FORKLING_MEMORY", str(tmp_path / "mem"))
    from forkling.__main__ import main
    rc = main(["clock", "--save", "--fork", "Spoonica"])
    assert rc == 0
    saved = tmp_path / "mem" / "clock.json"
    assert saved.exists()
    obj = json.loads(saved.read_text(encoding="utf-8"))
    assert obj["fork_name"] == "Spoonica"


def test_trace_cli_stats(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("FORKLING_MEMORY", str(tmp_path / "mem"))
    from forkling.__main__ import main
    rc = main(["trace", "stats"])
    assert rc == 0
    out = capsys.readouterr().out
    obj = json.loads(out)
    assert "total" in obj


def test_paper_publish_stages_file(tmp_path, monkeypatch):
    monkeypatch.setenv("FORKLING_MEMORY", str(tmp_path / "mem"))
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "paper").mkdir()
    (repo / "paper" / "paper.md").write_text("# rolling draft\n", encoding="utf-8")
    monkeypatch.setenv("FORKLING_REPO", str(repo))
    from forkling.__main__ import main
    rc = main(["paper", "publish", "day-30-first-month"])
    assert rc == 0
    staged = repo / "paper" / "papers" / "day-30-first-month.md"
    assert staged.exists()
    # `paper publish` first runs `paper update` (which regenerates from
    # the ledger/diary), then snapshots the result. So we assert the
    # snapshot landed at the expected path with non-empty content rather
    # than checking for the placeholder text.
    text = staged.read_text(encoding="utf-8")
    assert text.strip()
    assert len(text) > 100
    # Diary should have a paper.published milestone.
    diary_lines = (tmp_path / "mem" / "diary.jsonl").read_text(
        encoding="utf-8"
    ).splitlines()
    assert diary_lines, "diary should have at least one entry"
    diary = json.loads(diary_lines[0])
    assert diary["kind"] == "paper.published"
    assert diary["milestone"] is True
    assert diary["stage"] == "day-30-first-month"


def test_export_dataset_writes_zip(tmp_path, monkeypatch):
    monkeypatch.setenv("FORKLING_MEMORY", str(tmp_path / "mem"))
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "paper").mkdir()
    # Seed diary so export has something to bundle.
    (tmp_path / "mem").mkdir(exist_ok=True)
    (tmp_path / "mem" / "diary.jsonl").write_text(
        json.dumps({"ts": time.time(), "kind": "milestone",
                    "content": "test", "milestone": True}) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("FORKLING_REPO", str(repo))
    from forkling.__main__ import main
    rc = main(["export-dataset"])
    assert rc == 0
    out = repo / "paper" / "datasets"
    zips = list(out.glob("forkling-dataset-*.zip"))
    assert len(zips) == 1
    # Confirm the zip is a real archive and contains README + manifest.
    import zipfile
    with zipfile.ZipFile(zips[0]) as zf:
        names = zf.namelist()
        assert any("manifest.json" in n for n in names)
        assert any("clock.json" in n for n in names)
        assert "README.md" in names