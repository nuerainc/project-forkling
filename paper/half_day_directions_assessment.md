# Half-Day Novel Directions — Assessment Memo

**Date:** 2026-09-28
**Author:** Jeremy Beebe (with assistance from the agent)
**Status:** ASSESSMENT ONLY. None of these experiments has
been pre-registered or run. This memo ranks them by value
and effort, identifies the most publishable, and flags the
design risks per direction.

---

## Context

The mechanism case (filter-only, P − N = +0.545, p = 0.0005,
n = 12 across two seeds, FORKLAND-BENCH-002, qwen2.5-coder:3b,
temperature 0.8) is closed. exp003b closed as floor-effect on
FORKLAND-BENCH-001. exp008 closed as envelope-bounded on
model-change. The next-move question is: which novel
directions are worth pursuing in a half-day budget?

This memo assesses four candidate directions, ranked by
publishability and novelty, with design effort, run cost,
falsifiability, and risk per direction.

---

## Direction 1 — Cumulative Improvement (Multi-Round In-Loop)

**Question:** does the filter effect *accumulate* over
rounds, or is it one-shot?

**The current mechanism finding is one-shot.** exp006 + exp007
ran K=10 independent draws per (task, arm, replicate) and
compared returned_pass across arms. The result is "filter
helps: re-ranking 10 draws picks a better patch than picking
the first one." But forkling's actual claim is **temporal**:
the in-loop selector keeps applying patches, each informed by
the previous, and accumulates improvement across rounds.

**What this tests:** if we run the in-loop arm (I) for
T = 5 rounds, where each round accepts the best of K=10 draws
and re-prompts with the new state, does the final patch
quality exceed what one round of K=10 or what K=50
independent draws would produce? If yes, the filter
*accumulates*. If no, the filter is one-shot and the loop
adds no value beyond what a single re-rank provides.

**Endpoint:** `cumulative_pass` — whether the final patch
after T rounds satisfies held-out tests. Per-round
intermediate `returned_pass` reported for trajectory
analysis.

**Design effort:** ~2 hours to extend Protocol 2 with a
multi-round mode and define the round-reset semantics
(discard the prompt history between rounds? carry the
running source? re-prompt with original buggy.py?).
The original exp003 audit found M2 (in-loop prompt
decoupled from running source) as a real failure mode;
v9 must specify which mode to use, with rationale.

**Run cost:** ~30 min × 1 cell (6 tasks × 1 arm × 5 reps ×
T=5 rounds × K=10 calls per round = 1500 calls). Plus a
control arm: K=50 independent draws (the "all-at-once"
upper bound) to establish the ceiling.

**Falsifiability:** clean. If cumulative_pass after T=5
rounds is statistically indistinguishable from K=50
independent draws' best-of-50, the mechanism is one-shot
and the loop adds nothing. If cumulative_pass exceeds
K=50 best-of-50, the loop *does* add value.

**Expected outcomes:**
- Loop beats K=50 best-of-50: **mechanism is temporal**;
  forkling's loop claim is supported.
- Loop ties K=50 best-of-50: mechanism is one-shot; loop
  is just a less efficient way to do re-rank.
- Loop is worse than K=50 best-of-50: loop *hurts*; the
  in-loop arm has a hidden cost (e.g., mode collapse from
  over-conditioning on prior patches).

**Novelty:** **highest.** This is the question forkling's
actual autonomy claim depends on. exp001–exp008 all test
the one-shot mechanism. None tests cumulative.

**Risk:** medium. The protocol extension (multi-round mode)
is non-trivial and may need its own harness self-test. The
M2-style failure mode (decoupled prompt) is a known risk
that needs explicit registration.

**Recommendation:** **Direction 1 is the most valuable
half-day novel direction.** It directly addresses forkling's
core claim. The protocol-extension risk is the main cost,
but it's a one-time investment that future experiments
re-use.

---

## Direction 2 — Cross-Task-Class Replication

**Question:** is the filter effect specific to
algorithm-heavy tasks, or does it generalize across task
classes?

