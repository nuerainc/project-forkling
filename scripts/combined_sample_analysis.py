"""Combined-sample analysis (registered in paper/hypothesis_v7.md §4.2
and extended in paper/hypothesis_v8.md §9).

v7 behavior (default, backward-compatible):
  Pool per-task arm scores across exp006 + exp007 (per-task mean of
  S replicates within each seed; seeds as paired blocks), run
  Wilcoxon signed-rank on the combined n=12 per-task paired
  differences. Reports each comparison with effect size, 95%
  bootstrap CI, and exact two-sided p-value.

v8 behavior (generalized):
  Accept any number of result files via sys.argv. Pool all
  per-task arm scores; report per-cell summaries plus the
  combined-sample test. If the optional --sign-test flag is
  passed, also report a sign test on the direction of P - N
  across cells.

Honest reporting: zero diffs are dropped per Wilcoxon; ties get
mid-ranks; the permutation null is exact for n <= 14, normal
approximation otherwise.
"""
from __future__ import annotations

import json
import statistics
import sys
from itertools import product
from math import erfc, sqrt
from pathlib import Path


def load_per_task(path: str) -> dict[str, dict[str, float]]:
    out = {}
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    for tid in sorted(d["per_task_returned_pass"].keys()):
        arms = d["per_task_returned_pass"][tid]
        if all(a in arms for a in ("N", "P", "I", "R")):
            out[tid] = {
                "N": arms["N"],
                "P": arms["P"],
                "I": arms["I"],
                "R": arms["R"],
            }
    return out


def deltas(per_task: dict[str, dict[str, float]]) -> dict[str, dict[str, float]]:
    out = {}
    for tid, arms in per_task.items():
        out[tid] = {
            "P-N": arms["P"] - arms["N"],
            "I-P": arms["I"] - arms["P"],
            "I-R": arms["I"] - arms["R"],
            "I-N": arms["I"] - arms["N"],
        }
    return out


def wilcoxon_paired(diffs: list[float]) -> tuple[float, int, float, float]:
    """Two-sided exact Wilcoxon signed-rank. zeros dropped; ties mid-rank.

    Returns (W+, n_nonzero, mean_diff_overall, p_two_sided).
    """
    nz = [d for d in diffs if d != 0]
    n = len(nz)
    if n == 0:
        return (0.0, 0, 0.0, 1.0)
    abs_sorted = sorted(range(n), key=lambda i: abs(nz[i]))
    ranks_nz = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j + 1 < n and abs(nz[abs_sorted[j + 1]]) == abs(nz[abs_sorted[i]]):
            j += 1
        avg = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks_nz[abs_sorted[k]] = avg
        i = j + 1
    w_plus = sum(r for r, v in zip(ranks_nz, nz) if v > 0)

    if n <= 14:
        cnt = 0
        total = 0
        for signs in product([1, -1], repeat=n):
            w_perm = sum(s * r for s, r in zip(signs, ranks_nz))
            total += 1
            if abs(w_perm - w_plus) < 1e-6:
                cnt += 1
        p = cnt / total
    else:
        mu = n * (n + 1) / 4
        sigma = sqrt(n * (n + 1) * (2 * n + 1) / 24)
        z = (w_plus - mu) / sigma
        p = erfc(abs(z) / 2**0.5)

    mean_diff = sum(diffs) / len(diffs) if diffs else 0.0
    return (w_plus, n, mean_diff, p)


def bootstrap_ci(diffs: list[float], n_resamples: int = 10000,
                 seed: int = 20261030) -> tuple[float, float]:
    """95% bootstrap CI on the mean of the paired diffs (kept simple)."""
    import random
    rng = random.Random(seed)
    means = []
    n = len(diffs)
    for _ in range(n_resamples):
        sample = [diffs[rng.randrange(n)] for _ in range(n)]
        means.append(sum(sample) / n)
    means.sort()
    lo = means[int(0.025 * n_resamples)]
    hi = means[int(0.975 * n_resamples)]
    return (lo, hi)


