"""FORKLAND experiment harness, protocol 2.

Implements the design in paper/hypothesis_v4r1.md (exp004) and
paper/hypothesis_v3b.md (exp003b). **Read those before changing this
file.** Protocol 1 (exp001-exp003) lives unchanged in experiment.py so
those results stay reproducible.

What protocol 2 fixes (see paper/exp003_results.md, "Validity caveat"):

1. The primary endpoint is ``returned_pass``: whether the patch an arm
   actually returns passes the held-out tests. Protocol 1 scored
   pass@k over all draws, which ignores selection.
2. In-loop arms (I, R) are prompted with the *current* source plus
   feedback on the previous attempt, instead of the original buggy.py
   with no feedback.
3. Selection ranks on the number of visible tests passed, not a
   boolean, so partial fixes can be ranked.
4. Sub-seeds come from a stable hash; per-call Ollama seed and
   temperature are pinned and recorded.
5. Each (task, arm) is run for S replicates; arms are compared with an
   exact paired Wilcoxon signed-rank test over tasks plus a bootstrap
   CI on the mean difference.
6. A rule-based fallback completion (Ollama unreachable) is recorded as
   an infra failure, never as model output.

Arms (K = LLM calls per task/arm/replicate):
  N  one-shot          K independent draws; returns attempt 0.
  P  post-hoc re-rank  K independent draws; returns the draw with the
                       most visible tests passed (tie: lowest index).
  I  in-loop select    sees current source + feedback; keeps a patch iff
                       it passes strictly more visible tests; stops once
                       all visible tests pass; returns the final source.
  R  in-loop random    same prompt as I; keeps a parsed patch with
                       probability 0.5; no early stop.
"""
from __future__ import annotations

import dataclasses
import json
import math
import random
import time
import zlib
from pathlib import Path
from typing import Any, Callable, Protocol

from .bench import BenchTask, GradeResult, grade, load_benchmark
from .experiment import PROMPT_TEMPLATE, extract_patch

PROTOCOL = 2
ARMS = ("N", "P", "I", "R")
FEEDBACK_MAX_CHARS = 2000
DEFAULT_TEMPERATURE = 0.8

PRIMARY = ("I", "P")
SECONDARY = (("P", "N"), ("I", "R"), ("I", "N"))


class CompletionLike(Protocol):
    text: str
    used_llm: bool


class LLMLike(Protocol):
    def complete(self, prompt: str, system: str | None = None,
                 kind: str = "complete", task: str = "",
                 options: dict | None = None) -> CompletionLike: ...


Grader = Callable[[BenchTask, str], GradeResult]


# ----- seeds ---------------------------------------------------------------

def stable_seed(*parts: Any) -> int:
    """Deterministic 31-bit seed from arbitrary JSON-able parts.

    Unlike hash(), this does not change between Python processes.
    """
    blob = json.dumps(parts, separators=(",", ":"), default=str)
    return zlib.crc32(blob.encode("utf-8")) & 0x7FFFFFFF


def call_seed(seed: int, task_id: str, replicate: int, attempt: int) -> int:
    """Ollama seed for one call.

    Deliberately independent of the arm: arms whose prompts coincide
    (all arms at attempt 0; N and P at every attempt) get the same
    sample, which pairs the arms (common random numbers) and reduces
    the variance of between-arm differences.
    """
    return stable_seed("call", seed, task_id, replicate, attempt)


# ----- prompts -------------------------------------------------------------

FEEDBACK_TEMPLATE = """

Feedback on your previous attempt:
{feedback}
"""


def _visible_tests(task: BenchTask) -> str:
    return (task.abs_path() / "visible_tests.py").read_text(encoding="utf-8")


def build_prompt(task: BenchTask, source: str, feedback: str = "") -> str:
    """Protocol-1 prompt text around ``source``, plus optional feedback."""
    prompt = PROMPT_TEMPLATE.format(
        prompt=task.prompt, buggy=source, visible_tests=_visible_tests(task))
    if feedback:
        prompt += FEEDBACK_TEMPLATE.format(feedback=feedback)
    return prompt


