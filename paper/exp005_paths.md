# Path Assessment — exp005 from the Deferred exp004

**Status:** v0.1 draft, 2026-09-27
**Premise:** exp004 was deferred per v4r1 §6 (calibration produced
only 3/12 survivors; the 6-survivor floor was not met). The
writeup at [`paper/exp004_results.md`](exp004_results.md) listed
four candidate next-attempt paths. This document assesses each on
three axes (feasibility, discipline compatibility, expected value)
and recommends one consolidated exp005 design.

---

## The four paths (as listed in exp004_results.md)

- **Path A** — relax the freeze band downward.
- **Path B** — re-author the candidate pool (more algorithm-heavy tasks).
- **Path C** — escalate the model (qwen2.5-coder:7b).
- **Path D** — re-register the question (drop arms, change unit of replication, etc.).

The natural question is: can we take all four? Yes, in the trivial
sense that they are short strings in markdown and don't fight at
the keyboard level. No, in the sense that each path proposes a
**different experimental design** and we can run only one next
experiment at a time. The real question is whether the four paths
*combine* into a single better design, or whether exactly one of
them is the right fix.

Verdict (read below): the data favours a single consolidated exp005
that takes Path B as the main lever, rejects Paths A and D on
discipline grounds, and folds Path C in as a pre-registered
model-escalation fallback if Path B alone is insufficient.

---

## Path A — relax the freeze band

**What it is.** Modify the v4r1 §6 freeze rule from
`0.10 ≤ p1 ≤ 0.50` to e.g. `0.05 ≤ p1 ≤ 0.55`. The pre-registered
freeze logic in `scripts/freeze_bench_002.py` is updated to match,
and a new calibration cycle is run on the existing 12-candidate
pool.

**Feasibility.** Trivial. Mechanical change.

**Discipline compatibility.** **Strongly negative.** The
pre-registration in v4r1 §6 says the freeze rule is a *script*
committed before calibration runs, with no human judgment
involved. Modifying the rule after seeing the rule do what it
was supposed to do (correctly refuse to freeze a miscalibrated
benchmark) violates the discipline that exp004 was specifically
designed to enforce. The fix would be invisible in the headline
result but obvious to anyone reading the diff.

**Expected value.** Low. The calibration outcome was not "the band
was too narrow" — it was "9 of 12 candidates land outside the band
in *both* directions." Widening the band makes the survivors
distribution bimodal-only-wider. Calibration would still be
deferred.

**Verdict.** Reject.

---

## Path B — re-author the candidate pool

**What it is.** Author 8–10 *algorithm-heavy* candidates similar
to 006 (merge intervals), 008 (flatten), 011 (search-insert),
keeping 4–5 of the existing parser-heavy candidates as control
contrast. Replace `FORKLAND-BENCH-002-candidates.jsonl` with the
expanded pool. Re-run calibration.

**Feasibility.** Modest cost. Authoring tasks is mechanical but
each needs `prompt.md` + `buggy.py` + `expected.py` + `visible_tests.py`
+ `held_out_tests.py`. The 006 / 008 / 011 templates are good
seeds. Strict validation must pass.

**Discipline compatibility.** Good. v4r1 §6 allows re-authoring
the candidate pool before re-calibration (the freeze rule applies
to whatever is in the pool; the pool itself is not frozen until
the freeze commit). The audit's "candidates must not describe the
bug" + "buggy.py must fail held-out" + "≥1 visible test fails on
buggy" + "≥3 held-out tests, ≥1 not covered by visible" constraints
all carry over.

**Expected value.** Strong — directly aligned with the calibration
data direction.

The exp004 calibration table told us exactly what is missing:

