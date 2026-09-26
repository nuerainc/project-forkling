"""Freeze FORKLAND-BENCH-002 from the exp004 calibration run.

Implements paper/hypothesis_v4r1.md §6 mechanically, with no judgment:

    keep a candidate iff 0.10 <= p1 <= 0.50 and parse_ok_rate >= 0.5
    > 10 survivors: keep the 10 with p1 closest to 0.30 (ties: task id)
    < 6 survivors:  calibration failed; write nothing, exit 1

p1 is the fraction of calibration draws (arm N, protocol 2) whose patch
passes the held-out tests. Also reports vis_gap, the fraction of
visible-passing draws that fail held-out (reported, not a criterion).

Usage:
    python scripts/freeze_bench_002.py \
        [--calibration results/exp004_calibration.json] \
        [--candidates bench/benchmark_002_proof/FORKLAND-BENCH-002-candidates.jsonl] \
        [--out bench/FORKLAND-BENCH-002.jsonl]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

P1_MIN, P1_MAX, P1_TARGET = 0.10, 0.50, 0.30
PARSE_OK_MIN = 0.5
MAX_TASKS, MIN_TASKS = 10, 6


def calibration_table(calibration: dict) -> dict[str, dict[str, float]]:
    if calibration.get("config", {}).get("protocol") != 2:
        raise SystemExit("calibration file must come from --protocol 2")
    attempts: dict[str, list[dict]] = {}
    for run in calibration["runs"]:
        if run["arm"] != "N":
            continue
        attempts.setdefault(run["task_id"], []).extend(run["attempts"])
    table = {}
    for tid, atts in sorted(attempts.items()):
        n = len(atts)
        visible = [a for a in atts if a["visible_pass"]]
        table[tid] = {
            "n": n,
            "p1": sum(a["held_out_pass"] for a in atts) / n if n else 0.0,
            "parse_ok_rate": sum(a["parse_ok"] for a in atts) / n if n else 0.0,
            "infra_rate": sum(a["infra"] for a in atts) / n if n else 0.0,
            "vis_gap": (sum(not a["held_out_pass"] for a in visible) / len(visible)
                        if visible else 0.0),
        }
    return table


def select(table: dict[str, dict[str, float]]) -> list[str]:
    survivors = [tid for tid, row in table.items()
                 if P1_MIN <= row["p1"] <= P1_MAX
                 and row["parse_ok_rate"] >= PARSE_OK_MIN]
    # Round so float noise (0.3 - 0.1 != 0.5 - 0.3) cannot break ties;
    # true ties go to the lower task id.
    survivors.sort(key=lambda tid: (round(abs(table[tid]["p1"] - P1_TARGET), 9), tid))
    return sorted(survivors[:MAX_TASKS])


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--calibration", default="results/exp004_calibration.json")
    ap.add_argument("--candidates",
                    default="bench/benchmark_002_proof/FORKLAND-BENCH-002-candidates.jsonl")
    ap.add_argument("--out", default="bench/FORKLAND-BENCH-002.jsonl")
    args = ap.parse_args(argv)

    calibration = json.loads(Path(args.calibration).read_text(encoding="utf-8"))
    table = calibration_table(calibration)
    kept = select(table)

    print(f"{'task':>5} {'n':>3} {'p1':>5} {'parse_ok':>8} {'infra':>5} {'vis_gap':>7}  kept")
    for tid, row in table.items():
        print(f"{tid:>5} {row['n']:>3} {row['p1']:>5.2f} {row['parse_ok_rate']:>8.2f} "
              f"{row['infra_rate']:>5.2f} {row['vis_gap']:>7.2f}  "
              f"{'yes' if tid in kept else ''}")

    if len(kept) < MIN_TASKS:
        print(f"\n{len(kept)} task(s) survive (need >= {MIN_TASKS}). "
              "Benchmark calibration failed; primary question deferred. "
              "Nothing written.")
        return 1

    cand_path = Path(args.candidates)
    out_path = Path(args.out)
    candidates = [json.loads(line) for line in
                  cand_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    by_id = {c["id"]: c for c in candidates}
    missing = [tid for tid in kept if tid not in by_id]
    if missing:
        raise SystemExit(f"calibrated tasks not in candidates file: {missing}")
    # Task paths in the frozen manifest are relative to its own directory.
    rel = Path(os.path.relpath(cand_path.parent, out_path.parent))
    lines = []
    for tid in kept:
        entry = dict(by_id[tid])
        entry["path"] = (rel / entry["path"]).as_posix()
        lines.append(json.dumps(entry) + "\n")
    out_path.write_text("".join(lines), encoding="utf-8")
    print(f"\nFroze {len(kept)} tasks -> {out_path}: {', '.join(kept)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