def _patch_summary(raw: str, limit: int = 600) -> str:
    raw = raw.strip()
    return raw if len(raw) <= limit else raw[:limit] + " …[truncated]"


def describe_attempt(rec: "Attempt", kept: bool, output: str) -> str:
    """Feedback block describing one in-loop attempt."""
    lines = [f"Your response was:\n{_patch_summary(rec.raw_response)}"]
    if not rec.parse_ok:
        lines.append("It could not be parsed as a patch, or its `old` text "
                     "was not found in the current buggy.py. The file is "
                     "unchanged.")
    else:
        lines.append(f"It passed {rec.visible_passed} of {rec.visible_total} "
                     "visible tests.")
        lines.append("The patch was KEPT; the current buggy.py above "
                     "includes it." if kept else
                     "The patch was NOT kept; the current buggy.py above "
                     "does not include it.")
        if output.strip():
            lines.append("Visible test output:\n" + output.strip())
    text = "\n".join(lines)
    return text[:FEEDBACK_MAX_CHARS]


# ----- records -------------------------------------------------------------

@dataclasses.dataclass
class Attempt:
    task_id: str
    arm: str
    replicate: int
    attempt_idx: int
    parse_ok: bool
    kept: bool
    visible_passed: int
    visible_total: int
    visible_pass: bool
    held_out_pass: bool
    used_llm: bool
    infra: bool
    raw_response: str
    elapsed_s: float
    note: str = ""


@dataclasses.dataclass
class ArmRun:
    task_id: str
    arm: str
    replicate: int
    returned_pass: bool
    returned_visible_passed: int
    calls: int
    attempts: list[Attempt]


def _attempt(llm: LLMLike, grader: Grader, task: BenchTask, arm: str,
             replicate: int, idx: int, source: str, prompt: str,
             options: dict) -> tuple[Attempt, str, str]:
    """One LLM call + grade. Returns (record, patched_source, visible_output)."""
    t0 = time.monotonic()
    completion = llm.complete(prompt, kind="experiment", task=task.id,
                              options=options)
    elapsed = time.monotonic() - t0
    raw = completion.text
    base = dict(task_id=task.id, arm=arm, replicate=replicate,
                attempt_idx=idx, raw_response=raw, elapsed_s=elapsed,
                used_llm=bool(completion.used_llm))
    if not completion.used_llm:
        return Attempt(**base, parse_ok=False, kept=False, visible_passed=0,
                       visible_total=0, visible_pass=False,
                       held_out_pass=False, infra=True,
                       note="infra:llm_fallback"), source, ""
    parsed = extract_patch(raw, source)
    if parsed is None:
        return Attempt(**base, parse_ok=False, kept=False, visible_passed=0,
                       visible_total=0, visible_pass=False,
                       held_out_pass=False, infra=False,
                       note="parse_fail"), source, ""
    new_source, _ = parsed
    g = grader(task, new_source)
    # A patch that hangs the tests ("pytest timeout") is the model's
    # failure; only a harness that cannot launch pytest is infra.
    infra = g.error.startswith("pytest launch failed")
    return Attempt(**base, parse_ok=True, kept=False,
                   visible_passed=g.visible_passed,
                   visible_total=g.visible_total,
                   visible_pass=g.visible_pass,
                   held_out_pass=g.held_out_pass, infra=infra,
                   note=f"infra:{g.error[:80]}" if infra else ""), \
        new_source, g.visible_output


