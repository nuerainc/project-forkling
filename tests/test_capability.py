"""Tests for the append-only capability ledger."""

from __future__ import annotations

from forkling.capability import CapabilityLedger


def test_record_appends_and_chains(tmp_path):
    ledger = CapabilityLedger(tmp_path / "cap.jsonl")
    s1 = ledger.record(action="read", target="a.py", ok=True, agent_sha="abc")
    s2 = ledger.record(action="patch", target="a.py", ok=True, agent_sha="abc")
    assert s1 != s2
    assert ledger.head == s2
    entries = ledger.entries()
    assert len(entries) == 2
    assert entries[1]["sha_prev"] == s1


def test_chain_verifies_clean(tmp_path):
    ledger = CapabilityLedger(tmp_path / "cap.jsonl")
    for i in range(20):
        ledger.record(action="test", target=f"t{i}.py", ok=(i % 2 == 0))
    ok, msg = ledger.verify()
    assert ok, msg


def test_chain_detects_tamper(tmp_path):
    ledger = CapabilityLedger(tmp_path / "cap.jsonl")
    ledger.record(action="read", target="a", ok=True)
    ledger.record(action="read", target="b", ok=True)
    # Tamper: rewrite the file with one entry's content altered.
    text = (tmp_path / "cap.jsonl").read_text(encoding="utf-8")
    lines = text.splitlines()
    lines[0] = lines[0].replace('"a"', '"HACKED"')
    (tmp_path / "cap.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    # Build a fresh ledger reading the tampered file.
    ledger2 = CapabilityLedger(tmp_path / "cap.jsonl")
    ok, msg = ledger2.verify()
    assert not ok
    assert "mismatch" in msg or "break" in msg


def test_distinct_actions_and_targets(tmp_path):
    ledger = CapabilityLedger(tmp_path / "cap.jsonl")
    ledger.record(action="read", target="a.py", ok=True)
    ledger.record(action="read", target="b.py", ok=True)
    ledger.record(action="patch", target="a.py", ok=True)
    ledger.record(action="patch", target="a.py", ok=False)  # failure, not counted
    assert ledger.distinct_actions() == {"read", "patch"}
    assert ledger.distinct_targets() == {"a.py", "b.py"}


def test_empty_ledger_verifies(tmp_path):
    ledger = CapabilityLedger(tmp_path / "cap.jsonl")
    ok, msg = ledger.verify()
    assert ok