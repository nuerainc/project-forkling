"""FORKLAND Experiment driver — three-arm comparison on FORKLAND-BENCH-001.

This is the implementation of the pre-registered hypothesis in
paper/hypothesis.md. **Read that file before changing this one.**

This module is protocol 1, frozen so exp001-exp003 stay reproducible.
New experiments use protocol 2 (forkling/experiment2.py, selected with
``--protocol 2``); see paper/exp003_results.md, "Validity caveat", for
why.

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
import os
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
patch with this EXACT shape (no other fields, no list, just this object):

{{"kind": "patch", "path": "buggy.py",
  "old": "<the EXACT substring in buggy.py you are replacing>",
  "new": "<the replacement text>"}}

Worked example — given buggy.py:
```python
def add(a, b):
    return a - b
```
and the task "add should add", the correct response is:
{{"kind": "patch", "path": "buggy.py",
  "old": "return a - b", "new": "return a + b"}}

Rules:
- `old` MUST appear verbatim in buggy.py (copy-paste it; do not paraphrase).
- `new` MUST be the full replacement (include the same indentation).
- Do NOT wrap the JSON in markdown fences.
- Do NOT include prose, explanations, or code blocks around the JSON.
- Output exactly one JSON object, nothing else.

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


# Aliases for exp003 nomenclature (N=no-iterate, I=in-loop select,
# R=in-loop random). exp003 also adds P=post-hoc re-rank.
arm_N_no_iterate = arm_A_baseline          # same logic, new name
arm_I_in_loop_select = arm_B_select        # same logic, new name
arm_R_in_loop_random = arm_C_random       # same logic, new name


def arm_P_post_hoc_rerank(llm: LLM, task: BenchTask, k: int,
                           rng: random.Random) -> list[AttemptRecord]:
    """K independent one-shot draws, then re-rank by visible-test score.

    Same LLM calls as arm N/A. The only difference is *when* the
    selector runs: arm P selects the BEST candidate from K draws
    at the end; arm I selects PASS/FAIL on each iteration in-loop.

    Pre-registration §6 (paper/hypothesis_v3.md): "For each task,
    iterate up to K attempts. After all K draws, pick the patch
    with the most visible tests passing. Tie-break: first one in
    attempt order."

    Returns the SAME records as arm_A_baseline, but with exactly
    one record marked committed=True: the winner. Others are
    committed=False (the candidate was rejected by the post-hoc
    ranker).

    To avoid re-grading patches we already graded in run_attempt,
    we cache the (idx -> source) map and re-call grade() to count
    visible-test passes per candidate.
    """
    buggy = (task.abs_path() / "buggy.py").read_text(encoding="utf-8")
    # Run K attempts and collect parseable candidates.
    recs: list[AttemptRecord] = []
    candidates: list[tuple[int, str, AttemptRecord]] = []  # (idx, source, rec)
    for i in range(k):
        rec, src = run_attempt(llm, task, i, buggy, rng)
        rec.arm = "P"
        rec.committed = False  # default: rejected by post-hoc ranker
        recs.append(rec)
        if rec.parse_ok and not rec.note.startswith("infra:"):
            candidates.append((i, src, rec))

    # Re-grade each candidate against visible tests and score.
    # (We already have held_out_pass but we need visible-test score,
    # which run_attempt doesn't track. Re-grade.)
    scored: list[tuple[float, int, str]] = []  # (-score, idx, source)
    for idx, src, _ in candidates:
        result = grade(task, src)
        # Score = number of visible tests passing. Use 1.0 / 0.0 for
        # boolean visible_pass as a tie-break.
        visible_score = float(result.visible_pass) * 1000
        # If we could parse pytest output for individual test
        # counts we could be finer; visible_pass is the simple proxy.
        scored.append((-visible_score, idx, src))
    # Sort: lowest score first (since we negated). Actually we want
    # HIGHEST first, so sort by -score ascending.
    scored.sort()
    if scored:
        # The winner is the LAST element (highest score).
        # Tie-break: first in attempt order means lower idx wins.
        # Since we sorted ascending by (-score, idx), the last
        # element has the highest score and within tie the highest
        # idx. That's wrong — we want lowest idx in tie. Let me
        # re-sort.
        scored.sort(key=lambda t: (-t[0], t[1]))
        _, winner_idx, _ = scored[0]
        recs[winner_idx].committed = True
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
    checkpoint_path: Path | None = None,
    resume_from: Path | None = None,
) -> ExperimentResult:
    rng = random.Random(seed)
    tasks = load_benchmark(bench_jsonl)
    llm = LLM(url=ollama_url, model=model, timeout=timeout_s)

    arm_fns: dict[str, Callable] = {
        # exp001/exp002 nomenclature
        "A": arm_A_baseline,
        "B": arm_B_select,
        "C": arm_C_random,
        # exp003 nomenclature (aliases above + new arm P)
        "N": arm_N_no_iterate,
        "I": arm_I_in_loop_select,
        "R": arm_R_in_loop_random,
        "P": arm_P_post_hoc_rerank,
    }
    records_by_task: dict[str, list[AttemptRecord]] = {
        t.id: [] for t in tasks
    }
    # We'll group records by (task, arm) to compute pass@k cleanly.
    grouped: dict[tuple[str, str], list[AttemptRecord]] = {
        (t.id, arm): [] for t in tasks for arm in arms
    }

    # Optional resume: load any previously-completed (task, arm) pairs
    # from a JSONL checkpoint file. Each line: {"task_id", "arm",
    # "records": [...]}.
    completed: set[tuple[str, str]] = set()
    if resume_from is not None and resume_from.is_file():
        with resume_from.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                obj = json.loads(line)
                recs = [AttemptRecord(**r) for r in obj["records"]]
                key = (obj["task_id"], obj["arm"])
                grouped[key] = recs
                records_by_task[obj["task_id"]].extend(recs)
                completed.add(key)
        print(f"[exp] resumed {len(completed)} (task, arm) pairs from {resume_from}")

    # Optional checkpoint: append one JSONL line per completed
    # (task, arm). If the run is killed mid-experiment, the file
    # already has every completed pair and can be used as resume_from
    # for the next attempt.
    ckpt_file = None
    if checkpoint_path is not None:
        checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        ckpt_file = checkpoint_path.open("a", encoding="utf-8")

    for arm in arms:
        fn = arm_fns[arm]
        for task in tasks:
            if (task.id, arm) in completed:
                continue  # resumed; don't redo
            # Per-arm sub-RNG so the experiment is reproducible but
            # arm C's accept/reject coin is independent of arm B's.
            sub_seed = seed + hash((arm, task.id)) % (2**31)
            sub_rng = random.Random(sub_seed)
            recs = fn(llm, task, k_per_task, sub_rng)
            grouped[(task.id, arm)] = recs
            records_by_task[task.id].extend(recs)
            if ckpt_file is not None:
                line_obj = {
                    "task_id": task.id,
                    "arm": arm,
                    "records": [dataclasses.asdict(r) for r in recs],
                }
                ckpt_file.write(json.dumps(line_obj) + "\n")
                ckpt_file.flush()
                os.fsync(ckpt_file.fileno())

    if ckpt_file is not None:
        ckpt_file.close()

    metrics = compute_metrics(records_by_task)

    # Per-task pass@5 for stats.
    per_task_pass: dict[str, dict[str, int]] = {}
    for t in tasks:
        per_task_pass[t.id] = {}
        for arm in arms:
            per_task_pass[t.id][arm] = pass_at_k(
                grouped[(t.id, arm)], min(5, k_per_task))

    stats: dict[str, dict[str, float]] = {}
    # exp001/exp002 comparisons: B vs A, B vs C
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
    # exp003 primary: I vs P (in-loop select vs post-hoc re-rank)
    if "I" in arms and "P" in arms:
        x = [float(per_task_pass[t.id]["I"]) for t in tasks]
        y = [float(per_task_pass[t.id]["P"]) for t in tasks]
        u, p = mann_whitney_u(x, y)
        stats["I_vs_P"] = {"u": u, "p": p}
    # exp003 secondaries: I vs N, I vs R, P vs N
    if "I" in arms and "N" in arms:
        x = [float(per_task_pass[t.id]["I"]) for t in tasks]
        y = [float(per_task_pass[t.id]["N"]) for t in tasks]
        u, p = mann_whitney_u(x, y)
        stats["I_vs_N"] = {"u": u, "p": p}
    if "I" in arms and "R" in arms:
        x = [float(per_task_pass[t.id]["I"]) for t in tasks]
        y = [float(per_task_pass[t.id]["R"]) for t in tasks]
        u, p = mann_whitney_u(x, y)
        stats["I_vs_R"] = {"u": u, "p": p}
    if "P" in arms and "N" in arms:
        x = [float(per_task_pass[t.id]["P"]) for t in tasks]
        y = [float(per_task_pass[t.id]["N"]) for t in tasks]
        u, p = mann_whitney_u(x, y)
        stats["P_vs_N"] = {"u": u, "p": p}

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
    if args.protocol == 2:
        from . import experiment2
        return experiment2.cmd_run(args)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"[exp] loading benchmark from {args.bench}")
    print(f"[exp] model={args.model} k_per_task={args.k} seed={args.seed}")
    checkpoint = Path(args.checkpoint) if args.checkpoint else None
    resume = Path(args.resume_from) if args.resume_from else None
    result = run_experiment(
        bench_jsonl=Path(args.bench),
        k_per_task=args.k,
        model=args.model,
        ollama_url=args.ollama_url,
        timeout_s=args.timeout,
        seed=args.seed,
        arms=tuple(args.arms.split(",")),
        checkpoint_path=checkpoint,
        resume_from=resume,
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


def add_protocol_args(parser: argparse.ArgumentParser) -> None:
    """Options shared by `forkling experiment run` and this module's CLI."""
    parser.add_argument("--protocol", type=int, choices=(1, 2), default=1,
                        help="1 = exp001-exp003 harness (kept for reproduction); "
                             "2 = fixed harness from paper/hypothesis_v4r1.md "
                             "(returned-patch endpoint, in-loop feedback, "
                             "replicates, paired Wilcoxon).")
    parser.add_argument("--replicates", type=int, default=5,
                        help="Protocol 2 only: replicates per (task, arm).")
    parser.add_argument("--temperature", type=float, default=0.8,
                        help="Protocol 2 only: pinned Ollama sampling temperature.")


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
    pr.add_argument("--checkpoint", default=None,
                    help="Append JSONL checkpoint after each (task, arm) completes. "
                         "Survives crashes; can be passed back via --resume-from.")
    pr.add_argument("--resume-from", default=None,
                    help="Resume from a previous checkpoint JSONL. Skips any "
                         "(task, arm) pairs already completed.")
    add_protocol_args(pr)
    pr.set_defaults(func=cmd_experiment_run)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