def run_arm(llm: LLMLike, task: BenchTask, arm: str, k: int, replicate: int,
            seed: int, temperature: float,
            grader: Grader = grade) -> ArmRun:
    """Run one (task, arm, replicate) under protocol 2."""
    if arm not in ARMS:
        raise ValueError(f"unknown protocol-2 arm {arm!r}; expected one of {ARMS}")
    buggy = (task.abs_path() / "buggy.py").read_text(encoding="utf-8")
    coin = random.Random(stable_seed("coin", seed, arm, task.id, replicate))

    def opts(idx: int) -> dict:
        return {"temperature": temperature,
                "seed": call_seed(seed, task.id, replicate, idx)}

    attempts: list[Attempt] = []

    if arm in ("N", "P"):
        sources: list[str] = []
        prompt = build_prompt(task, buggy)
        for i in range(k):
            rec, src, _ = _attempt(llm, grader, task, arm, replicate, i,
                                   buggy, prompt, opts(i))
            attempts.append(rec)
            sources.append(src)
        if arm == "N":
            pick = 0 if attempts and attempts[0].parse_ok else None
        else:
            ok = [a for a in attempts if a.parse_ok and not a.infra]
            pick = (min(ok, key=lambda a: (-a.visible_passed, a.attempt_idx))
                    .attempt_idx if ok else None)
        if pick is not None:
            attempts[pick].kept = True
            chosen = attempts[pick]
            return ArmRun(task.id, arm, replicate,
                          returned_pass=chosen.held_out_pass,
                          returned_visible_passed=chosen.visible_passed,
                          calls=len(attempts), attempts=attempts)
        g = grader(task, buggy)
        return ArmRun(task.id, arm, replicate, returned_pass=g.held_out_pass,
                      returned_visible_passed=g.visible_passed,
                      calls=len(attempts), attempts=attempts)

    # In-loop arms: I (select) and R (random accept).
    current = buggy
    g0 = grader(task, buggy)
    cur_score, cur_held = g0.visible_passed, g0.held_out_pass
    total = g0.visible_total
    feedback = ""
    for i in range(k):
        if arm == "I" and total and cur_score >= total:
            break  # every visible test passes: nothing left to select on
        prompt = build_prompt(task, current, feedback)
        rec, src, out = _attempt(llm, grader, task, arm, replicate, i,
                                 current, prompt, opts(i))
        if arm == "I":
            keep = rec.parse_ok and not rec.infra and rec.visible_passed > cur_score
        else:
            keep = rec.parse_ok and not rec.infra and coin.random() < 0.5
        if keep:
            rec.kept = True
            current = src
            cur_score, cur_held = rec.visible_passed, rec.held_out_pass
        attempts.append(rec)
        feedback = describe_attempt(rec, keep, out)
    return ArmRun(task.id, arm, replicate, returned_pass=cur_held,
                  returned_visible_passed=cur_score, calls=len(attempts),
                  attempts=attempts)


# ----- statistics ----------------------------------------------------------

