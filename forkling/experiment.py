"""FORKLAND Experiment driver — three-arm comparison on FORKLAND-BENCH-001.

This is the implementation of the pre-registered hypothesis in
paper/hypothesis.md. **Read that file before changing this one.**

Arms:
  A: baseline        — one-shot generation. K independent draws per task.
  B: evolve + select — iterate, keep patches that pass visible tests.
  C: evolve + random — iterate, accept each patch with probability 0.5.

Each arm gets K attempts per task. For arm A, the K draws are
independent (no iteration). For arms B and C, the K attempts are
sequential — later attempts see the current state of the file.

Primary metric: mean pass@5 across the 10 tasks, per arm.

Statistical test (reported by --stats): paired Mann-Whitney U on
per-task pass@5, B vs A and B vs C.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import math
import random
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable

from .bench import BenchTask, GradeResult, grade, load_benchmark
from .llm import LLM


# ----- prompt construction -------------------------------------------------

PROMPT_TEMPLATE = """You are fixing a small Python function. Produce a JSON
patch with this exact shape:

{{"kind": "patch", "path": "buggy.py", "old": "<exact text to replace>",
 "new": "<replacement text>"}}

Or, if you want to replace the entire function:

{{"kind": "patch", "path": "buggy.py",
 "old": "<the whole current function body, signature + body>",
 "new": "<the whole new function body, signature + body>"}}

Respond with JSON only. No prose, no markdown fences.

Task description:
{prompt}

Current buggy.py:
```python
{buggy}
```

Visible tests (these MUST still pass after your fix):
```python
{visible_tests}
```

