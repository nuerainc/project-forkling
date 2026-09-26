# Methods Outline — Pre-Registered Falsifiable Science on Agent Self-Improvement

**Status:** outline draft, v0.1. **Not a paper yet.** This is a 1-page
frame a future draft can expand. Sections are scaffolds; the actual
prose lives in `exp00N_results.md`, `hypothesis_vN.md`,
`MODEL_DECISION.md`, and the SCHEMA / PROTOCOL / FAILURE_TAXONOMY
docs.

**Working title (suggestion):** *"Pre-Registered Falsifiable
Methodology for Long-Horizon Agent Self-Improvement, with Three
Convergent Nulls as Preliminary Data."*

---

## 1. Motivation (≈600 words)

LLM-driven agent self-improvement systems (DGM, AlphaEvolve,
FunSearch, Gödel Agent) implicitly bet that an interactive
*evolve loop* — iterate, select, commit, repeat — produces
something a one-shot generator cannot. None of these systems
pre-register the question. None report negative results. The
literature is uniformly positive-result-biased.

We argue this is a methodological gap, not a settled finding.
A question about mechanism (whether selection is a filter or
an amplifier) deserves a pre-registered, falsifiable test —
not a system demo.

The contribution of this paper is the *methodology*: how to
do pre-registered falsifiable science on long-horizon agent
self-improvement, with examples of what it produces when
applied honestly.

## 2. Method (≈1200 words)

### 2.1 Organism model

Forkling is a long-horizon agent that edits its own source
under selection pressure. The substrate is:
- A *real git working tree* (no in-memory tricks).
- An append-only SHA-256-chained capability ledger
  (each generation adds a verified capability).
- A patch graveyard (every rejection recorded with reason).
- A bounded evolve loop with kernel-guard (the agent
  cannot edit its own evaluator).

State variables (formalized in §3 below):
- `genome`: the agent's working-tree git SHAs over time.
- `phenotype`: the agent's demonstrated capabilities
  (`CapabilityLedger.distinct_actions()`).
- `fitness`: a scalar summary derived from
  `fitness-snapshot.json`.
- `environment`: hardware model + ollama model + model load
  state.
- `speciation`: family membership, currently one fork per
  repo with opt-in ledger sharing.

### 2.2 Pre-registration discipline

Every experiment file `paper/hypothesis_vN.md` is committed
*before* any pilot data is viewed under its design. A
hypothesis binds:
- mechanism question (typically one primary, mechanism-level)
- arms and primary comparison
- benchmark + calibration procedure (if not yet frozen)
- stopping rule
- statistical test + alpha

The only pre-registered exception: model-swap clause (see
`MODEL_DECISION.md` for the worked example in exp002).

### 2.3 Benchmark calibration

Benchmarks are *calibrated*, not authored-to-difficulty.
Procedure (pre-registered in `hypothesis_v4.md` §3):
1. Author a candidate pool of N≥10 tasks.
2. Run arm N (no-iterate) at K=20 independent draws per task.
3. Drop tasks where pass@1 ≥ 0.7 (too easy) or pass@1 ≤
   0.05 (impossible) or parse_ok_rate < 0.5.
4. From survivors, freeze 8–10 whose arm-N pass@5 ∈
   [0.2, 0.4]. Defer to a re-tuned target if no task lands
   in range.
5. Commit `FORKLAND-BENCH-NNN.jsonl` at freeze time.

This is the key methodological lever. exp003's three
convergent nulls are reproducible on any benchmark the LLMs
can already ace. A fair test requires a benchmark they
*cannot* ace.

### 2.4 Evolution operators

Mutation: LLM proposes a JSON `{kind, path, old, new}` patch
against the working tree.
Selection: `pytest -q` against the agent's own test suite.
Recombination: not used (single-organism runs).
Speciation: opt-in cross-fork ledger sharing. Sovereign
substrates — no code merging.

### 2.5 Reproducibility

Every experiment's full configuration, records, and
reproduction command are part of the dataset release.
`docs/SCHEMA.md` defines the JSONL contract; `docs/PROTOCOL.md`
defines the runtime + evaluation contract.

## 3. Formal model (≈500 words)

Borrowing from evolutionary computation (AVO, ALife),
we formalize Forkling's evolution as a tuple:

```
E = (G, F, P, S, M)
```

- **G** (genome): a sequence of git SHAs, `g_0, g_1, ...,
  g_T`. Each `g_t` is a heritable state. A generation *g*
  is a `g_t` where `g_t != g_{t-1}`.
- **F** (fitness): `F(g_t) = (smartness(g_t), skill(g_t),
  total(g_t))` computed from `fitness-snapshot.json`.
