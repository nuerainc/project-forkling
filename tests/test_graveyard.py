"""Tests for the patch graveyard."""

from __future__ import annotations

from forkling.graveyard import Graveyard


def test_record_and_retrieve(tmp_path):
    g = Graveyard(tmp_path / "grave.jsonl")
    g.record(path="a.py", old="x", new="y", reason="not unique", source="validate")
    assert len(g.entries()) == 1
    assert g.entries()[0]["path"] == "a.py"


def test_recent_truncates(tmp_path):
    g = Graveyard(tmp_path / "grave.jsonl")
    for i in range(20):
        g.record(path=f"f{i}.py", old=str(i), new="x", reason=f"reason {i}")
    assert len(g.recent(5)) == 5
    assert g.recent(5)[-1]["reason"] == "reason 19"


def test_prompt_excerpt_is_safe_for_empty(tmp_path):
    g = Graveyard(tmp_path / "grave.jsonl")
    assert g.as_prompt_excerpt() == ""


def test_prompt_excerpt_format(tmp_path):
    g = Graveyard(tmp_path / "grave.jsonl")
    g.record(path="a.py", old="x", new="y", reason="not unique", source="validate")
    g.record(path="b.py", old="m", new="n", reason="empty patch", source="validate")
    excerpt = g.as_prompt_excerpt()
    assert "Recent rejected" in excerpt
    assert "a.py" in excerpt and "b.py" in excerpt


def test_stats_aggregate(tmp_path):
    g = Graveyard(tmp_path / "grave.jsonl")
    g.record(path="a.py", old="x", new="y", reason="not unique", source="validate")
    g.record(path="a.py", old="p", new="q", reason="not unique", source="validate")
    g.record(path="b.py", old="m", new="n", reason="empty patch", source="llm")
    stats = g.stats()
    assert stats["total"] == 3
    assert stats["by_path"]["a.py"] == 2
    assert stats["by_source"]["validate"] == 2