def _midranks(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        for t in range(i, j + 1):
            ranks[order[t]] = (i + j) / 2 + 1
        i = j + 1
    return ranks


def wilcoxon_signed_rank(diffs: list[float]) -> dict[str, float]:
    """Two-sided Wilcoxon signed-rank test on paired differences.

    Zero differences are dropped; tied |d| get mid-ranks. The null
    distribution is exact (all 2^n sign flips) for n <= 20, else a
    normal approximation. Returns {"w_plus", "n", "p"}.
    """
    d = [x for x in diffs if x != 0]
    n = len(d)
    if n == 0:
        return {"w_plus": 0.0, "n": 0, "p": 1.0}
    ranks = _midranks([abs(x) for x in d])
    w_plus = sum(r for r, x in zip(ranks, d) if x > 0)
    mean = sum(ranks) / 2
    obs = abs(w_plus - mean)
    eps = 1e-9
    if n <= 20:
        # Distribution of the positive-rank sum via subset-sum counting on
        # doubled ranks (mid-ranks are multiples of 0.5).
        counts: dict[int, int] = {0: 1}
        for r in ranks:
            step = int(round(r * 2))
            nxt = dict(counts)
            for s, c in counts.items():
                nxt[s + step] = nxt.get(s + step, 0) + c
            counts = nxt
        total = 2 ** n
        extreme = sum(c for s, c in counts.items()
                      if abs(s / 2 - mean) >= obs - eps)
        p = extreme / total
    else:
        var = sum(r * r for r in ranks) / 4
        z = obs / math.sqrt(var) if var else 0.0
        p = math.erfc(z / math.sqrt(2))
    return {"w_plus": float(w_plus), "n": n, "p": float(min(p, 1.0))}


def bootstrap_ci(diffs: list[float], seed: int, n_boot: int = 10000,
                 alpha: float = 0.05) -> tuple[float, float]:
    """Percentile bootstrap CI for the mean difference, resampling tasks."""
    if not diffs:
        return (0.0, 0.0)
    rng = random.Random(seed)
    n = len(diffs)
    means = sorted(sum(rng.choice(diffs) for _ in range(n)) / n
                   for _ in range(n_boot))
    lo = means[int((alpha / 2) * n_boot)]
    hi = means[min(int((1 - alpha / 2) * n_boot), n_boot - 1)]
    return (lo, hi)


def compare(per_task: dict[str, dict[str, float]], a: str, b: str,
            seed: int) -> dict[str, Any]:
    tasks = sorted(per_task)
    diffs = [per_task[t][a] - per_task[t][b] for t in tasks]
    w = wilcoxon_signed_rank(diffs)
    lo, hi = bootstrap_ci(diffs, seed)
    return {"mean_diff": sum(diffs) / max(len(diffs), 1),
            "ci95": [lo, hi], **w}


# ----- driver --------------------------------------------------------------

def _pass_at_k(attempts: list[Attempt], k: int) -> int:
    return int(any(a.held_out_pass for a in attempts[:k]))


def summarize_runs(runs: list[ArmRun], arms: tuple[str, ...], seed: int
                   ) -> dict[str, Any]:
    tasks = sorted({r.task_id for r in runs})
    per_task: dict[str, dict[str, float]] = {t: {} for t in tasks}
    metrics: dict[str, dict[str, float]] = {}
    for arm in arms:
        arm_runs = [r for r in runs if r.arm == arm]
        for t in tasks:
            rs = [r for r in arm_runs if r.task_id == t]
            per_task[t][arm] = (sum(r.returned_pass for r in rs) / len(rs)
                                if rs else 0.0)
        attempts = [a for r in arm_runs for a in r.attempts]
        n_att = max(len(attempts), 1)
        n_runs = max(len(arm_runs), 1)
        metrics[arm] = {
            "returned_pass": sum(per_task[t][arm] for t in tasks) / max(len(tasks), 1),
            "pass_at_1": sum(_pass_at_k(r.attempts, 1) for r in arm_runs) / n_runs,
            "pass_at_5": sum(_pass_at_k(r.attempts, 5) for r in arm_runs) / n_runs,
            "parse_ok_rate": sum(a.parse_ok for a in attempts) / n_att,
            "kept_rate": sum(a.kept for a in attempts) / n_att,
            "infra_rate": sum(a.infra for a in attempts) / n_att,
            "mean_calls": sum(r.calls for r in arm_runs) / n_runs,
            "n_runs": len(arm_runs),
        }
    stats: dict[str, Any] = {}
    for a, b in (PRIMARY, *SECONDARY):
        if a in arms and b in arms:
            stats[f"{a}_vs_{b}"] = compare(per_task, a, b,
                                           stable_seed("boot", seed, a, b))
    return {"per_task_returned_pass": per_task, "metrics": metrics,
            "stats": stats}


def run_experiment(tasks: list[BenchTask], llm: LLMLike, arms: tuple[str, ...],
                   k: int, replicates: int, seed: int,
                   temperature: float = DEFAULT_TEMPERATURE,
                   grader: Grader = grade,
                   checkpoint_path: Path | None = None,
                   resume_from: Path | None = None,
                   progress: Callable[[str], None] | None = None
                   ) -> dict[str, Any]:
    """Run every (task, arm, replicate) and return the result dict."""
    done: dict[tuple[str, str, int], ArmRun] = {}
    if resume_from is not None and resume_from.is_file():
        for line in resume_from.read_text(encoding="utf-8").splitlines():
            if line.strip():
                run = _run_from_json(json.loads(line))
                done[(run.task_id, run.arm, run.replicate)] = run
    ckpt = None
    if checkpoint_path is not None:
        checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        ckpt = checkpoint_path.open("a", encoding="utf-8")
    runs: list[ArmRun] = []
    try:
        for rep in range(replicates):
            for task in tasks:
                for arm in arms:
                    key = (task.id, arm, rep)
                    if key in done:
                        runs.append(done[key])
                        continue
                    run = run_arm(llm, task, arm, k, rep, seed, temperature,
                                  grader)
                    runs.append(run)
                    if ckpt is not None:
                        ckpt.write(json.dumps(dataclasses.asdict(run)) + "\n")
                        ckpt.flush()
                    if progress is not None:
                        progress(f"rep={rep} task={task.id} arm={arm} "
                                 f"returned_pass={int(run.returned_pass)} "
                                 f"calls={run.calls}")
    finally:
        if ckpt is not None:
            ckpt.close()
    out = summarize_runs(runs, arms, seed)
    out["runs"] = [dataclasses.asdict(r) for r in runs]
    return out


def _run_from_json(obj: dict) -> ArmRun:
    attempts = [Attempt(**a) for a in obj.pop("attempts")]
    return ArmRun(**obj, attempts=attempts)


def cmd_run(args) -> int:
    """`forkling experiment run --protocol 2` entry point."""
    from .llm import LLM

    arms = tuple(a.strip() for a in args.arms.split(",") if a.strip())
    unknown = [a for a in arms if a not in ARMS]
    if unknown:
        print(f"[exp] protocol 2 arms are {','.join(ARMS)}; got {unknown}")
        return 2
    tasks = load_benchmark(args.bench)
    llm = LLM(url=args.ollama_url, model=args.model, timeout=args.timeout)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"[exp] protocol 2: {len(tasks)} tasks, arms={','.join(arms)}, "
          f"k={args.k}, replicates={args.replicates}, model={args.model}, "
          f"temperature={args.temperature}, seed={args.seed}")
    result = run_experiment(
        tasks, llm, arms, k=args.k, replicates=args.replicates,
        seed=args.seed, temperature=args.temperature,
        checkpoint_path=Path(args.checkpoint) if args.checkpoint else None,
        resume_from=Path(args.resume_from) if args.resume_from else None,
        progress=lambda msg: print(f"[exp] {msg}", flush=True),
    )
    result = {"config": {
        "protocol": PROTOCOL, "bench": args.bench, "model": args.model,
        "ollama_url": args.ollama_url, "k_per_task": args.k,
        "replicates": args.replicates, "seed": args.seed,
        "temperature": args.temperature, "arms": list(arms),
        "harness_commit": _git_head(),
    }, **result}
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"[exp] wrote {out_path}")
    for arm, m in result["metrics"].items():
        print(f"  arm {arm}: returned_pass={m['returned_pass']:.2f} "
              f"pass@5={m['pass_at_5']:.2f} parse_ok={m['parse_ok_rate']:.2f} "
              f"infra={m['infra_rate']:.2f} calls={m['mean_calls']:.1f}")
    for name, s in result["stats"].items():
        print(f"  {name}: mean_diff={s['mean_diff']:+.3f} "
              f"CI95=[{s['ci95'][0]:+.3f}, {s['ci95'][1]:+.3f}] "
              f"W+={s['w_plus']:.1f} n={s['n']} p={s['p']:.4f}")
    worst = max((m["infra_rate"] for m in result["metrics"].values()), default=0)
    if worst > 0.20:
        print(f"[exp] WARNING: infra_rate {worst:.2f} > 0.20 in some arm; "
              "per the pre-registration this run is an infra failure.")
    return 0


def _git_head() -> str:
    import subprocess
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                              text=True, timeout=5).stdout.strip()
    except Exception:
        return ""
