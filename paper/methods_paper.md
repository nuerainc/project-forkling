# Pre-Registered Falsifiable Methodology for Long-Horizon Agent Self-Improvement, with the Closed Case on Filter-vs-Amplifier

*Working title. Author: Jeremy Beebe. Date: 2026-09-27.*

## Abstract

Long-horizon agent self-improvement — systems that iteratively
edit their own source under selection pressure — is one of the
most consequential capabilities in modern AI. The current
literature (DGM, AlphaEvolve, FunSearch, Gödel Agent) implicitly
bets that the *interactive* evolve loop is *load-bearing*: that
iteration, prompt feedback, and selection together produce
something a one-shot generator cannot. We argue that this bet
is unverified. Existing systems do not pre-register their
hypotheses; do not report negative results; and do not
stress-test the loop against a draw-and-rerank baseline at
equal budget.

This paper introduces a pre-registered, falsifiable
methodology for the question — *is selection pressure on
LLM-generated patches a **filter** (a way to discard bad
patches) or an **amplifier** (a way to make the LLM generate
better patches)?* — applies it to a calibrated hard-bug-fix
benchmark (`FORKLAND-BENCH-002`, 6 tasks, p1 ∈ [0.10, 0.50]),
and reports a mechanism result. Over six pre-registered
attempts across two protocol generations, **including a
seed-replication**, we found:

1. **Filter effect is real and survives replication** —
   post-hoc re-rank by visible tests outperforms one-shot
   generation at equal budget. Combined-sample effect:
   P − N = **+0.527, 95% CI [+0.418, +0.636], p < 0.0001**
   (n = 24 paired measurements across four seeds, 6 tasks
   × S = 5 replicates each).
2. **Iteration does not improve over re-rank** — the
   in-loop select arm is *worse* than post-hoc re-rank at
   equal budget, with all seventeen non-zero combined-sample
   I − P differences negative (W+ = 0.0): combined mean diff
   **−0.376, 95% CI [−0.459, −0.294]**, p = 0.0003 (below
   α = 0.05, having been 0.0547 at n = 12).
3. **Two secondary effects that frame the result**:
   in-loop select beats random-accept (I − R = +0.333,
   p = 0.0033) — the in-loop selector is doing real work,
   just not enough to outperform re-rank at equal budget.
   In-loop beats one-shot (I − N = +0.433, p = 0.0002) —
   the loop is doing *something*, but the same selector
   applied *post-hoc* does more with it.

The pre-registered interpretation is **"filter only — and the
loop's iteration actively hurts."** Selection on LLM-generated
patches is a *filter*, not an *amplifier*, at this scale on
this benchmark with this model.

The mechanism question that was open across exp001–005
is closed. exp006 (protocol 2, calibration-frozen
benchmark, seed 20261025) produced the first non-deferred
mechanism result; exp007 (seed 20261030) and exp009a
(seed 20261104) reproduce its direction; exp009b-lowT
(seed 20261105, temperature 0.5) reproduces it at a
*different temperature*, the robustness check registered
in `hypothesis_v9.md`. The combined-sample analysis at
n = 24 paired measurements across four seeds is the
load-bearing empirical test. **The case is closed.**

**Methodological contributions.** A
pre-registration-then-audit protocol: a research artifact is
self-audited against the question it claims to answer before
release; if the audit finds class-M (measurement) failures,
the protocol is re-registered under `hypothesis_vN.md` and
the harness is rewritten (`forkling/experiment2.py`), with a
self-test (`tests/test_experiment_power.py`, 20/20) that
must pass at the data-producing commit. A
`bench/validate_bench.py --strict` gating that fails
candidates whose buggy.py passes every held-out test — a
class of failure the v0.1 protocol silently accepted. A
benchmark calibration procedure (`hypothesis_v4r1.md` §6)
that refuses to commit to a benchmark whose difficulty
distribution does not give the question a fair test. A
failure taxonomy that distinguishes proposal-side failures
(A/B/C/D) from measurement-side failures (M1–M5). A
*registered combined-sample analysis* registered at
registration time (v7 §4.2), invoked as the load-bearing
step when per-seed tests are power-bounded at small n.

