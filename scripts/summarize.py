"""Summarize any results/exp*.json produced by `forkling experiment run`.

Protocol-2 files (exp003b onward; ``config.protocol == 2``) already carry
per-task returned-pass rates and paired statistics; those are printed
as recorded. The rest of this docstring is about protocol-1 files.

Usage:
    python scripts/summarize.py results/exp003.json

Works for every experiment so far (exp001/exp002 arms A/B/C, exp003
arms N/P/I/R) because it recomputes everything from ``records`` keyed
by the arm letters that were actually run. It does not trust the
``metrics`` block: before exp004 that block was always keyed A/B/C,
so for exp003 it mislabels N/I/R and omits P.

Two kinds of numbers are printed:

- **pass@k** (pre-registered endpoint for exp001-exp003): 1 if any of
  the first k attempts passed held-out tests, whether or not the arm
  selected it.
- **returned-patch pass** (exploratory, not pre-registered): whether
  the patch the arm would actually hand back passes held-out tests.
  N/A: attempt 0. P: the re-ranker's winner. I/R/B/C: the last
  committed patch (the final state of the loop), or the unfixed
  buggy.py if nothing was committed.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

LOOP_ARMS = {"B", "C", "I", "R"}   # iterate on a running source
RERANK_ARMS = {"P"}                 # pick one winner after K draws


def pass_at_k(recs: list[dict], k: int) -> int:
    return int(any(r["held_out_pass"] for r in recs[:k]))


def returned_pass(arm: str, recs: list[dict]) -> int:
    if arm in RERANK_ARMS or arm in LOOP_ARMS:
        committed = [r for r in recs if r["committed"]]
        return int(bool(committed) and committed[-1]["held_out_pass"])
    return int(bool(recs) and recs[0]["held_out_pass"])


def summarize_protocol2(path: Path, d: dict) -> int:
    cfg = d["config"]
    arms = cfg["arms"]
    per_task = d["per_task_returned_pass"]
    print(f"=== {path.name} (protocol 2) ===")
    print(f"model: {cfg['model']}  k: {cfg['k_per_task']}  replicates: "
          f"{cfg['replicates']}  temperature: {cfg['temperature']}  "
          f"seed: {cfg['seed']}  harness: {cfg.get('harness_commit', '?')[:7]}")
    print("\n=== per-task returned-patch pass rate ===")
    print(f"{'task':>6} " + " ".join(f"{a:>5}" for a in arms))
    for tid in sorted(per_task):
        print(f"{tid:>6} " + " ".join(f"{per_task[tid][a]:>5.2f}" for a in arms))
    print("\n=== per-arm metrics ===")
    for arm, m in d["metrics"].items():
        print(f"  arm {arm}: returned={m['returned_pass']:.2f} "
              f"pass@1={m['pass_at_1']:.2f} pass@5={m['pass_at_5']:.2f} "
              f"parse_ok={m['parse_ok_rate']:.2f} kept={m['kept_rate']:.2f} "
              f"infra={m['infra_rate']:.2f} calls={m['mean_calls']:.1f}")
    print("\n=== paired Wilcoxon signed-rank over tasks (first = primary) ===")
    for name, st in d["stats"].items():
        print(f"  {name}: mean_diff={st['mean_diff']:+.3f} "
              f"CI95=[{st['ci95'][0]:+.3f}, {st['ci95'][1]:+.3f}] "
              f"W+={st['w_plus']:.1f} n={st['n']} p={st['p']:.4f}")
    return 0


def main(argv: list[str]) -> int:
    path = Path(argv[1] if len(argv) > 1 else "results/exp003.json")
    d = json.loads(path.read_text(encoding="utf-8"))
    cfg = d.get("config", {})
    if cfg.get("protocol") == 2:
        return summarize_protocol2(path, d)
    arms = list(d["records"])

    by_task: dict[str, dict[str, list[dict]]] = {}
    for arm in arms:
        for r in d["records"][arm]:
            by_task.setdefault(r["task_id"], {}).setdefault(arm, []).append(r)
    for per_arm in by_task.values():
        for recs in per_arm.values():
            recs.sort(key=lambda r: r["attempt_idx"])
    tasks = sorted(by_task)
    n = max(len(tasks), 1)

    print(f"=== {path.name} ===")
    print(f"model: {cfg.get('model', '?')}  k_per_task: {cfg.get('k_per_task', '?')}"
          f"  seed: {cfg.get('seed', '?')}  arms: {','.join(arms)}  tasks: {len(tasks)}")

    print("\n=== per-task pass@5 / returned-patch pass ===")
    print(f"{'task':>6} " + " ".join(f"{a:>5}" for a in arms))
    for tid in tasks:
        cells = []
        for arm in arms:
            recs = by_task[tid].get(arm, [])
            cells.append(f"{pass_at_k(recs, 5)}/{returned_pass(arm, recs)}")
        print(f"{tid:>6} " + " ".join(f"{c:>5}" for c in cells))

    print("\n=== per-arm metrics ===")
    for arm in arms:
        recs = d["records"][arm]
        per_task = [by_task[t].get(arm, []) for t in tasks]
        p1, p5, p10 = (sum(pass_at_k(x, k) for x in per_task) / n for k in (1, 5, 10))
        ret = sum(returned_pass(arm, x) for x in per_task) / n
        total = max(len(recs), 1)
        parse_ok = sum(r["parse_ok"] for r in recs) / total
        commit = sum(r["committed"] for r in recs) / total
        print(f"  arm {arm}: pass@1={p1:.2f} pass@5={p5:.2f} pass@10={p10:.2f} "
              f"returned={ret:.2f} parse_ok={parse_ok:.2f} commit={commit:.2f} "
              f"n={len(recs)}")

    k = int(cfg.get("k_per_task") or max(
        (r["attempt_idx"] + 1 for recs in d["records"].values() for r in recs),
        default=0))
    print("\n=== parse_ok by attempt index (summed over tasks) ===")
    for arm in arms:
        counts = [sum(1 for r in d["records"][arm]
                      if r["attempt_idx"] == i and r["parse_ok"]) for i in range(k)]
        print(f"  arm {arm}: {counts}")

    print("\n=== stats (as recorded by the harness) ===")
    for cmp, s in d.get("stats", {}).items():
        print(f"  {cmp}: U={s['u']:.2f} p={s['p']:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
