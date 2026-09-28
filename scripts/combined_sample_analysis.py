"""Combined-sample analysis for exp006 + exp007 (paper/methods_paper.md §4.2).

The methods paper's registered secondary step: pool per-task arm
scores across the two seeds (per-task mean of S replicates within
each seed; seeds as paired blocks), run Wilcoxon signed-rank on the
combined n=12 per-task paired differences. Reports each comparison
with effect size, 95% bootstrap CI, and exact two-sided p-value.

Honest reporting: zero diffs are dropped per Wilcoxon; ties get
mid-ranks; the permutation null is exact for n <= 14, normal
approximation otherwise.
"""
from __future__ import annotations

import json
import statistics
from itertools import combinations, product
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


def main() -> None:
    repo = Path(__file__).resolve().parent.parent
    d6 = deltas(load_per_task(repo / "results" / "exp006.json"))
    d7 = deltas(load_per_task(repo / "results" / "exp007.json"))

    print("=== exp006 (seed 20261025) per-task diffs ===")
    for tid, dd in sorted(d6.items()):
        print(f"  {tid}: " + ", ".join(f"{k}={v:+.2f}" for k, v in dd.items()))
    print()
    print("=== exp007 (seed 20261030) per-task diffs ===")
    for tid, dd in sorted(d7.items()):
        print(f"  {tid}: " + ", ".join(f"{k}={v:+.2f}" for k, v in dd.items()))

    all_tids = sorted(set(d6.keys()) | set(d7.keys()))
    print()
    print("=== combined n=12 Wilcoxon (per-task arm pooled across seeds) ===")
    for cmp in ("P-N", "I-P", "I-R", "I-N"):
        combined = []
        for tid in all_tids:
            if tid in d6:
                combined.append(d6[tid][cmp])
            if tid in d7:
                combined.append(d7[tid][cmp])
        w, n, mean, p = wilcoxon_paired(combined)
        nz = [v for v in combined if v != 0]
        nz_mean = sum(nz) / len(nz) if nz else 0.0
        nz_lo, nz_hi = (
            bootstrap_ci([v for v in combined if v != 0]) if n > 0 else (0.0, 0.0)
        )
        print(
            f"  {cmp}: combined={[round(d, 2) for d in combined]}, "
            f"n_nz={n}, W+={w:.1f}, mean(non-zero)={nz_mean:+.3f}, "
            f"CI95=[{nz_lo:+.3f}, {nz_hi:+.3f}], p={p:.4f}"
        )


if __name__ == "__main__":
    main()
