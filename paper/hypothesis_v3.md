# FORKLAND Experiment 003 — Pre-registered Hypothesis

**Author:** Jeremy Beebe
**Date written:** 2026-09-25
**Status:** ACTIVE — no pilot data has been inspected under this design
**Predecessors:**
- [hypothesis.md](hypothesis.md) — exp001, NULL, [results](exp001_results.md)
- [hypothesis_v2.md](hypothesis_v2.md) — exp002 (in flight, model swap)

---

## 1. The question

**Is selection pressure on LLM-generated patches a *filter* (a way to
discard bad patches so the running state stays good) or an *amplifier*
(a way to make the LLM generate *better* patches because the prompt
context includes prior attempts)?**

Concretely: when an LLM agent proposes K candidate patches for a
bug-fix task, does the order in which selection operates (after each
attempt, in-loop) outperform selection operating only at the end (on
K independent draws, post-hoc re-rank)?

This question is scientific, not engineering. It is independent of
the specific model, the specific benchmark, and the specific
metric. The answer generalizes to every LLM-driven self-improvement
system that uses a selection mechanism:

- If selection is a **filter** (no signal amplification):
  `iterate_in_loop` ≈ `draw_K_then_re_rank`. The interactive
  component of the evolve loop is *not* the source of value; the
  value is in the re-ranking step itself. Cheap simplification:
  bypass the loop entirely, draw K, pick best.
- If selection is an **amplifier** (signal amplification):
  `iterate_in_loop` > `draw_K_then_re_rank`. The interactive
  loop is load-bearing — running state, prompt context, and
  in-loop retry all contribute. Removing the loop costs
  meaningful accuracy.

Existing self-improvement systems (DGM, AlphaEvolve, FunSearch,
Gödel Agent) implicitly bet on "amplifier" by structuring their
loops with in-loop selection. None of them have tested it.

## 2. The arms

Four arms. All use the same model, prompt, task list, visible
tests, and held-out tests. The only difference is **when** and
**how** selection operates.

| Arm | Name | K | Selection timing | Selection policy |
|---|---|---|---|---|
| N | no-iterate | 10 | n/a (each attempt is independent) | n/a — report first held-out pass |
| P | post-hoc re-rank | 10 | after all K draws | pick the patch with the most visible tests passing |
| I | in-loop select | 10 | after each attempt | keep patch iff visible tests pass (current Arm B) |
| R | in-loop random | 10 | after each attempt | accept patch with probability 0.5 (current Arm C) |

Arm N is the no-iterate baseline (current exp001/002 Arm A).
Arm I is the in-loop iterate-with-selection (current Arm B).
Arm R is the in-loop iterate-with-random-accept (current Arm C)
— included as a sanity check, not a primary comparison.
**Arm P is the new arm** — K independent draws, ranked by visible
tests at the end, best one returned.

The **primary comparison is I vs P**. They use the same K
attempts and the same selector (visible tests). The only
difference is *when* the selector runs. If pass@5(I) > pass@5(P)
with statistical significance, selection is an amplifier. If not,
selection is a filter.

Secondary comparisons (reported, not gated):
- **I vs N:** does in-loop iteration help at all?
- **I vs R:** is selection better than random-accept iteration?
- **P vs N:** does post-hoc re-ranking help at all?

These three secondary comparisons are *not* corrected for multiple
testing in the primary hypothesis. They are reported for context
only.

## 3. Hypothesis

### H1 (alternative, primary)

After N=10 attempts per task per arm on FORKLAND-BENCH-001 (10
tasks × 10 attempts per arm × 4 arms = 400 LLM calls), Arm I
(in-loop select) achieves a higher mean pass@5 than Arm P
(post-hoc re-rank) at p<0.05 by paired Mann–Whitney U on per-task
pass@5.

Pre-registered direction: pass@5(I) > pass@5(P).

### H0 (null, primary)

There is no difference between I and P at alpha=0.05 — pass@5(I)
≤ pass@5(P).

### Pre-registered interpretation rules

| Outcome | Interpretation |
|---|---|
| I > P at p<0.05 | **Positive.** Selection is an amplifier. In-loop iteration is load-bearing. |
| I ≈ P at p≥0.05 | **Null.** Selection is a filter. Post-hoc re-ranking is sufficient. |
| I < P | **Surprising.** In-loop iteration actively hurts vs post-hoc re-ranking. Hypothesis of "amplification" is not just weak, it's wrong-signed; candidate explanation is overfitting on visible-test quirks. Report as null with a discussion. |

### Why this is a single primary hypothesis

Because the question is one question. Whether selection is a
filter or an amplifier is a single fact about the world.
Secondary comparisons (I vs N, I vs R, P vs N) are useful for
*context* and to spot implementation bugs in the arms, but only
one of them is the primary.

If we bundle multiple primaries (e.g., "I > P AND I > R"), we'd
be testing whether selection is an amplifier *and* whether it
beats random — two questions requiring different evidence. The
second is closer to "does the selector work at all" and is
addressed by Arm R's role as a sanity check, not as a primary.

## 4. Why this advances science

This experiment produces a result that is publishable independent
of whether it comes out positive or null:

- **Positive (selection is an amplifier):** Validates the design
  of every LLM-driven self-improvement system that uses an
  interactive evolve loop. Tells the field that the loop is
  load-bearing, not just bookkeeping.
- **Null (selection is a filter):** *Even more impactful.* Tells
  the field that the entire "evolve loop" paradigm in LLM
  self-improvement could be replaced with a much simpler
  "draw N candidates and re-rank" pipeline. This is a falsifiable
  claim with first-order implications for system design.