| p1 band | Current pool | After Path B (estimated) |
|---|---|---|
| 0.00 | 9/12 | 4-5/20 |
| 0.05–0.10 | 0 | 2-3/20 |
| 0.10–0.50 | 3/12 (the 006/008/011 cluster) | 10-13/20 |
| 0.50–1.0 | 0 | 0 (don't want any) |

Algorithmic tasks populate the band precisely because the model's
known strength is algorithm-synthesis over string-manipulation. This
is what the calibration told us to expect.

**Verdict.** Strong recommendation. This is the path the data
wants.

---

## Path C — escalate the model

**What it is.** Run the calibration and main experiment on a
stronger coder (qwen2.5-coder:7b or qwen3:4b) instead of
qwen2.5-coder:3b. Re-use the existing candidate pool or an
expanded one.

**Feasibility.** Blocked on current hardware. qwen2.5-coder:7b
partial-offloads on 4 GB VRAM (RTX 2050), causing 5–6 s per call
instead of 0.7 s — empirically unworkable per `MODEL_DECISION.md`.
qwen3:4b fits in 4 GB VRAM but is not coder-specific. Either:

- Rent cloud compute (e.g. Lambda 1×A10 24 GB ≈ $0.60/hr, ~$5 for a
  full exp004-equivalent run). Doable, but introduces a
  reproducibility layer (cloud GPU is not part of the protocol v1
  spec).
- Acquire different hardware. Out of scope for this work.

**Discipline compatibility.** Good. v3/v4 have explicit
model-swap clauses; the hypothesis is "model changes are not
hypothesis changes." A new pre-registration naming the model
specifically preserves the discipline.

**Expected value.** Medium. A bigger model probably *would* shift
*p1* rightward and populate the band, but:

- We can't empirically verify on this hardware, so the calibration
  is hypothetical until we run it.
- The mechanism question (I vs P) is interesting either way.
  Inflating *p1* to "model dominates one-shot and the loop has no
  headroom" brings back the FORKLAND-BENCH-001 floor effect — the
  very thing exp004 was designed to avoid.

The combination of "blocked on hardware" + "doesn't address the
diagnosis" + "risks re-introducing floor effect" makes Path C
*not* the main fix. But it could be a fallback after Path B if
the augmented pool still doesn't populate the band.

**Verdict.** Defer; allow as pre-registered fallback in exp005.

---

## Path D — re-register the question

**What it is.** Drop arm R (random accept, currently a sanity
check), drop arms with the same baseline (N vs P is informative,
P vs N is filtered), change replication (more replicates,
fewer tasks), or pose a different mechanism question entirely
(e.g. "does in-loop feedback help at any K" instead of "filter
vs amplifier").

**Feasibility.** Trivial.

**Discipline compatibility.** Good. New pre-registrations are
allowed at any time.

**Expected value.** Low for *this* calibration outcome. The
mechanism question is still open (no class-M answer from exp001–003;
no class-V answer from exp004 because exp004 didn't run). A
better-fitted benchmark with the same question is more valuable
than a different question on the same evidence. The audit gave
us protocol-2 fixes — those should be tested on a properly
calibrated benchmark, not on a different one.

**Verdict.** Reject for the immediate next step. Worth
considering later, on its own merits, after exp005 produces a
result.

---

## "Can we not take all four?"

In the trivial sense, yes — they are independent text.

In the operational sense, no — at most one of A/B/C/D can be the
**main lever** of exp005, because each one changes a different
parameter (band, pool, model, question). The four are not
orthogonal alternatives; they are alternative fixes for the
calibration failure.

What is *possible* — and recommended — is to fold the viable
elements into a single consolidated exp005 pre-registration:

- **Path B** as the main lever (re-author the pool to add
  algorithm-heavy candidates).
- **Path A** explicitly rejected (discipline-bad; the freeze rule
  stays at `[0.10, 0.50]`).
- **Path C** as a pre-registered model-escalation fallback if
  Path B alone does not populate the band. v3/v4 model-swap clause
  applies; exp005 pre-registers the model decision as a function of
  the calibration outcome.
- **Path D** rejected (question stays put).

---

## Recommended consolidated exp005 design (high-level)

**Pre-registration doc:** `paper/hypothesis_v5.md`, signed off
before any new pilot data is viewed.

**Question:** identical to v4r1 — *"Is selection pressure on
LLM-generated patches a filter or an amplifier?"* Primary
comparison I vs P. Same mechanism, same arms (N, P, I, R). Same
endpoint (returned_pass, 5 replicates). Same statistical test
(Wilcoxon signed-rank + bootstrap CI).

**Candidate pool:** `FORKLAND-BENCH-002-candidates.jsonl`. Replace
the existing 12 candidates with a new pool of 18–22 candidates,
roughly:
- 4–5 algorithm-heavy tasks like 006/008/011
- 4–5 *mid-difficulty* algorithm tasks (binary search variants,
  small graph algorithms, balanced trees on small inputs)
- 3–4 parser tasks *with a clearer visible-test signal* than the
  current ones (so the model gets feedback that helps the loop)
- 3–4 control tasks (1–2 trivial, 1–2 hard-impossible) for sanity
  All candidates pass `bench/validate_bench.py --strict`.

**Freeze rule:** identical to v4r1 §6. *Do not relax the band.*
The discipline matters more than getting a result one cycle
faster.

**Stopping rule:** K=20 for calibration (unchanged); K=10 for the
main run with S=5 replicates per (task, arm) (unchanged).

**Model:** *qwen2.5-coder:3b* is the primary model. The model
decision is registered *as a function of the calibration outcome*:
- If the augmented pool produces ≥ 6 survivors in the band,
  main run uses 3b (Path C off; hardware no constraint).
- If the augmented pool produces < 6 survivors, *the model is
  escalated to a stronger coder* before the main run, with the
  hardware requirement (≥16 GB VRAM for 7b) pre-registered in
  advance. This is the model-swap clause from v3/v4, re-applied.

**Harness self-test gate:** `tests/test_experiment_power.py` 14/14
must pass at the commit that produces the calibration data. Same
as exp004.

**Reporting:** `results/exp005.json` + `paper/exp005_results.md`
following the same template as exp003_results.md /
exp004_results.md. Calibration table; primary test and effect
size; secondaries labelled exploratory; interpretation per the
v4r1 rules table; explicit statement of which path(s) above were
the levers.

**If exp005 also defers:** the failure mode is informative — at
that point, "FORKLAND-BENCH-002 cannot be calibrated for this
model on this hardware with this harness" is a publishable
finding *as long as we report it honestly*. The pre-registration
must include an honest-failure reporting clause.

---

## Concrete sequence to ship exp005

1. Pre-register `paper/hypothesis_v5.md` (no pilot data viewed).
2. Author the augmented candidate pool (Path B). Pass strict
   validation.
3. Re-run calibration on the augmented pool (12 → 18-22 candidates,
   360-440 LLM calls at K=20, ~6-8 minutes).
4. Apply freeze (script, no judgment). Either ≥ 6 survivors
   → proceed to main run with 3b, or < 6 survivors → escalate to
   7b (Path C fires).
5. Main run (≤ 22 tasks × 4 arms × 5 reps × 10 calls = 4400 calls,
   ~ 50 minutes on 3b or ~ 6 hours on 7b).
6. Write up. Commit. Push. Submit real proposals for reals.

Total wall time: 2-3 hours of work over 1-2 calendar days at
3b-only; longer if Path C fires.

---

## What we are *not* doing

- **Not** running exp005 *today* in this writeup. This document
  is the assessment, not the experiment. exp005 needs its own
  pre-registration committed before any pilot data is viewed.
- **Not** deciding the model-swap threshold unilaterally. The
  pre-registered "model decision is a function of the
  calibration outcome" is the discipline-respecting version.
- **Not** re-running exp004 on the existing pool. exp004 is
  closed; it deferred; reopening it would move goalposts.
- **Not** modifying the `[0.10, 0.50]` band to force the existing
  pool through freeze. That would be Path A. We rejected Path A.

---

## Sign-off

2026-09-27. Four paths reviewed. Three rejected (A: discipline-bad;
C: blocked on hardware + risks floor effect; D: wrong question).
One recommended (B: re-author the candidate pool, mid-difficulty
algorithm-heavy tasks). One consolidated exp005 design proposed
that folds the viable elements together.

Next action: I will draft `paper/hypothesis_v5.md` for review
before any pilot data is viewed, per the discipline. Tell me to
proceed and I will write it; tell me to redirect and I will stop.