- **P** (proposal distribution): the LLM's conditional
  distribution over patches given the current state and
  the prompt context (which includes the previous
  generation's diff, the diary tail, the graveyard tail).
- **S** (selection): a hard gate — `pytest -q` exit 0.
  No soft scoring.
- **M** (mutation operator): a string-replace patch that
  passed kernel-guard, validator, and parse checks but
  has not yet been selected.

Selection is `S(g_t') = 1 iff pytest(g_t') = 0` where
`g_t'` is the candidate. Crossover is degenerate
(`M(g_t) = g_t` for unchanged state).

A *speciation event* is a fork producing a divergent
genome sequence. Currently not exercised (single fork);
the family registry (§2.1) provides the affordance.

This formal model connects Forkling to AVO
(austin1997/AVO) and EvoFlock (cwreynolds/evoflock) at
the level of agentic variation operators. The key
*Forkling-specific* claim is the hard pytest selection —
none of the AVO/ALife systems gate on the agent's *own*
test suite the way we do.

## 4. Preliminary data (≈800 words)

Three pre-registered experiments, all on
`FORKLAND-BENCH-001` with `qwen2.5-coder:3b` at K=10.

| Exp | Hypothesis | Result | p (primary) |
|---|---|---|---|
| exp001 | B > A AND B > C | NULL | n/a (multiple primaries diluted) |
| exp002 | B > A AND B > C | NULL | n/a (model swap to 3b) |
| exp003 | I > P (filter vs amplifier) | NULL | 0.71 (direction wrong) |

exp001/exp002 each tested two primaries; exp001's writeup
noted the dilution. exp003 collapsed to one primary. All
three returned null.

Mechanism-level interpretation (exp003 §"Mechanism-level
answer"):
- `I == R` on pass@5 (selection no better than random accept).
- `I < P` on pass@5 (in-loop worse than post-hoc re-rank).
- `P == N` on pass@5 (re-rank no better than first hit).

Together: **selection on LLM-generated patches is neither an
amplifier nor a useful filter at this scale on this
benchmark.** Two competing explanations remain:

- **A:** selection really doesn't help (replicates on a
  harder benchmark).
- **B:** FORKLAND-BENCH-001 was too easy (floor effect;
  exp004 with the pre-registered calibration procedure
  is the disambiguating experiment).

exp004 is in flight.

## 5. Related work (≈600 words)

We position against:

- **DGM** (DeepGeneticMachine) — edits in-memory Python,
  benchmarks in-memory. Selection is implicit (bench
  pass). No pre-registration. Positive-result only.
- **AlphaEvolve / FunSearch** — same family. Positive
  results on hard math problems; no null published.
- **Gödel Agent** — meta-improvement framework;
  recursively self-modifies. Theoretical.
- **AVO / EvoFlock** — agentic variation operators in
  evolutionary computation. Theoretical framework.
- **Self-rewriting agents (general)** — early literature
  (Schmidhuber 2002; later works). Mostly conceptual.

The contribution-claim boundary: we do not claim "the
evolve loop is bad." We claim "the evolve loop is not
measurably better than a no-iterate baseline at the
scales we tested, with the models we tested, on the
benchmarks we tested, for the selection mechanism we
tested." Each clause generalizes narrowly. That is the
point of a falsifiable question.

## 6. Discussion (≈500 words)

Two contributions:

1. **Methodological.** Pre-registration is cheap (one
   markdown file per experiment), falsifiable by
   construction, and reveals design bugs (exp001's
   multiple primaries were caught in writeup).
   Recommended for the field.

2. **Empirical (preliminary).** Three convergent nulls
   on FORKLAND-BENCH-001. Mechanisms: floor effect vs
   real null. exp004 will disambiguate.

The honest framing: **this paper reports methodology +
preliminary data, not conclusions.** The conclusions
arrive when exp004 lands.

## 7. Reproducibility appendix (≈200 words)

Every figure and table in this paper is reproducible from
public artifacts:

- `paper/datasets/forkling-dataset-*.zip` — released bundles.
- `paper/hypothesis_v*.md` — pre-registrations (committed).
- `paper/exp00N_results.md` — result writeups.
- `paper/fitness-snapshot.json` — derived metrics.
- `paper/ledger-verify.json` — SHA-256 chain verification.
- `bench/FORKLAND-BENCH-NNN.jsonl` — frozen benchmarks.
- `results/exp00N.json` — per-experiment records.

`docs/PROTOCOL.md` is the runtime spec; `docs/SCHEMA.md`
is the data contract. Reading the appendix should produce
the same numbers in the same figures, within rounding.

---

## Open questions for the author

- *Should exp004 go in §4 (preliminary data) or §6
  (discussion as "exp004 result closes the A-vs-B
  question")?* Depends on timing.
- *Should the failure taxonomy (§C of
  `FAILURE_TAXONOMY.md`) be its own section, or folded
  into the methods?* Probably its own — it's the second
  novel methodological contribution.
- *Should the formal model in §3 use ALife-style
  notation (Eiben & Smith) or AVO-style
  (austin1997/AVO)?* AVO is more recent and more
  aligned with the agentic framing.
- *What's the right venue?* Pre-registered
  falsifiable methodology + honest nulls fits
  workshops at ICML / NeurIPS / ALife better than
  a main track. Targeting ICML 2026 *FAccT* /
  *MLRC* workshops as a working hypothesis.

---

**Sign-off:** This is a methods outline, not a paper.
The prose does not yet exist. The substrate does, and
it is honest.
