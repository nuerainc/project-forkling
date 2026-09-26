"""Tests for the Forkland & Family registry and the paper module."""

from __future__ import annotations

from pathlib import Path

from forkling.family import Family
from forkling.paper import render


def test_family_register_and_list(tmp_path):
    f = Family(tmp_path / "fam.json")
    f.register("Forkland", str(tmp_path / "forkling"), note="primary")
    f.register("Spoonica", str(tmp_path / "spoonica"), note="control")
    members = f.members()
    assert {m.name for m in members} == {"Forkland", "Spoonica"}


def test_family_register_replaces(tmp_path):
    f = Family(tmp_path / "fam.json")
    f.register("Forkland", str(tmp_path / "v1"))
    f.register("Forkland", str(tmp_path / "v2"))  # replaces
    members = f.members()
    assert len(members) == 1
    assert members[0].repo.endswith("v2")


def test_family_remove(tmp_path):
    f = Family(tmp_path / "fam.json")
    f.register("A", str(tmp_path))
    assert f.remove("A") is True
    assert f.remove("A") is False  # already gone


def test_family_persists_across_instances(tmp_path):
    f = Family(tmp_path / "fam.json")
    f.register("A", str(tmp_path))
    f2 = Family(tmp_path / "fam.json")
    assert f2.find("A") is not None


def test_family_sync_ledger_missing_member(tmp_path):
    f = Family(tmp_path / "fam.json")
    assert f.sync_ledger("Ghost") is None


def test_paper_render_uses_state(tmp_path):
    # Set up a small ledger + diary and render.
    from forkling.capability import CapabilityLedger
    from forkling.diary import Diary
    ledger = CapabilityLedger(tmp_path / "capabilities.jsonl")
    ledger.record(action="read", target="a.py", ok=True)
    diary = Diary(tmp_path / "diary.jsonl")
    diary.write("milestone", "shipped v0.2", milestone=True)
    text = render(tmp_path)
    assert "forkling" in text
    assert "capability" in text.lower()
    assert "1" in text  # one capability