Constraints:
- Do NOT import anything outside the Python standard library.
- Do NOT change the function signature.
- Do NOT add new top-level definitions.
- Produce ONE patch.
"""


def build_prompt(task: BenchTask) -> str:
    ad = task.abs_path()
    buggy = (ad / "buggy.py").read_text(encoding="utf-8")
    visible = (ad / "visible_tests.py").read_text(encoding="utf-8")
    return PROMPT_TEMPLATE.format(
        prompt=task.prompt,
        buggy=buggy,
        visible_tests=visible,
    )


# ----- patch application ---------------------------------------------------

def apply_patch(source: str, old: str, new: str) -> str | None:
    """Apply a string replacement to source. Return None if old not found.

    Tries the strings as-given first; if that fails, tries to interpret
    any backslash-escaped sequences in `old` (so \\n becomes a literal
    newline, etc.). The LLM sometimes double-escapes newlines; this
    second pass makes the parser robust to that.
    """
    if old and old in source:
        return source.replace(old, new, 1)
    # Fallback: if old is empty (LLM returned full replacement), accept as-is.
    if not old:
        return new
    # Second try: unescape common sequences in `old`.
    try:
        unescaped = old.encode("utf-8").decode("unicode_escape")
        if unescaped in source:
            return source.replace(unescaped, new, 1)
    except UnicodeDecodeError:
        pass
    return None


def extract_patch(llm_output: str, fallback_source: str) -> tuple[str, str] | None:
    """Parse LLM JSON. Return (new_source, note) or None on parse failure.

    note is a short string for the diary: "ok", "parse_fail", "no_match".
    """
    text = llm_output.strip()
    # Strip optional markdown fences.
    if text.startswith("```"):
        m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if m:
            text = m.group(1)
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        # Try to find the first {...} block.
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if not m:
            return None
        try:
            obj = json.loads(m.group(0))
        except json.JSONDecodeError:
            return None

    if not isinstance(obj, dict):
        return None
    if obj.get("kind") != "patch":
        return None
    old = obj.get("old", "")
    new = obj.get("new", "")
    applied = apply_patch(fallback_source, old, new)
    if applied is None:
        return None
    return applied, "ok"


# ----- attempt loop --------------------------------------------------------

@dataclasses.dataclass
class AttemptRecord:
    task_id: str
    arm: str
    attempt_idx: int  # 0-indexed within (task, arm)
    committed: bool   # whether this arm accepted the patch (B keeps; C accepts 50%)
    visible_pass: bool
    held_out_pass: bool
    parse_ok: bool
    raw_response: str
    elapsed_s: float
    note: str = ""


def run_attempt(llm: LLM, task: BenchTask, attempt_idx: int,
                current_source: str, rng: random.Random
                ) -> tuple[AttemptRecord, str]:
    """Run ONE attempt. Return (record, new_source_if_changed).

    new_source_if_changed is the source to use for the NEXT attempt in
    iterate-mode arms. For arm A (one-shot), the caller does not use it.
    """
    prompt = build_prompt(task)
    t0 = time.monotonic()
    completion = llm.complete(prompt, kind="experiment", task=task.id)
    raw = completion.text
    elapsed = time.monotonic() - t0

    parsed = extract_patch(raw, current_source)
    if parsed is None:
        return AttemptRecord(
            task_id=task.id, arm="?", attempt_idx=attempt_idx,
            committed=False, visible_pass=False, held_out_pass=False,
            parse_ok=False, raw_response=raw, elapsed_s=elapsed,
            note="parse_fail",
        ), current_source

    new_source, _ = parsed
    result = grade(task, new_source)
    return AttemptRecord(
        task_id=task.id, arm="?", attempt_idx=attempt_idx,
        committed=False,  # set by caller based on arm policy
        visible_pass=result.visible_pass,
        held_out_pass=result.held_out_pass,
        parse_ok=True,
        raw_response=raw,
        elapsed_s=elapsed,
        note="" if not result.error else f"infra:{result.error[:80]}",
    ), new_source


# ----- per-arm logic -------------------------------------------------------

def arm_A_baseline(llm: LLM, task: BenchTask, k: int,
                   rng: random.Random) -> list[AttemptRecord]:
    """K independent one-shot draws. Each draws from a clean buggy.py."""
    recs: list[AttemptRecord] = []
    buggy = (task.abs_path() / "buggy.py").read_text(encoding="utf-8")
    for i in range(k):
        rec, _src = run_attempt(llm, task, i, buggy, rng)
        rec.arm = "A"
        rec.committed = True  # arm A has no policy; treat every parse as "kept"
        recs.append(rec)
    return recs


def arm_B_select(llm: LLM, task: BenchTask, k: int,
                 rng: random.Random) -> list[AttemptRecord]:
    """Iterate; keep the patch iff visible tests pass."""
    recs: list[AttemptRecord] = []
    current = (task.abs_path() / "buggy.py").read_text(encoding="utf-8")
    for i in range(k):
        rec, new_src = run_attempt(llm, task, i, current, rng)
        rec.arm = "B"
        if rec.parse_ok and rec.visible_pass:
            rec.committed = True
            current = new_src  # KEEP the patch
        # else: revert to previous current (do nothing)
        recs.append(rec)
    return recs


def arm_C_random(llm: LLM, task: BenchTask, k: int,
                 rng: random.Random) -> list[AttemptRecord]:
    """Iterate; accept each patch with probability 0.5 regardless of test outcome."""
    recs: list[AttemptRecord] = []
    current = (task.abs_path() / "buggy.py").read_text(encoding="utf-8")
    for i in range(k):
        rec, new_src = run_attempt(llm, task, i, current, rng)
        rec.arm = "C"
        if rec.parse_ok and rng.random() < 0.5:
            rec.committed = True
            current = new_src
        recs.append(rec)
    return recs


# ----- metric computation --------------------------------------------------

def pass_at_k(records: list[AttemptRecord], k: int) -> int:
    """1 if any of the first k records has held_out_pass=True, else 0."""
    for r in records[:k]:
        if r.held_out_pass:
            return 1
    return 0


def compute_metrics(records_by_task: dict[str, list[AttemptRecord]],
                    k_values: tuple[int, ...] = (1, 5, 10)
                    ) -> dict[str, dict[str, float]]:
    """Compute per-arm metrics.

    Returns {arm_name: {"pass_at_1": mean, "pass_at_5": mean, ...,
                        "commit_rate": mean, "parse_ok_rate": mean}}
    """
    arms = ("A", "B", "C")
    out: dict[str, dict[str, float]] = {}
    for arm in arms:
        all_recs = [r for recs in records_by_task.values()
                    for r in recs if r.arm == arm]
        n_tasks = len(records_by_task)
        # Pass@k: per task
        per_task_pass: dict[int, float] = {}
        for k in k_values:
            per_task_pass[k] = sum(
                pass_at_k([r for r in records_by_task[tid] if r.arm == arm], k)
                for tid in records_by_task
            ) / max(n_tasks, 1)
        commit_rate = (sum(1 for r in all_recs if r.committed)
                       / max(len(all_recs), 1))
        parse_ok_rate = (sum(1 for r in all_recs if r.parse_ok)
                         / max(len(all_recs), 1))
        out[arm] = {
            **{f"pass_at_{k}": per_task_pass[k] for k in k_values},
            "commit_rate": commit_rate,
            "parse_ok_rate": parse_ok_rate,
            "n_records": len(all_recs),
        }
    return out


# ----- Mann-Whitney U (small-sample exact) ---------------------------------

def mann_whitney_u(x: list[float], y: list[float]) -> tuple[float, float]:
    """Exact two-sided Mann-Whitney U for two small samples.

    Returns (U, p_two_sided). Uses permutation null when feasible
    (2**n with n<=12), else normal approximation with continuity
    correction.
    """
    nx, ny = len(x), len(y)
    if nx == 0 or ny == 0:
        return 0.0, 1.0
    # Rank combined sample, breaking ties by mean rank.
    combined = [(v, "x") for v in x] + [(v, "y") for v in y]
    combined.sort(key=lambda t: t[0])
    # Assign ranks with tie handling.
    ranks: list[float] = []
    i = 0
    while i < len(combined):
        j = i
        while j + 1 < len(combined) and combined[j + 1][0] == combined[i][0]:
            j += 1
        avg_rank = (i + j) / 2 + 1  # 1-indexed
        for k in range(i, j + 1):
            ranks.append(avg_rank)
        i = j + 1
    # Sum of ranks for x.
    r_x = sum(ranks[i] for i in range(len(combined)) if combined[i][1] == "x")
    u_x = r_x - nx * (nx + 1) / 2
    u_y = nx * ny - u_x
    u = min(u_x, u_y)

    # Exact permutation test if 2**(nx+ny) <= 200000.
    n_total = nx + ny
    if n_total <= 17:  # 2^17 = 131072, fast enough
        from itertools import combinations
        count = 0
        total = 0
        for idxs in combinations(range(n_total), nx):
            # In the permutation test, we ask: if we re-labeled these
            # specific indices as 'x' (rest as 'y'), what U would we
            # get? The ranks must be computed against the FULL combined
            # sample — not within the picked subset — because U depends
            # on how x ranks compare to y ranks.
            r_sub = sum(ranks[i] for i in idxs)
            u_sub = r_sub - nx * (nx + 1) / 2
            u_sub_min = min(u_sub, nx * ny - u_sub)
            total += 1
            if u_sub_min <= u:
                count += 1
        p = count / total
        return float(u), float(p)

    # Normal approximation.
    mu = nx * ny / 2
    sigma = math.sqrt(nx * ny * (nx + ny + 1) / 12)
    if sigma == 0:
        return float(u), 1.0
    z = (u - mu) / sigma
    # Two-sided p via erf approximation.
    p = math.erfc(abs(z) / math.sqrt(2))
    return float(u), float(p)


# ----- driver --------------------------------------------------------------

@dataclasses.dataclass
class ExperimentResult:
    arms_data: dict[str, list[AttemptRecord]]  # arm -> all records
    metrics: dict[str, dict[str, float]]
    per_task_pass_at_5: dict[str, dict[str, int]]  # task_id -> arm -> 0/1
    stats: dict[str, dict[str, float]]  # comparison -> {u, p}


def run_experiment(
    bench_jsonl: Path,
    k_per_task: int,
    model: str,
    ollama_url: str,
    timeout_s: float,
    seed: int,
    arms: tuple[str, ...] = ("A", "B", "C"),
) -> ExperimentResult:
    rng = random.Random(seed)
    tasks = load_benchmark(bench_jsonl)
    llm = LLM(url=ollama_url, model=model, timeout=timeout_s)

    arm_fns: dict[str, Callable] = {
        "A": arm_A_baseline,
        "B": arm_B_select,
        "C": arm_C_random,
    }
    records_by_task: dict[str, list[AttemptRecord]] = {
        t.id: [] for t in tasks
    }
    # We'll group records by (task, arm) to compute pass@k cleanly.
    grouped: dict[tuple[str, str], list[AttemptRecord]] = {
        (t.id, arm): [] for t in tasks for arm in arms
    }

    for arm in arms:
        fn = arm_fns[arm]
        for task in tasks:
            # Per-arm sub-RNG so the experiment is reproducible but
            # arm C's accept/reject coin is independent of arm B's.
            sub_seed = seed + hash((arm, task.id)) % (2**31)
            sub_rng = random.Random(sub_seed)
            recs = fn(llm, task, k_per_task, sub_rng)
            grouped[(task.id, arm)] = recs
            records_by_task[task.id].extend(recs)

    metrics = compute_metrics(records_by_task)

    # Per-task pass@5 for stats.
    per_task_pass: dict[str, dict[str, int]] = {}
    for t in tasks:
        per_task_pass[t.id] = {}
        for arm in arms:
            per_task_pass[t.id][arm] = pass_at_k(
                grouped[(t.id, arm)], min(5, k_per_task))

    stats: dict[str, dict[str, float]] = {}
    if "A" in arms and "B" in arms:
        x = [float(per_task_pass[t.id]["B"]) for t in tasks]
        y = [float(per_task_pass[t.id]["A"]) for t in tasks]
        u, p = mann_whitney_u(x, y)
        stats["B_vs_A"] = {"u": u, "p": p}
    if "C" in arms and "B" in arms:
        x = [float(per_task_pass[t.id]["B"]) for t in tasks]
        y = [float(per_task_pass[t.id]["C"]) for t in tasks]
        u, p = mann_whitney_u(x, y)
        stats["B_vs_C"] = {"u": u, "p": p}

    arms_data: dict[str, list[AttemptRecord]] = {
        arm: [r for (tid, a), recs in grouped.items()
              if a == arm for r in recs]
        for arm in arms
    }
    return ExperimentResult(
        arms_data=arms_data,
        metrics=metrics,
        per_task_pass_at_5=per_task_pass,
        stats=stats,
    )


# ----- CLI -----------------------------------------------------------------

def cmd_experiment_run(args: argparse.Namespace) -> int:
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"[exp] loading benchmark from {args.bench}")
    print(f"[exp] model={args.model} k_per_task={args.k} seed={args.seed}")
    result = run_experiment(
        bench_jsonl=Path(args.bench),
        k_per_task=args.k,
        model=args.model,
        ollama_url=args.ollama_url,
        timeout_s=args.timeout,
        seed=args.seed,
        arms=tuple(args.arms.split(",")),
    )
    # Serialize: convert dataclasses to dicts.
    serialized = {
        "config": {
            "bench": args.bench,
            "model": args.model,
            "ollama_url": args.ollama_url,
            "k_per_task": args.k,
            "seed": args.seed,
            "arms": args.arms.split(","),
        },
        "metrics": result.metrics,
        "per_task_pass_at_5": result.per_task_pass_at_5,
        "stats": result.stats,
        "records": {
            arm: [dataclasses.asdict(r) for r in recs]
            for arm, recs in result.arms_data.items()
        },
    }
    out_path.write_text(json.dumps(serialized, indent=2),
                        encoding="utf-8")
    print(f"[exp] wrote {out_path}")
    # Print summary.
    print("\n=== summary (pass@5 mean ± per-arm) ===")
    for arm, m in result.metrics.items():
        print(f"  arm {arm}: pass@1={m['pass_at_1']:.2f} "
              f"pass@5={m['pass_at_5']:.2f} pass@10={m['pass_at_10']:.2f} "
              f"parse_ok={m['parse_ok_rate']:.2f} "
              f"commit={m['commit_rate']:.2f}")
    if result.stats:
        print("\n=== stats (Mann-Whitney U, two-sided) ===")
        for cmp, s in result.stats.items():
            print(f"  {cmp}: U={s['u']:.2f} p={s['p']:.4f}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="forkling experiment")
    sub = p.add_subparsers(dest="cmd", required=True)

    pr = sub.add_parser("run", help="Run the three-arm experiment.")
    pr.add_argument("--bench", required=True,
                    help="Path to FORKLAND-BENCH-001.jsonl")
    pr.add_argument("--k", type=int, default=10,
                    help="Attempts per task per arm (default 10).")
    pr.add_argument("--model", default="llama3.2:3b")
    pr.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    pr.add_argument("--timeout", type=float, default=60.0)
    pr.add_argument("--seed", type=int, default=20260925)
    pr.add_argument("--arms", default="A,B,C",
                    help="Comma-separated arm ids (default A,B,C).")
    pr.add_argument("--out", required=True, help="Output JSON file.")
    pr.set_defaults(func=cmd_experiment_run)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