- **Surprising null (selection is worse than a filter):**
  Suggests overfitting on visible tests during in-loop iteration.
  A known pathology worth naming.

In all three cases, the result is a contribution. It's not
tuning exp001 to find some effect. It's a falsifiable question
about mechanism.

## 5. What's different from exp001 and exp002

| Variable | exp001 | exp002 | exp003 |
|---|---|---|---|
| Hypothesis | Does selection help? | Does selection help with a stronger model and tighter prompt? | Is selection a filter or an amplifier? |
| Arms | A/B/C | A/B/C | **N/P/I/R** (adds post-hoc re-rank) |
| Primary comparison | B vs A, B vs C | B vs A, B vs C | I vs P |
| Number of LLM calls | 300 | 300 | 400 |
| Pre-registered direction | B > A AND B > C | B > A AND B > C | I > P |

Everything else is held constant. Same benchmark. Same
hard-coded alpha. Same exact Mann-Whitney U test.

## 6. Implementation: how Arm P works

`forkling/experiment.py` needs a small new arm. Sketch:

```python
def arm_P_post_hoc_rerank(llm, task, k, rng):
    """K independent one-shot draws, then pick the one with the
    most visible tests passing. Same compute as Arm N (no
    iteration), different post-processing."""
    recs = arm_N_no_iterate(llm, task, k, rng)  # K independent draws
    # For each candidate patch, count how many visible tests pass.
    # Pick the best. Tie-break: first one in attempt order.
    buggy = (task.abs_path() / "buggy.py").read_text()
    candidates = []  # (visible_pass_count, attempt_idx, new_source)
    for rec in recs:
        if not rec.parse_ok:
            continue
        # ... grade the patch on visible tests, count passes
        candidates.append((score, rec.attempt_idx, new_source))
    candidates.sort(key=lambda x: (-x[0], x[1]))
    # The "kept" patch is the best one; record a synthetic committed
    # marker on that attempt.
    # ... return recs with committed=True only on the best one
    return recs
```

The harness invariant: arms N and P run the *same* LLM calls in
the *same order*. Only the post-processing differs. This keeps
the experiment well-controlled.

## 7. Stopping rule

K=10 attempts per task per arm = 40 attempts per task = 400 LLM
calls total. **No early stopping.**

Pre-registered failure modes:

- If parse_ok in any arm is < 0.50, the prompt fix didn't help
  and selection comparisons are confounded. Report as null with
  the parse_ok breakdown.
- If Arm R and Arm I have very similar commit_rates (e.g., the
  selector behaves like random), report as null and explicitly
  state "selection had nothing to select."
- If model timeouts affect > 20% of attempts in any arm, abort
  and report as null.

## 8. Statistical test

Paired Mann-Whitney U on per-task pass@5. One comparison: I vs P.
Alpha = 0.05 (no Bonferroni because there is exactly one primary
comparison).

Per-task pass@5 definition: 1 if any of the first 5 attempts
produced a patch that passed held-out tests. For Arm P, "any of
the first 5 attempts" means first 5 of the K independent draws;
the post-hoc re-ranking is applied to whichever of the K the agent
"chooses to return" but pass@5 is just about whether *any*
attempt worked — the post-processing only affects commit and what
gets recorded as the "final patch."

Use the exact permutation distribution for N=10, implemented in
`forkling/experiment.py:mann_whitney_u`. No correction needed.

## 9. Reproducibility

```bash
python bench/validate_bench.py  # benchmark still frozen
python -m forkling experiment run \
    --bench bench/FORKLAND-BENCH-001.jsonl \
    --k 10 --model qwen2.5-coder:7b \
    --seed 20261025 \
    --arms N,P,I,R \
    --out results/exp003.json
```

**Note on model:** this pre-registration assumes exp002 confirms
the model works with the new prompt schema. If exp002's prompt
fix didn't fully resolve the parse issue, exp003 falls back to
`llama3.2:3b` with a known caveat. Either way, the *hypothesis*
is preserved.

Wall time on qwen2.5-coder:7b (warm): ~12s cold + ~0.5s × ~399
≈ 3.5 min. Tractable.

## 10. What I expect (NOT a hypothesis)

My calibrated guess, with the caveat that this is prior not
posterior:

- Arm P likely matches or beats Arm N (re-ranking at least
  catches the cases where one of K independent draws was lucky).
- Arm I likely matches Arm P closely, since both end up with the
  best-K visible-test-passing patch (modulo how the running state
  affects later draws in Arm I).

If pass@5(I) ≈ pass@5(P) ≈ pass@5(N), selection is just a filter
in this configuration. That's the scientifically informative
null.

If pass@5(I) > pass@5(P), selection is providing some in-loop
amplification. We could then probe (in a future experiment) how
much of that is running-state vs prompt-context vs something
else — but that's a separate pre-registration.

## 11. Reporting

Single result file `results/exp003.json`. Companion writeup
`paper/exp003_results.md` with the same structure as
`exp001_results.md`, explicitly stating:

- Whether exp003 replicates or breaks the exp001/exp002 null.
- Whether pass@5(I) > pass@5(P) per the pre-registered test.
- The interpretation per the rules in §3.
- Discussion of arm P's new role as a "filter" baseline.

---

**Sign-off:** This document is frozen at the commit that introduced
it. The hypothesis is **falsifiable, mechanism-driven, and
publishable in either direction**. We did not write it to confirm
selection; we wrote it to find out whether selection is a filter or
an amplifier.
