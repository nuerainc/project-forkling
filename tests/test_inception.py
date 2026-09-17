"""Tests for the inception trigger mechanism (fragments, interruptive)."""

from __future__ import annotations

import json

import pytest

from forkling.inception import MIN_WORDS, Inception, _word_count


def test_word_count_simple():
    assert _word_count("one two three") == 3
    assert _word_count("one, two; three!") == 3
    assert _word_count("") == 0


def test_no_folder_means_baseline(tmp_path):
    inc = Inception(tmp_path)
    assert inc.exists() is False
    assert inc.list() == []
    assert inc.ambient_block() == ""


def test_plant_writes_json_file(tmp_path):
    inc = Inception(tmp_path)
    thought = "im just walking down the street and bang whats that"
    t = inc.plant(thought, tags=["intrusive"], planted_by="test")
    assert t.id == "trg-001"
    assert (tmp_path / "inception_triggers" / "trg-001.json").exists()
    assert "intrusive" in t.tags


def test_plant_accepts_fragments(tmp_path):
    inc = Inception(tmp_path)
    fragments = [
        "haha thats wild, no way, no chance",
        "wait what was that over there",
        "huh what was that",
        "i should be focusing",
        "the wind is loud today",
    ]
    for f in fragments:
        t = inc.plant(f, planted_by="test")
        assert t.id.startswith("trg-")


def test_plant_rejects_too_short(tmp_path):
    inc = Inception(tmp_path)
    with pytest.raises(ValueError, match=">= 3 words"):
        inc.plant("huh no", planted_by="test")
    with pytest.raises(ValueError, match=">= 3 words"):
        inc.plant("", planted_by="test")


def test_plant_creates_multiple_ids(tmp_path):
    inc = Inception(tmp_path)
    inc.plant("im walking down the street and something is off", planted_by="a")
    inc.plant("haha thats wild, no way, no chance", planted_by="b")
    inc.plant("wait what was that", planted_by="c")
    ids = [t.id for t in inc.list()]
    assert ids == ["trg-001", "trg-002", "trg-003"]


def test_validate_dict_payload(tmp_path):
    inc = Inception(tmp_path)
    ok, msg = inc.validate({"id": "trg-001",
                            "thought": "haha thats wild no way"})
    assert ok
    ok, msg = inc.validate({"id": "trg-002", "thought": "huh"})
    assert not ok
    assert ">= 3" in msg


def test_ambient_block_has_no_header(tmp_path):
    inc = Inception(tmp_path)
    inc.plant("im just walking down the street and bang whats that",
              planted_by="test", tags=["nature"])
    inc.plant("haha thats wild, no way, no chance",
              planted_by="test", tags=["reaction"])
    block = inc.ambient_block()
    # No label / header — fragments, raw.
    assert "Trigger" not in block
    assert "Seed" not in block
    assert "thought" not in block.lower()
    # Both fragments present.
    assert "walking" in block
    assert "wild" in block


def test_remove_trigger(tmp_path):
    inc = Inception(tmp_path)
    inc.plant("im just walking down the street and bang whats that",
              planted_by="test")
    assert inc.remove("trg-001") is True
    assert inc.list() == []
    assert inc.remove("trg-001") is False


def test_loaded_from_disk(tmp_path):
    inc = Inception(tmp_path)
    inc.plant("im just walking down the street and bang whats that",
              planted_by="test")
    inc2 = Inception(tmp_path)
    assert len(inc2.list()) == 1
    assert "walking" in inc2.ambient_block()


def test_malformed_files_are_skipped(tmp_path):
    import os
    inc = Inception(tmp_path)
    inc.plant("im just walking down the street and bang whats that",
              planted_by="good")
    (tmp_path / "inception_triggers" / "bad.json").write_text("{not json")
    loaded = inc.list()
    assert len(loaded) == 1
    assert loaded[0].id == "trg-001"


def test_realistic_examples_validate(tmp_path):
    """The kinds of fragments the user gave us."""
    inc = Inception(tmp_path)
    examples = [
        "im just walking down the street and bang whats that",
        "haha thats wild, no way, no chance",
        "wait what was that over there",
        "huh did you see that",
        "i should be focusing on the task",
    ]
    for ex in examples:
        ok, msg = inc.validate({"id": "x", "thought": ex})
        assert ok, f"{ex!r} should validate: {msg}"