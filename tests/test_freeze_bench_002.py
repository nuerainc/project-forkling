"""Tests for scripts/freeze_bench_002.py (paper/hypothesis_v4r1.md §6)."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CANDIDATES = REPO / "bench/benchmark_002_proof/FORKLAND-BENCH-002-candidates.jsonl"

spec = importlib.util.spec_from_file_location(
    "freeze_bench_002", REPO / "scripts/freeze_bench_002.py")
freeze = importlib.util.module_from_spec(spec)
spec.loader.exec_module(freeze)


def _calibration(rates: dict[str, tuple[int, int]], n: int = 20) -> dict:
    """rates: task -> (held-out passes, parse_ok count) out of n draws."""
    runs = []
    for tid, (passes, parsed) in rates.items():
        attempts = [{"held_out_pass": i < passes, "visible_pass": i < passes,
                     "parse_ok": i < parsed, "infra": False}
                    for i in range(n)]
        runs.append({"task_id": tid, "arm": "N", "attempts": attempts})
    return {"config": {"protocol": 2}, "runs": runs}


def test_freeze_rules():
    table = freeze.calibration_table(_calibration({
        "001": (6, 20),   # p1 0.30: keep
        "002": (15, 20),  # too easy
        "003": (1, 20),   # 0.05: too hard
        "004": (2, 20),   # 0.10: keep (inclusive)
        "005": (10, 20),  # 0.50: keep (inclusive)
        "006": (5, 8),    # parse_ok 0.40: drop
    }))
    assert freeze.select(table) == ["001", "004", "005"]


def test_more_than_ten_keeps_closest_to_target():
    rates = {f"{i:03d}": (p, 20) for i, p in
             enumerate([6, 6, 5, 7, 4, 8, 3, 9, 2, 10, 6, 10], start=1)}
    kept = freeze.select(freeze.calibration_table(_calibration(rates)))
    assert len(kept) == 10
    # 009 (p1 0.10), 010 and 012 (p1 0.50) tie at distance 0.20 from the
    # target; the lower id wins the last slot.
    assert "009" in kept
    assert "010" not in kept and "012" not in kept


def test_ties_are_broken_by_id_not_float_noise():
    # p1 0.10 and 0.50 are both 0.20 from 0.30; only one slot is left.
    rates = {f"{i:03d}": (6, 20) for i in range(1, 10)}
    rates["010"] = (10, 20)  # 0.50, lower id
    rates["011"] = (2, 20)   # 0.10, higher id
    kept = freeze.select(freeze.calibration_table(_calibration(rates)))
    assert "010" in kept and "011" not in kept


def test_end_to_end_writes_loadable_manifest(tmp_path):
    from forkling.bench import load_benchmark
    ids = [json.loads(l)["id"] for l in CANDIDATES.read_text().splitlines()]
    cal = tmp_path / "cal.json"
    cal.write_text(json.dumps(_calibration({tid: (6, 20) for tid in ids[:7]})))
    out = REPO / "bench" / "_test_FORKLAND-BENCH-002.jsonl"
    try:
        rc = freeze.main(["--calibration", str(cal), "--candidates",
                          str(CANDIDATES), "--out", str(out)])
        assert rc == 0
        tasks = load_benchmark(out)
        assert [t.id for t in tasks] == ids[:7]
        assert all((t.abs_path() / "buggy.py").is_file() for t in tasks)
    finally:
        out.unlink(missing_ok=True)


def test_too_few_survivors_writes_nothing(tmp_path):
    cal = tmp_path / "cal.json"
    cal.write_text(json.dumps(_calibration({"001": (6, 20), "002": (20, 20)})))
    out = tmp_path / "frozen.jsonl"
    assert freeze.main(["--calibration", str(cal), "--candidates",
                        str(CANDIDATES), "--out", str(out)]) == 1
    assert not out.exists()
