"""Tests for the evolution (fitness + A/B lineages) module."""

from __future__ import annotations

from forkling.capability import CapabilityLedger
from forkling.evolution import Evolution
from forkling.graveyard import Graveyard


def _empty_evo(tmp_path) -> Evolution:
    return Evolution(
        CapabilityLedger(tmp_path / "cap.jsonl"),
        Graveyard(tmp_path / "grave.jsonl"),
        tmp_path,
    )


def test_empty_fitness_is_zero(tmp_path):
    evo = _empty_evo(tmp_path)
    fit = evo.fitness()
    assert fit.total == 0.0
    assert fit.distinct_actions == 0
    assert fit.file_diversity == 0.0


def test_fitness_grows_with_capabilities(tmp_path):
    evo = _empty_evo(tmp_path)
    # Add 5 successful reads on 5 different files + 1 patch accepted + 1 test pass.
    for i in range(5):
        evo.ledger.record(action="read", target=f"f{i}.py", ok=True)
    evo.ledger.record(action="patch", target="f0.py", ok=True)
    evo.ledger.record(action="test", target="pytest", ok=True)
    fit = evo.fitness()
    assert fit.smartness > 0.0
    assert fit.skill > 0.0
    assert fit.distinct_actions >= 2


def test_graveyard_reduces_acceptance_rate(tmp_path):
    evo = _empty_evo(tmp_path)
    evo.ledger.record(action="patch", target="a.py", ok=True)
    for _ in range(10):
        evo.graveyard.record(path="a.py", old="x", new="y", reason="rejected")
    fit = evo.fitness()
    # Acceptance should be low (1 / (1+10)).
    assert fit.acceptance_rate < 0.15


def test_shannon_normalization(tmp_path):
    # All on one file -> entropy = 0 / 1 = 0
    evo = _empty_evo(tmp_path)
    for _ in range(5):
        evo.ledger.record(action="read", target="only.py", ok=True)
    assert evo.fitness().file_diversity == 0.0

    # Spread across many files -> diversity should be > 0.5
    evo2 = _empty_evo(tmp_path)
    for i in range(10):
        evo2.ledger.record(action="read", target=f"f{i}.py", ok=True)
    assert evo2.fitness().file_diversity > 0.5


def test_fitness_history_formatter():
    from forkling.evolution import Fitness, format_fitness_history
    history = [
        Fitness(smartness=0.1, skill=0.2, acceptance_rate=0.1,
                test_pass_rate=0.1, distinct_actions=2, file_diversity=0.2),
        Fitness(smartness=0.3, skill=0.4, acceptance_rate=0.3,
                test_pass_rate=0.3, distinct_actions=3, file_diversity=0.4),
    ]
    out = format_fitness_history(history)
    assert "gen" in out and ("1" in out) and ("2" in out)
    assert "0.200" in out and "0.350" in out