**The current finding is on FORKLAND-BENCH-002** (six
tasks, all algorithm-heavy: merge-intervals, flatten,
insert-position, wrap-text, binary-search, rotate-array).
The mechanism might be task-class-specific: algorithm-heavy
tasks have structured solutions that an LLM is good at
proposing, and the filter surfaces the best one. Other task
classes (string manipulation, data-structure bugs,
recursion-heavy tasks) might not benefit from the same
filter because the patch space is different.

**What this tests:** does the filter effect transfer to a
different task class? If yes, the mechanism is
task-class-invariant. If no, the mechanism is
algorithm-heavy-specific.

**Endpoint:** same as v6/v7 (`returned_pass`). Same
statistics.

**Design effort:** ~2-3 hours to author a 4-6 task
mini-benchmark in a different class. Options:
- String manipulation (e.g., "reverse-words", "anagram-group",
  "longest-palindromic-substring")
- Data-structure bugs (e.g., off-by-one in a list slicing,
  hash collision in a dict, BST traversal)
- Recursion-heavy (e.g., Fibonacci, factorial, tree traversal)

Plus a calibration run on the new mini-benchmark to ensure
arm N pass@5 lands in [0.10, 0.50] (per exp005's Path B).

**Run cost:** ~30 min main run + ~10 min calibration =
~40 min for one cell.

**Falsifiability:** clean. Per-task Wilcoxon + combined-
sample. Same protocol as v6.

**Expected outcomes:**
- Filter replicates (P > N, p<0.05): **task-class-
  invariant**; mechanism generalizes.
- Filter null: **task-class-specific**; mechanism is a
  property of algorithm-heavy tasks only.
- Filter reverses (P < N): surprise; would require
  re-examination.

**Novelty:** high. Cross-task-class generalization is a
natural next step from "filter works on this benchmark"
to "filter works in general." This is what reviewers will
ask about.

**Risk:** high on calibration. A new mini-benchmark has a
high chance of either floor effect (like exp003b) or
ceiling effect (like exp001). The calibration step would
catch this but adds design iteration.

**Recommendation:** Direction 2 is **most publishable**
after Direction 1. The risk is calibration, but if it
passes, the result is clean.

---

## Direction 3 — Harder Benchmark (Upper-Bound Test)

**Question:** does the filter effect hold at the upper
bound of task difficulty, or is it bounded to mid-difficulty?

**FORKLAND-BENCH-002 was calibrated to p1 ∈ [0.10, 0.50]
in arm N** — that's the "non-trivial but not too easy"
band. The mechanism might require that band specifically:
if tasks are too easy (p1 > 0.50), all arms pass and the
filter has nothing to do (floor effect). If tasks are too
hard (p1 < 0.10), all arms fail and the filter has nothing
to surface. The mechanism might only operate in the
calibration band.

**What this tests:** does the filter hold when arm N's
p1 ∈ [0.05, 0.20] — a harder band where most draws fail
but a few succeed? This tests the upper-bound difficulty
regime.

**Endpoint:** same as v6/v7.

**Design effort:** ~2-3 hours to author harder tasks
(closer to SWE-bench-style difficulty) or pull from an
external benchmark. Authoring is preferred (calibration
control) but harder.

**Run cost:** ~30-50 min main run + ~10 min calibration.

**Falsifiability:** clean.

**Expected outcomes:**
- Filter replicates: **mechanism is robust across
  difficulty regimes**.
- Filter null: **mechanism is band-bounded**; only works
  in mid-difficulty.
- Filter reverses: surprise.

**Novelty:** medium. Tests an extension of the existing
finding but doesn't address the cumulative claim
(Direction 1) or the task-class-generalization claim
(Direction 2).

**Risk:** high on calibration. Harder tasks might push
arm N pass@5 below 0.05, making the test meaningless.
Multiple calibration iterations may be needed.

**Recommendation:** Direction 3 is **least publishable**
of the four. It extends the existing finding in a
straightforward way but doesn't address a new mechanism
question.

---

## Direction 4 — Alternative Ranker

**Question:** does the filter effect require an LLM-based
semantic ranker, or does it hold for any reasonable
selection mechanism?

**The current filter uses visible_test pass-rate as the
ranking signal** (per v6 §3). That's a structural test:
"did the patch make the visible tests pass?" But other
rankers exist:
- Random (baseline): would lose all signal.
- Edit-distance to expected.py: structural similarity.
- Static-analysis features (lines changed, syntax validity).
- A different LLM judge: "does this patch look correct?"

**What this tests:** is the filter effect a property of
*visible-test rankers*, or does it generalize to other
selection signals? If a non-LLM ranker also produces
filter-only, the mechanism is ranker-agnostic. If only
visible-test ranking produces the effect, the mechanism
is ranker-specific.

**Endpoint:** same as v6/v7.

**Design effort:** ~1-2 hours to implement a non-LLM
ranker. Options:
- Edit-distance ranker: compute Levenshtein distance from
  patch to expected.py's fix; rank by inverse distance.
- Static-analysis ranker: parse the patch, validate syntax,
  rank by AST validity + visible-test pass.
- Hybrid: visible-test pass (binary) + edit-distance
  (continuous) as a 2-D score.

**Run cost:** ~30 min main run × 1 cell.

**Falsifiability:** clean. Replace the ranker, run the
protocol, see if filter holds.

**Expected outcomes:**
- Filter replicates with non-LLM ranker: **ranker-
  agnostic**; mechanism is selection-in-general, not
  LLM-specific.
- Filter nulls: **ranker-specific**; the visible-test
  ranker has a property other rankers don't (perhaps
  the test-passing rate is itself a low-quality signal
  and the filter's effectiveness depends on something
  particular to it).
