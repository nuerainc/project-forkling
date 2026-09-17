"""Tests for the grant hunter and the chat diary."""

from __future__ import annotations

import json

from forkling.diary import Diary
from forkling.grants import ProjectProfile, draft, load_db, match


def test_grants_db_loads(tmp_path):
    db = [
        {"name": "Test Fund", "sponsor": "TestOrg", "url": "https://example.com",
         "typical_amount": "$1,000", "typical_amount_usd": 1000, "deadline": "rolling",
         "requires": ["open-source", "ai"], "stages": ["early"],
         "focus": ["AI"], "open_source": True},
    ]
    p = tmp_path / "grants.json"
    p.write_text(json.dumps(db), encoding="utf-8")
    loaded = load_db(p)
    assert len(loaded) == 1
    assert loaded[0]["name"] == "Test Fund"


def test_match_scores_by_tags(tmp_path):
    db = [
        {"name": "Open AI Fund", "url": "x", "typical_amount": "$5k",
         "typical_amount_usd": 5000, "requires": ["open-source", "ai"],
         "stages": ["early"], "focus": ["AI"], "open_source": True},
        {"name": "Closed Lab Grant", "url": "x", "typical_amount": "$10k",
         "typical_amount_usd": 10000, "requires": ["closed"], "stages": ["growth"],
         "focus": ["labs"], "open_source": False},
    ]
    p = tmp_path / "grants.json"
    p.write_text(json.dumps(db), encoding="utf-8")
    profile = ProjectProfile()
    ranked = match(profile, db_path=p)
    assert ranked[0]["name"] == "Open AI Fund"
    assert ranked[0]["_fit"] > ranked[1]["_fit"]


def test_draft_contains_keyword(tmp_path):
    grant = {"name": "Test Fund", "sponsor": "TestOrg", "focus": ["AI for good"]}
    text = draft(grant)
    assert "Test Fund" in text
    assert "AI for good" in text or "forkling" in text


def test_diary_writes_and_reads(tmp_path):
    d = Diary(tmp_path / "diary.jsonl")
    d.write("run.start", "task=hello", task="hello")
    d.write("milestone", "shipped self-improvement", milestone=True)
    assert len(d.entries()) == 2
    assert len(d.milestones()) == 1
    assert d.tail(1)[0]["kind"] == "milestone"


def test_diary_stats(tmp_path):
    d = Diary(tmp_path / "diary.jsonl")
    d.write("run.start", "a")
    d.write("run.start", "b")
    d.write("self-improve.start", "c")
    stats = d.stats()
    assert stats["total"] == 3
    assert stats["by_kind"]["run.start"] == 2
    assert stats["by_kind"]["self-improve.start"] == 1