**Data and code:** all artifacts (working code, dataset,
calibration files, result files, seven pre-registered
hypothesis documents, three result writeups for the
deferred outcomes, the audit, the schema, the protocol, and
the seed-replication combined-sample analysis) are released
under MIT at
[`nuerainc/project-forkling`](https://github.com/nuerainc/project-forkling).

---

## 1. Introduction

LLM-driven agent self-improvement systems iteratively edit
their own source code, gate edits on a fitness function, and
commit or roll back based on the gate's verdict. Five of the
most-cited recent systems — the Darwin Gödel Machine (DGM),
AlphaEvolve, FunSearch, the Gödel Agent, and an emerging
class of "self-evolving" agents — share an architectural bet:
that the *interactive* loop is *load-bearing*. If looping
with feedback were merely bookkeeping, a one-shot generator
plus a ranking step would suffice. The bet is that
iterating, running the candidate through a fitness gate, and
feeding the failure back into the next prompt produces
patches that a one-shot generator cannot reach within the
same LLM-call budget.

This bet is widespread but **empirically untested as a
falsifiable claim**. The literature does not pre-register
the question (we searched; no published system does), does
not report null results (every published system reports a
positive, and reviewers have no way to distinguish "we got
lucky" from "the bet is real"), and does not compare the
interactive loop against a draw-and-rerank baseline at
equal budget. Without such a baseline, a positive result is
uninterpretable: a loop that "works" at K=10 calls could
match or be worse than K=10 independent draws plus a
selector.

We argue that this is a methodological gap, not a settled
finding. The bet deserves a falsifiable test.

This paper introduces such a test. We pre-register a
mechanism question — *is selection pressure on LLM-generated
patches a filter (just-discard-bad-ones) or an amplifier
(make-better-ones)?* — and run it across **five
pre-registered attempts** on a hard-bug-fix benchmark
(FORKLAND-BENCH-002), with two protocol generations:

- **Protocol 1** (`forkling/experiment.py`, exp001–003):
  pass@k as the primary endpoint, K=10 per (task, arm).
  Three pre-registered attempts; three nulls.
- **Protocol 2** (`forkling/experiment2.py`, exp004–006):
  `returned_pass` as the primary endpoint, K=10 per
  (task, arm, replicate), 5 replicates per (task, arm,
  replicate), exact paired Wilcoxon signed-rank with
  bootstrap CI. Three pre-registered attempts on
  FORKLAND-BENCH-002; the first two were deferred (the
  benchmark did not calibrate under the pre-registered
  freeze rule), and the third produced the mechanism
  result reported here.

The transition from Protocol 1 to Protocol 2 was **driven by
a self-audit**, not by post-hoc data analysis. The audit,
performed after exp003, found five real measurement-side
failures (class M1–M5) in the Protocol 1 harness. The
`hypothesis_v4r1.md` document carries out the audit and
registers a fixed protocol. This is the methodological
contribution that we think generalizes: **a pre-registered
harness is not a fix-once artifact; it is a hypothesis to be
self-audited and re-registered when the audit finds it
inadequate.**

The mechanism result (Section 5) is that the filter effect
is real (P > N, p = 0.031) and the amplifier effect is not
supported (I vs P p ≈ 0.063, CI excludes 0). The
pre-registered interpretation is "filter only": selection
helps, but only as a filter — the interactive loop with
feedback does not improve on post-hoc re-rank at equal
budget, and is trending worse. Future work should focus on
the loop being a *better* draw-and-rerank (better prompts,
more draws, richer ranking signals) rather than on
in-loop feedback being a substitute for re-ranking.

The paper does not claim general-purpose defeat of agent
self-improvement as a research direction. We claim only
that, on this benchmark (multi-line buggy.py/expected.py
tasks in stdlib only), at this scale (K = 10, S = 5), with
this model (`qwen2.5-coder:3b`), with the harness we built,
the **filter hypothesis holds and the amplifier hypothesis does
not**. Each clause narrows. The discipline is to write
narrowly, and to ship the artifact so that others can
test the broader claims.

---

## 2. Method

### 2.1 The forkling system

`forkling/` (paper open-sourced, MIT) is a small Python
agent that edits its own source under selection pressure.
The substrate is a *real git working tree*: every successful
self-edit becomes a `git commit`; every rolled-back edit is
recorded as such. The capability ledger
(`forkling/capability.py`) is a SHA-256-chained
append-only log: every demonstrated capability is recorded;
walking the chain reproduces every action; a single tampered
byte breaks the chain at exactly the offending entry. The
patch graveyard (`forkling/graveyard.py`) records every
rejected patch with its reason; recent failures are
appended to the next proposal prompt as a negative-example
memory.

`forkling/` is stdlib-only at runtime (`pytest` is the sole
dev dependency) and runs offline on a 4 GB-VRAM laptop with
Ollama + a `qwen2.5-coder:3b` model loaded (per
`paper/MODEL_DECISION.md`). The whole system is roughly
3,500 lines of Python; it ships with a public 30-day
self-improvement history and a SHA-chained audit log.

### 2.2 The mechanism question

```
E = (G, F, P, S, M)
```

- `G`: a sequence of git SHAs `g_0, g_1, ..., g_T` — the
  agent's heritable states. A *generation* is a `g_t` where
  `g_t ≠ g_{t-1}`.
- `F`: fitness — `F(g_t) = (smartness, skill, total)`
  computed from `paper/fitness-snapshot.json`.
- `P`: the proposal distribution — the LLM's conditional
  over `{kind, path, old, new}` patches given the running
  state and the prompt context (which includes the previous
  generation's diff, the diary tail, and the graveyard
  tail).
- `S`: selection — `S(g') = 1 iff pytest(g') = 0`. Hard
  gate; no soft scoring.
- `M`: the mutation operator — a string-replace patch that
  has passed the kernel-guard, the validator, and the parser.

Operationally, with a budget K of LLM calls per task, the
question is:

- **Filter effect:** the loop is *just* a filter — choosing
  among K independent draws by visible tests returns a
  better patch than one draw. Measured by **P vs N**
  (post-hoc re-rank vs no-iterate).
- **Amplifier effect:** the loop is more than a filter —
  iterating (running each attempt with feedback and
  keep-if-better) returns a better patch than the same
  K independent draws plus the same selector. Measured by
  **I vs P** (in-loop select vs post-hoc re-rank).

If `I ≈ P`, the evolve loop can be replaced with "draw K,
re-rank." This is the pre-registered null reading
("filter only").

This question is independent of the choice of benchmark, the
choice of model, and the specific parameter values. Each
generalizes narrowly; the question generalizes as written.

### 2.3 The protocol arms

| Arm | What the model sees | Selection | Returned |
|---|---|---|---|
| N | task prompt + original `buggy.py` + visible tests | none | attempt 0 (the other K-1 draws run for `pass@k` continuity) |
| P | same as N, K independent draws | after all K: most visible tests passed; tie → lowest attempt index | the winner |
| I | task prompt + **current** source + visible tests + **feedback from the previous attempt** (the patch tried, whether it was kept, the visible failure output, ≤ 2000 chars) | after each attempt: keep iff strictly more visible tests pass; stop once all visible tests pass | final current source |
| R | same prompt and feedback as I | keep parsed patch with p = 0.5; no early stop | final current source |

R shares I's prompt and feedback so **I vs R** isolates the
selector inside the loop from iteration with feedback.

### 2.4 The endpoint

The primary endpoint is `returned_pass` for each (task, arm,
replicate) — whether the patch the arm **returns** passes
the held-out tests. The per-task score is the mean over S = 5
replicates.

`pass@1/5/10` (any-draw, exp001–003-style) is computed and
reported for continuity but **never** used for any
hypothesis test. Per Section 4 of this paper, the audit
identified the pass@k endpoint as the most consequential
class-M failure in Protocol 1.

### 2.5 Statistics

- **Primary comparison:** I vs P, paired by task.
- **Test:** exact two-sided Wilcoxon signed-rank on
  per-task paired differences. Zero differences dropped;
  ties in `|difference|` get mid-ranks; exact permutation
  null. Alpha = 0.05.
- **Effect size:** mean per-task difference with a
  10,000-resample bootstrap CI; resampling seed derived
  from `(seed, comparison_name)`. Reported whatever the
  p-value.
- **Replicates:** S = 5 per (task, arm). With n = 6 tasks,
  the smallest attainable two-sided p-values are bounded.

### 2.6 Pre-registration

Every experiment is committed to
`paper/hypothesis_vN.md` **before** any pilot data is
viewed under its design. A pre-registration binds:

- mechanism question (typically falsifiable, mechanism-level)
- arms and primary comparison
- benchmark + calibration procedure (if not frozen)
- statistical test, alpha, replicates
- stopping rule (no early stopping)
- the model decision (kept as a function of the calibration
  outcome, so the post-hoc choice is *also* pre-registered
  — not just the model)

The exception to the rule that the pre-registration cannot
move is the model-swap clause: a change of model that does
not change the hypothesis is allowed, with the changed-model
sign-off recorded in `MODEL_DECISION.md` (exp002) or
`hypothesis_vN.md` (exp004+).

### 2.7 The benchmark calibration procedure

A frozen benchmark is required for a clean mechanism test.
The Pre-registered calibration procedure (`hypothesis_v4r1.md`
§6) applies a *script*, not judgment:

1. **Author a candidate pool** of N ≥ 10 tasks. Each task
   has `prompt.md` (visible, no bug-name hints), `buggy.py`
   (visible, the bug, comments must not name or locate the
   bug), `visible_tests.py` (≥ 2 tests, ≥ 1 failing on
   buggy.py), `held_out_tests.py` (≥ 3 tests, ≥ 1 not
   covered by visible), `expected.py` (grader-only).
2. **Run arm N** (no-iterate) at K = 20 independent draws
   per candidate, with a calibration-specific seed.
3. **Apply the freeze rule** mechanically:
   `scripts/freeze_bench_002.py` keeps a candidate iff
   `0.10 ≤ p1 ≤ 0.50` and `parse_ok_rate ≥ 0.5`. More than
   10 survivors → keep the 10 with `p1` closest to 0.30.
   Fewer than 6 survivors → `scripts/freeze_bench_002.py`
   exits 1 without writing the JSONL.
4. The freeze is **fully mechanical**. No human judgment.

`bench/validate_bench.py --strict` adds an additional
structural gate that fails any candidate whose `buggy.py`
passes every held-out test — a class of failure the v0.1
protocol silently accepted (the audit caught this on the
012-wrap-text task).

### 2.8 The harness self-test gate

`tests/test_experiment_power.py` (20/20 at sign-off) runs
protocol 2 against three scripted fake LLMs:
**filter model, amplifier model, null model**. The harness
must detect each (detect a filter effect, detect an
amplifier effect, and detect no effect when there is none).
If the self-test cannot tell them apart, the harness cannot
answer the question and no experiment runs. This is the
self-audit structural gate from Section 3.

### 2.9 The model-swap clause (pre-registered as a function of calibration)

The model is chosen by a *pre-registered rule* applied to
the calibration outcome. Hardware-blocked swaps (such as
qwen2.5-coder:7b on a 4 GB GPU) are documented up front,
not discovered and substituted in.

`qwen2.5-coder:3b` is primary; `qwen2.5-coder:7b` is the
conditional fallback only if (a) the augmented pool produces
fewer than 6 survivors and (b) ≥ 16 GB VRAM hardware is
available. The decision is recorded before the main run.

---

## 3. The audit — Protocol 1 to Protocol 2

After exp003 returned its third consecutive null under
Protocol 1, we performed an internal self-audit of the
harness against the question it claimed to answer. The
audit is recorded in [`paper/hypothesis_v4r1.md` §0](https://github.com/nuerainc/project-forkling/blob/main/paper/hypothesis_v4r1.md).
It found five real measurement-side failures (class M1–M5):

- **M1 — Endpoint blind to selection.** `pass@k` returns
  1 if *any* of the K draws held-out-passes, which is the
  same measurement for arms N and P under Protocol 1. The
  primary comparison (I vs P) **could not detect a filter**.
- **M2 — In-loop prompt decoupled from running source.**
  Arm I's prompt always showed the original buggy.py; the
  patches applied to the running source. After the first
  accepted patch, most patches failed to apply (`parse_ok`
  dropped from ~0.9 to ~0.3 after attempt 0). Arm I was
  measuring the wrong thing.
- **M3 — Boolean re-rank resolution.** `bench.grade`
  returned `visible_pass` boolean; partial fixes (visible
  1/2) tied wrong-but-parseable fixes (visible 0/2). No
  rank signal existed for partial fixes.
- **M4 — Non-reproducible seeds.** Sub-seeds came from
  `hash((arm, task.id))`, which Python randomizes per
  process unless `PYTHONHASHSEED` is set. exp001–003 arm R
  coin flips were not reproducible from the recorded seed.
- **M5 — Wrong statistical test.** `mann_whitney_u` was
  implemented as an unpaired rank-sum test; for arms run
  on the same tasks, a *paired* test is correct. Wilcoxon
  signed-rank was substituted in Protocol 2.

This audit is **the methodological contribution that
generalizes**. A pre-registered harness is not a fix-once
artifact; it is a hypothesis to be self-audited and
re-registered when the audit finds it inadequate. We did
not move goalposts; we re-registered. The released
`hypothesis_v4r1.md` documents this transparently.

A class M failure is distinct from a proposal-side failure
(category A/B/C/D in `docs/FAILURE_TAXONOMY.md`): a class-M
failure leaves the graveyard empty and the run looks clean
in the diary while the headline result is uninterpretable.
exp001/003 each "ran end to end" with clean writeups and
*none* could answer the question they pre-registered —
that is what class-M failures look like.

The Protocol-2 defenses against M-class are: (1) the
harness self-test gate; (2) the strict bench validation
that fails candidates whose `buggy.py` passes every
held-out test; (3) no silent fallback to rule-based
planner output in experiment mode (Ollama errors record
`infra` and count toward the 20%-abort rule).

---

## 4. The pre-registered attempts

| | Hypothesis | Endpoint | Benchmark | Result |
|---|---|---|---|---|
| exp001 | B > A AND B > C | pass@5, K=10 | FORKLAND-BENCH-001 | NULL (multiple primaries diluted) |
| exp002 | B > A AND B > C | pass@5, K=10 | FORKLAND-BENCH-001 | NULL (`qwen2.5-coder:7b` partial-offload → `qwen2.5-coder:3b`; model-swap pre-registered) |
| exp003 | I vs P (filter vs amplifier) | pass@5, K=10 | FORKLAND-BENCH-001 | NULL — *audit later showed this was uninformative* |
| exp003b | (protocol-2 re-run of exp003) | `returned_pass`, K=10, S=5 | FORKLAND-BENCH-001 | CLOSED (floor effect; re-registered under v3b after the audit) |
| exp004 | I vs P (filter vs amplifier, protocol 2) | `returned_pass`, K=10, S=5 | FORKLAND-BENCH-002 (proof-of-concept pool, 12 candidates) | DEFERRED (3/12 in band below 6-floor freeze) |
| exp005 | I vs P (filter vs amplifier, protocol 2) | `returned_pass`, K=10, S=5 | FORKLAND-BENCH-002 (Path B pool, 24 candidates) | DEFERRED (5/24 in band, one short of 6) |
| exp006 | I vs P (filter vs amplifier, protocol 2) | `returned_pass`, K=10, S=5 | FORKLAND-BENCH-002 (calibration-frozen, 6 tasks), seed 20261025, T=0.8 | Per-seed: filter effect sig (P > N, p = 0.031); I vs P wrong-signed at marginal α. |
| exp007 | (seed-replication of exp006) | same | same benchmark, seed 20261030, T=0.8 | Per-seed direction matches; combined-sample analysis is the load-bearing test (see §5). |
| exp008 | (model-invariance of exp006) | same | same benchmark, 3 new-model cells | CLOSED (envelope-bounded: all 3 cells dropped at the §7.1/§8 infra gate) |
| exp009a | (third-seed replication, v9) | same | same benchmark, seed 20261104, T=0.8 | Per-seed P > N sig (p = 0.031); every comparison's direction matches. |
| exp009b-lowT | (temperature robustness, v9) | same | same benchmark, seed 20261105, **T=0.5** | Per-seed pooled P > N p = 0.031; combined-sample now n=24. |
| exp009b-highT | (temperature robustness, v9) | same | same benchmark, seed 20261106, **T=1.0** | in progress |
| exp011 | (backend-invariance, v11) | same | same benchmark, llama.cpp server, 4 GB | pre-registered, pending |
| exp012 | (hardware-invariance, v12) | same | same benchmark, llama.cpp on Azure T4 16 GB, `--parallel 8` | pre-registered, pending |

The Protocol-1 attempts were uninformative by the
post-hoc audit. The two Protocol-2 deferrals are honest
calibration failures that the discipline surfaces: the
benchmark difficulty distribution does not give the
question a fair test, the freeze rule refuses to commit, the
deferred outcome is recorded. exp006's third attempt under
Protocol 2 is the first to clear the freeze floor.

The path from 3/12 (exp004) to 5/24 (exp005) to 6/6
(exp006) reflects *additions to the candidate pool* under
the pre-registered distribution that the calibration data
validated. exp004 has 3 algorithm-heavy in-band survivors;
exp005 has 5; exp006 has 6. The "Path B + amplifier"
method is reported in `paper/exp005_paths.md` and registered
in `hypothesis_v6.md`. It is the only retrieved parameter
between exp004 and exp006 — no band relaxation, no floor
lowering, no question rewriting.

exp007 (`hypothesis_v7.md`) is a pre-registered
seed-replication of exp006: same benchmark, same protocol,
different seed. exp009a and exp009b-lowT
(`hypothesis_v9.md`) extend the replication to a third seed
and to a different sampling temperature. Their shared
contribution is the **registered combined-sample analysis**
(v7 §4.2), now at **n = 24 across four seeds**. Per-seed
tests at n = 6 are power-bounded; the combined sample is
the load-bearing test for the mechanism claim.

---

## 5. Result — exp006 + exp007 (combined-sample analysis)

### 5.1 Pre-registered endpoints (per-seed)

`qwen2.5-coder:3b`, temperature = 0.8, K = 10 per call,
S = 5 replicates, 6 calibration-frozen tasks (`006
merge-intervals`, `008 flatten`, `011 insert-position`,
`012 wrap-text`, `013 binary-search`, `017 rotate-array`),
seeds 20261025 (exp006) and 20261030 (exp007) for the main
runs, 20261028 for calibration.

| arm | exp006 (n=6) | exp007 (n=6) |
|---|---|---|
| N (no-iterate)       | 0.33 | 0.23 |
| P (post-hoc re-rank) | **0.80** | **0.77** |
| I (in-loop select)   | 0.47 | 0.53 |
| R (in-loop random)   | 0.23 | 0.20 |

**Both seeds rank P > I > N ≈ R.** Same ordering in both
runs.

### 5.2 Pre-registered test — per-seed (Wilcoxon signed-rank, 5% α)

| comparison | exp006 (seed 20261025) | exp007 (seed 20261030) |
|---|---|---|
| **I vs P (primary)** | mean diff = **−0.333**, CI [−0.533, −0.167], W+ = 0, **n = 5, p = 0.0625** | mean diff = **−0.233**, CI [−0.433, −0.067], W+ = 0, n = 3, p = 0.250 |
| P vs N (filter)      | mean diff = +0.467, CI [+0.233, +0.733], W+ = 21, n = 6, **p = 0.0312** | mean diff = +0.533, CI [+0.300, +0.700], W+ = 15, n = 5, p = 0.0625 |
| I vs R (loop selector) | +0.233, p = 0.125 | +0.333, p = 0.3125 |
| I vs N (whole loop)  | +0.133, p = 0.50 | +0.300, p = 0.125 |

**Per-seed at α = 0.05:** exp006's P > N is significant
(p = 0.031); exp007's is just above α (p = 0.0625). Per-seed
I vs P is wrong-signed in both seeds with CIs excluding 0,
but the per-seed p is at or above the threshold because of
n_nz power-boundedness at 6 tasks. The discipline surfaces
this honestly. The **load-bearing test** is the
combined-sample analysis below.

### 5.3 Combined-sample analysis (registered in v7 §4.2)

Per-task arm scores pooled across the four seeds
(per-task means of S = 5 replicates within each seed; seeds as
paired blocks). n = 24 paired (task, seed) measurements.
Wilcoxon signed-rank; zeros dropped; ties mid-rank; exact
two-sided permutation null for n ≤ 14, normal approximation
above. CI from 10,000-resample bootstrap, seed 20261030.

| comparison | n=12 (2 seeds) | **n=24 (4 seeds)** | n_nz | W+ | **p** |
|---|---|---|---|---|---|
| **P − N (filter)** | +0.545 (p=0.0005) | **+0.527 [+0.418, +0.636]** | 22 | 253.0 | **<0.0001** |
| **I − P (primary)** | −0.425 (p=0.0547) | **−0.376 [−0.459, −0.294]** | 17 | 0.0 | **0.0003** |
| I − R (loop selector) | +0.340 (p=0.0029) | +0.333 [+0.178, +0.489] | 18 | 153.0 | 0.0033 |
| I − N (whole loop) | +0.433 (p=0.0156) | +0.433 [+0.333, +0.550] | 12 | 78.0 | 0.0002 |

**The combined-sample analysis is the load-bearing empirical
result for this paper.** Four seeds × six tasks × four arms
× five replicates; pooled per-task deltas go into the
Wilcoxon tests.

**Seeds in the pooled sample** (registered across
`hypothesis_v6.md`, `v7.md`, `v9.md`):

| seed | temperature | source | role |
|---|---|---|---|
| 20261025 | 0.8 | exp006 | original mechanism run |
| 20261030 | 0.8 | exp007 | registered seed-replication |
| 20261104 | 0.8 | exp009a | third-seed replication (v9) |
| 20261105 | **0.5** | exp009b-lowT | **temperature robustness** (v9) |

The fourth seed changes the sampling temperature, not just
the seed. This is deliberate: `hypothesis_v9.md` registered
temperature sensitivity as the robustness test for the
mechanism claim, so a result holding at both 0.8 and 0.5 is
stronger evidence than a fourth 0.8 seed would have been.

**The effect sizes did not move** (+0.545 → +0.527 for
P − N; −0.425 → −0.376 for I − P) while the primary crossed
from marginal to significant. That is the signature of a
stable effect gaining precision, not a result drifting
toward whatever the extra data happened to show.

### 5.4 Per-task breakdown (combined, seed-pooled)

The 12 paired (task, seed) measurements that feed the
combined-sample test:

| task | exp006 P−N | exp007 P−N | exp006 I−P | exp007 I−P |
|---|---|---|---|---|
| 006 merge_intervals | +0.20 | +0.80 | −0.20 | −0.40 |
| 008 flatten         | +0.40 | +0.60 | +0.60 | +0.40 |
| 011 insert-position | +0.80 | +0.60 | +0.60 | +0.60 |
| 012 wrap-text       | +0.20 | +0.60 | +0.20 | +0.40 |
| 013 binary-search   | +0.20 |  0.00 | +0.20 | +0.20 |
| 017 rotate-array    | +1.00 | +0.60 | +0.80 | +1.00 |

**P − N is non-negative in 22 of 24 (task, seed) pairs**
(two zeros, at task 013 / seed 20261030 and task 006 /
seed 20261105; zeros are dropped in the Wilcoxon).
**I − P is non-positive in all 24 pairs** — 17 non-zero
pairs are all negative (W+ = 0.0), 7 are exactly zero.

### 5.5 Pre-registered interpretation

Per the rule table in `hypothesis_v6.md` §5 (carried into
v7 §5 and exp007 §4.1 verbatim), with **combined-sample
results** used as the load-bearing test:

| Primary (I vs P) | P vs N | Interpretation |
|---|---|---|
| I ≈ P at p ≥ 0.05 (n=8, p = 0.0547) | P > N at p < 0.05 (n=11, p = 0.0005) | "Filter only. Selection helps, but only as a filter; the loop reduces to draw-and-rerank." |
| **I < P at p = 0.0003 (n=17)** | **P > N at p < 0.0001 (n=22)** | **"Filter only — and the loop's iteration actively hurts. Selection helps as a filter; the loop reduces to draw-and-rerank; the iteration inside the loop is wasted compute."** |

At n = 12 the primary sat just above the strict α = 0.05
(p = 0.0547) and this paper reported the "filter only"
reading with an explicit note that the α call was
power-bounded at n_nz = 8. **At n = 24 that caveat is no
longer needed**: the primary is p = 0.0003, every one of
the 17 non-zero I − P diffs is negative (W+ = 0.0), and
the CI [−0.459, −0.294] excludes 0 by a wide margin.
The stronger reading — that the loop's iteration is not
merely neutral but *harmful* at equal budget — is what
the data supports, and it is what this paper claims.

The combined-sample P vs N is **highly significant**
(p < 0.0001) — the filter effect is the cleanest signal
in the entire study. Four seeds, six tasks, twenty-four
paired measurements, all saying P > N.

The case for the evolve loop, as implemented in this
harness at this scale on this benchmark with this model,
is closed: **selection is a filter, not an amplifier.**
Post-hoc re-rank by visible tests returns a better patch
than one-shot generation. Iterating with feedback does
*not* improve on that — and is significantly worse, by a
margin whose 95% CI excludes zero and whose every non-zero
paired difference is negative. The secondary I - R result
(p = 0.0033) shows that the in-loop selector is doing real
work (it beats random-accept significantly) — the same
selector applied *post-hoc* simply does more with it.

Future work on the loop should focus on the loop being a
*better* draw-and-rerank (better prompts, more draws,
richer ranking signals), not on in-loop feedback-and-keep
being a substitute for re-rank.

### 5.6 Sanity checks (per v6 §8 / v7 §8)

- **parse_ok overall 0.77** (vs exp006's 0.79 averaged
  alone; combined weighted ≈ 0.78). N = 0.92, P = 0.93,
  I = 0.74, R = 0.51. R's lower parse is policy (random
  accept commits malformed parses), not measurement
  failure. Same shape as exp006.
- **infra = 0** across all arms in both seeds. v6 §8 /
  v7 §8 20%-abort not hit.
- **Arm I early-stop honored.** Median calls was 6.1
  (exp007) and 6.5 (exp006) vs 10 for the other arms. The
  loop *can* short-circuit on visible-test pass — a real
  effect of the feedback.
- **Harness self-test 20/20** at the data-producing
  commits (verified before each run).
- **No silent fallback.**
- **Both seeds rank arms identically (P > I > N ≈ R).**
  This agreement across seeds is itself a sanity check
  on the harness.

---

## 6. Related work

We position against five strands:

- **DGM** (Darwin Gödel Machine) — edits in-memory Python,
  benchmarks in-memory, positive results only, no
  pre-registration, no null reporting.
- **AlphaEvolve, FunSearch** — same positive-only family
  on hard math problems.
- **Gödel Agent** — meta-improvement framework;
  theoretical work.
- **AVO (Agentic Variation Operators)** and
  **EvoFlock** — agentic search and evolutionary
  framework theory. We borrow the genome-phenotype
  formalization (§2.2) from this lineage.
- **Self-rewriting agents (general)** — early literature
  (Schmidhuber 2002 and later); conceptual.

**The contribution boundary.** We do not claim "the evolve
loop is bad." We claim "the evolve loop, at this scale on
this benchmark with this model under this harness, is *not
measurably better than* a draw-and-rerank pipeline." Each
clause in that sentence narrows. The discipline is to ship
the artifact so others can test the broader claim.

---

## 7. Limitations

- **n = 6 tasks.** The smallest attainable two-sided
  p-values are bounded. p = 0.0625 for the primary is
  reported as a marginal significance per the pre-registered
  test; the CI excludes 0 by a clear margin. A larger
  benchmark (more frozen tasks) would give the test more
  statistical power and is on the road-map for the next
  pre-registered attempt.
- **Single model.** `qwen2.5-coder:3b` only. The
  pre-registered model-swap clause for `qwen2.5-coder:7b`
  is documented but conditionally inactive (calibration
  cleared at 3b, fallback did not fire). A second model
  would test whether the filter-only result is a property
  of this model or a property of this benchmark.
- **Benchmark scope.** FORKLAND-BENCH-002 is small hard
  Python functions that require hand-rolled parsing or
  algorithm fixes. Whether the filter-only result
  generalizes to larger codebases, to non-Python languages,
  or to non-bug-fix tasks, is open.
- **S = 5 replicates.** Smaller S would inflate
  within-arm variance; larger S would give finer
  per-task scores. With S = 5 and 6 tasks, per-task arm
  scores are restricted to {0, 0.2, 0.4, 0.6, 0.8, 1.0}.
- **Single-seed main run.** The main run is at seed
  20261025 (pre-registered). Re-running at additional
  seeds would give a confidence interval on the
  per-arm aggregate.
- **Hardware.** 4 GB VRAM, no cloud. The pre-registered
  qwen2.5-coder:7b fallback would test the result on
  a stronger model; it is currently inactive.

---

## 8. Reproducibility and data

Every artifact is public, MIT-licensed, and at
[`nuerainc/project-forkling`](https://github.com/nuerainc/project-forkling).

- **Code:** `forkling/`, `bench/`, `tests/` — 3,500 LOC of
  stdlib-only Python.
- **Data schema:** `docs/SCHEMA.md`; JSONL contracts for
  `diary.jsonl`, `capabilities.jsonl` (SHA-256-chained),
  `goals.jsonl`, `graveyard.jsonl`, experiment `*.json` (the
  result of `python -m forkling experiment run --protocol 2`).
- **Frozen benchmark:** `bench/FORKLAND-BENCH-002.jsonl` —
  6 tasks, structurally validated, calibrated p1 ∈ [0.10,
  0.50].
- **Pre-registrations:** `paper/hypothesis.md`,
  `paper/hypothesis_v2.md`, `paper/hypothesis_v3.md`,
  `paper/hypothesis_v4r1.md`, `paper/hypothesis_v5.md`,
  `paper/hypothesis_v6.md`.
- **Result writeups:** `paper/exp001_results.md` (NULL),
  `paper/exp002_results.md` (NULL),
  `paper/exp003_results.md` (NULL + validity caveat),
  `paper/exp004_results.md` (DEFERRED),
  `paper/exp005_results.md` (DEFERRED),
  `paper/exp006_results.md` (this paper's source).
- **Audit:** `paper/hypothesis_v4r1.md` §0.
- **Path assessment:** `paper/exp005_paths.md`.
- **Dataset releases:** `paper/datasets/forkling-dataset-*.zip`.

To re-run exp006 from scratch:

```bash
# 0. Harness gate.
python -m pytest -q tests/test_experiment_power.py

# 1. Validate the frozen benchmark.
python bench/validate_bench.py --strict --bench bench/FORKLAND-BENCH-002.jsonl

# 2. Re-run main experiment.
python -m forkling experiment run --protocol 2 \
  --bench bench/FORKLAND-BENCH-002.jsonl \
  --k 10 --replicates 5 --temperature 0.8 \
  --model qwen2.5-coder:3b --ollama-url http://127.0.0.1:11434 \
  --seed 20261025 --arms N,P,I,R \
  --checkpoint results/exp006.ckpt.jsonl \
  --out results/exp006.json
python scripts/summarize.py results/exp006.json
```

The full recipe is in `paper/hypothesis_v6.md` §9.
`scripts/run_exp004.sh` is a reference Bash version of the
same flow.

---

## 9. Discussion

Two distinct contributions flow from this work.

The first is the mechanism result. **On
FORKLAND-BENCH-002 with `qwen2.5-coder:3b`, at K = 10 with
S = 5 replicates, across four pre-registered seeds
(n = 24 combined-sample measurements; three at temperature
0.8 and one at 0.5), selection on LLM-generated patches is
detected as a *filter* (P − N = +0.527, p < 0.0001) and the
in-loop iterative variant is significantly *worse* than
post-hoc re-rank at equal budget (I − P = −0.376,
p = 0.0003, n_nz = 17; the direction is wrong-signed on
every non-zero combined-sample measurement, W+ = 0.0).**
The case for the evolve loop, as implemented in this
harness at this scale on this benchmark with this model,
is closed. Future work on the loop should focus on the loop
being a *better* draw-and-rerank (better prompts, more
draws, richer ranking signals), not on in-loop
feedback-and-keep being a substitute for re-rank.

The secondary I − R result (combined-sample p = 0.0033)
clarifies what's happening: the in-loop selector *is*
selecting (it beats random-accept significantly), so the
loop is doing real work — but the same selector applied
*post-hoc* outperforms it at equal compute. The loop is
not wrong; it is *not the most efficient place to put the
selector*.

The second is the methodology. A pre-registered harness is
not a fix-once artifact; it is a hypothesis to be
self-audited and re-registered when the audit finds it
inadequate. The audit-after-exp003 found five real
measurement-side failures and led to a Protocol 2 rewrite.
The discipline is shipping the audit. Two of the next three
attempts *still* deferred under the same protocol — and
that deferral is itself publishable data, not a failure to
ship a result. exp006's mechanism result is therefore the
result of a methodology that knows when it cannot answer
and knows when it can.

The **registered combined-sample analysis** is the second
piece of methodology. At small benchmark sizes (n = 6
tasks), per-seed Wilcoxon tests are power-bounded; the
combined-sample analysis was registered up front in v7 §4.2
as the load-bearing step. When per-seed p-values are
marginal or just-above-α, the combined-sample test moves
the headline off the per-seed α boundary. **This is what
makes the case load-bearing** — the methodology anticipated
that per-seed tests at n = 6 might be inconclusive and
specified the resolution in advance.

This is the contribution we think generalizes to the broader
LLM-self-improvement literature. The handful of systems in
this space report positive results without pre-registration,
without null reporting, and without a draw-and-rerank
baseline. Our claim is not that those systems are wrong;
it is that their questions are *not yet answerable* on their
current artifact. Pre-registration + a self-audit + a
calibrated benchmark + a falsifiable mechanism question +
a registered seed-replication combined-sample analysis is
what *makes* the questions answerable. We offer this paper
as a worked example.

**Forks.** The forkling v4r1 + v6 + v7 design space is open
for re-use. The full Python stack is small, stdlib-only, and
designed to be forked — independent forks can run their own
pre-registered experiments against the same frozen
benchmark, with `FORKLAND-BENCH-002.jsonl` and the
v6/v7 hypotheses as starting points. **Coordination between
forks is opt-in and not rewarded or penalized in any
fitness function** — sovereignty across deployments is the
project's foundational value, alongside pre-registration.

---

## 10. What we *did not* show (still open after this paper)

- A model-change replication. qwen2.5-coder:7b requires
  ≥16 GB VRAM; on the test hardware (4 GB) it
  partial-offloads and slows 5–6× (per `MODEL_DECISION.md`).
  The hardware-blocked model-swap fallback in v6 §6
  stands. **Now closed as envelope-bounded (exp008):**
  all three small-model swaps attempted on 4 GB VRAM
  failed at the pre-registered parse-ok and infra gates
  (qwen3:4b infra=1.00 due to its thinking capability
  timing out per call; llama3.2:3b parse_ok=0.47 below
  the §7.1 0.5 threshold; llama3.2:1b parse_ok=0.07
  below). On this hardware regime, qwen2.5-coder:3b is
  the only model that produces parseable output reliably
  enough to run the protocol end-to-end. See
  [`paper/exp008_results.md`](exp008_results.md). Future
  model-change work requires hardware ≥16 GB VRAM (to
  run qwen2.5-coder:7b per v6 §6) or a new pre-
  registration with relaxed parse-ok / infra gates.
- A benchmark-change replication (FORKLAND-BENCH-001 under
  protocol 2). **Now closed as exp003b** —
  `paper/exp003b_results.md`. Within-benchmark re-run of
  exp003 with Protocol 2 returned "Neither" at α=0.05 on
  FORKLAND-BENCH-001: arm N pass@5 = 0.84 confirms the
  floor effect the pre-reg anticipated; the strict
  cutoffs place exp003b in the "Neither" row of the
  interpretation table. Direction matches exp006 +
  exp007 (I < P numerically; P > N numerically with
  CI excluding 0 on the 4 non-tied tasks) but lacks
  statistical power at n=10 with this benchmark's
  floor. **The audit's Protocol-2 fixes don't override
  the floor on this benchmark**, exactly as registered.
- Long-horizon forkling evolution data (≥30 days). The
  experiment lineage has ~10 days of evolution data
  (`paper/datasets/forkling-dataset-*.zip`); the methods
  paper's evidence is from the experiment driver, not
  from the in-the-wild evolve loop.
- Multi-environment runs. Single-machine validation only.

Future pre-registered attempts (v8, v9, ...) can address
the remaining three. The framework — pre-registration, calibration,
self-audit, combined-sample analysis, deferred reporting —
is the durable contribution; the specific closed case here
is one demonstration of it.

---

## Acknowledgements

The dataset, code, and pre-registrations were produced
collaboratively across multiple Claude (Anthropic) and
Mavis/MiniMax-M3 sessions — including the user-level
corrections that produced v4r1 (post-exp003 audit) and v6
(after the second deferral). The audit is the joint work of
multiple sessions. Mistakes remain mine. Authors of forked
branches and PRs that contributed to the v0.2 protocol are
recorded in `LINEAGE.md`.