- Filter reverses: surprise.

**Novelty:** high. Tests the *generality* of the
mechanism claim. Closely related to v8 (model-change)
but orthogonal: v8 asked "is the filter specific to the
model that generates patches?" Direction 4 asks "is the
filter specific to the ranker that selects them?"

**Risk:** medium. The non-LLM ranker implementation
needs care to be a fair comparison — it should have
access to the same information (visible tests) but
use a different scoring function.

**Recommendation:** Direction 4 is **second-most
valuable** after Direction 1. It's a clean test of
mechanism generality, and the result is directly
relevant to forkling's claim (since forkling uses
visible-test ranking as the ranker).

---

## Ranking Summary

| Direction | Novelty | Publishability | Risk | Wall-Clock |
|---|---|---|---|---|
| **1. Cumulative improvement** | **highest** | **highest** | medium (protocol extension) | ~half day |
| 2. Cross-task-class | high | high | high (calibration) | ~half day |
| 4. Alternative ranker | high | medium-high | medium (impl) | ~half day |
| 3. Harder benchmark | medium | medium | high (calibration) | ~half day |

**Top recommendation:** Direction 1 (cumulative
improvement). It is the most novel, addresses forkling's
core claim, and produces a publishable finding either way
(loop adds value vs. loop is one-shot). The protocol-
extension risk is the main cost.

**Second recommendation:** Direction 4 (alternative
ranker). It's a clean mechanism-generality test, and the
implementation is the cheapest of the four.

**Run together:** Directions 1 and 4 are complementary —
1 tests the temporal axis, 4 tests the ranker axis.
Running both in a single half-day is feasible if the
Direction 1 protocol extension is staged early.

---

## What this memo is *not*

- Not a pre-registration. None of these experiments has
  been registered yet.
- Not a commitment to run any of them. The user (Jeremy)
  decides which to pursue based on this assessment.
- Not a substitute for the existing mechanism finding.
  Directions 1–4 are extensions; the case on
  FORKLAND-BENCH-002 is closed independently.

---

## Pre-registration plan (when a direction is chosen)

When the user picks a direction, the next step is:
1. Author `paper/hypothesis_v10.md` (or `v10` if combining
   with v9, or a higher number) with the chosen
   direction's full pre-registration.
2. Commit before any pilot data viewed.
3. Implement any protocol extensions and add a harness
   self-test case.
4. Run the experiment with watchdog restarts using
   `--resume-from`.
5. Write up per the registered interpretation table.

The discipline is the same as v6/v7/v8/v9: pre-register
before data, apply registered rules literally, accept
honest nulls.