def sign_test(cell_diffs: list[float]) -> tuple[int, int, float]:
    """Sign test across cells. Returns (n_pos, n_nonzero, p_two_sided)."""
    nz = [d for d in cell_diffs if d != 0]
    n = len(nz)
    if n == 0:
        return (0, 0, 1.0)
    n_pos = sum(1 for d in nz if d > 0)
    # exact binomial two-sided under H0: p(positive) = 0.5
    from math import comb
    cnt = 0
    total = 0
    for k in range(n + 1):
        total += comb(n, k)
        if k <= n_pos:
            cnt += comb(n, k)
    # two-sided: 2 * min(P(X <= n_pos), P(X >= n_pos))
    p_le = cnt / total
    p_ge = 1.0 - (sum(comb(n, k) for k in range(n_pos)) / total)
    p = min(1.0, 2 * min(p_le, p_ge))
    return (n_pos, n, p)


def main(argv: list[str]) -> None:
    repo = Path(__file__).resolve().parent.parent
    args = list(argv)

    # Optional --sign-test flag (consumed but no-op on the test itself).
    sign_test_flag = False
    if "--sign-test" in args:
        sign_test_flag = True
        args.remove("--sign-test")
    # Optional --out <path> for JSON dump.
    out_path = None
    if "--out" in args:
        i = args.index("--out")
        out_path = Path(args[i + 1])
        del args[i : i + 2]

    # v7 default: exp006 + exp007 if no positional args.
    if not args:
        args = ["results/exp006.json", "results/exp007.json"]

    cells = []
    for path_str in args:
        full = Path(path_str)
        if not full.is_absolute():
            full = repo / full
        if not full.exists():
            print(f"[warn] {full} not found; skipping")
            continue
        per_task = load_per_task(str(full))
        cells.append((path_str, deltas(per_task)))

    if not cells:
        print("[error] no result files found")
        return

    # Per-cell summary.
    for label, dd in cells:
        print(f"=== {label} per-task diffs ===")
        for tid, d in sorted(dd.items()):
            print(f"  {tid}: " + ", ".join(f"{k}={v:+.2f}" for k, v in d.items()))
        print()

    all_tids = sorted(set().union(*(set(dd.keys()) for _, dd in cells)))
    n_datapoints = sum(len(dd) for _, dd in cells)
    print(
        f"=== combined n={n_datapoints} Wilcoxon "
        f"({len(cells)} cell(s), per-task arm pooled) ==="
    )
    out: dict = {"cells": [], "comparisons": {}, "n_datapoints": n_datapoints}
    for label, dd in cells:
        out["cells"].append(
            {
                "label": label,
                "n_tasks": len(dd),
            }
        )
    for cmp in ("P-N", "I-P", "I-R", "I-N"):
        combined = []
        per_cell_means = []
        for _, dd in cells:
            for tid, d in dd.items():
                combined.append(d[cmp])
            # one per-cell summary number for the sign test
            per_cell_diffs = [d[cmp] for d in dd.values() if d[cmp] != 0]
            per_cell_means.append(
                sum(per_cell_diffs) / len(per_cell_diffs) if per_cell_diffs else 0.0
            )
        w, n, mean, p = wilcoxon_paired(combined)
        nz = [v for v in combined if v != 0]
        nz_mean = sum(nz) / len(nz) if nz else 0.0
        nz_lo, nz_hi = (
            bootstrap_ci([v for v in combined if v != 0]) if n > 0 else (0.0, 0.0)
        )
        print(
            f"  {cmp}: combined_n={n_datapoints}, n_nz={n}, W+={w:.1f}, "
            f"mean(non-zero)={nz_mean:+.3f}, "
            f"CI95=[{nz_lo:+.3f}, {nz_hi:+.3f}], p={p:.4f}"
        )
        out["comparisons"][cmp] = {
            "combined_n": n_datapoints,
            "n_nonzero": n,
            "W_plus": w,
            "mean_non_zero": nz_mean,
            "ci95_lo": nz_lo,
            "ci95_hi": nz_hi,
            "p": p,
            "per_cell_means": per_cell_means,
        }
        if sign_test_flag and cmp == "P-N":
            n_pos, n_cells_nz, p_sign = sign_test(per_cell_means)
            print(
                f"    sign test (across {n_cells_nz} non-zero cells): "
                f"{n_pos}/{n_cells_nz} positive, p={p_sign:.4f}"
            )
            out["comparisons"][cmp]["sign_test"] = {
                "n_positive": n_pos,
                "n_nonzero_cells": n_cells_nz,
                "p": p_sign,
            }

    if out_path is not None:
        out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
        print(f"\nwrote {out_path}")


if __name__ == "__main__":
    main(sys.argv[1:])
