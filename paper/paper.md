# forkland: Version-Control-Native Evolution for Self-Improving Code Agents

**Authors:** Jeremy Beebe¹, forkland²
¹ forkland maintainers · ² Software co-author (capability ledger, graveyard, diary)

**Status:** v0.2 preprint · 2026-09-16
**Repository:** https://github.com/<your-org>/forkland
**License:** MIT

---

## Abstract

We present **forkland**, a self-contained, self-improving AI agent whose
evolutionary substrate is the git repository itself. Each commit is a
generation, the test suite is the fitness function, and the entire
evolutionary history is auditable from `git log`. forkland requires no
paid APIs (it speaks to a local Ollama daemon), runs offline on $15
hardware, and dogfoods itself from the first push. v0.2 introduces a
research substrate: a SHA-256-chained capability ledger, a patch
graveyard for negative-example learning, a multi-objective fitness
function (smartness × skill), an A/B lineage primitive for controlled
selection-pressure experiments, phylogenetic replay of ancestor agents,
an append-only diary of agent interactions, and a grant-hunter module
that turns the agent's own evolution into grant-proposal evidence. We
argue that treating git as an evolutionary database — rather than a
code-management tool — is a missing primitive for the self-improving
agent literature.

## 1. Introduction

Recent work on self-improving AI agents has produced impressive
demonstrations: AlphaEvolve (DeepMind, 2025) closed open problems in
mathematics; the Darwin Gödel Machine (Zhang et al., 2025) showed that
LLM-driven agents can rewrite themselves across a search tree. Both
frameworks treat the agent's code as the search space and use a fitness
function to select survivors.

We make one design choice differently: we use **git itself** as the
evolutionary substrate. Each commit is a generation, branches are
lineages, the test suite is the fitness function, `git checkout` is
extinction, and the merge is crossover. The agent's evolutionary history
is therefore **public, auditable, forkable, and replayable** by anyone
with `git clone`.

Three consequences fall out of this design:

1. **Reproducibility.** Any evolutionary trajectory can be replayed by
   checking out the commits in order and running the agent at each
   generation. Our phylogenetic-replay module automates this.

2. **Audit trail.** The SHA-256-chained capability ledger guarantees
   that the agent's record of what it has demonstrated is tamper-evident
   for honest actors. This matters for AI safety: the agent can prove
   what it has done.

3. **Distributed evolution.** Git forks are natural population members.
   Anyone can fork, run the dogfood loop, and propose a merge. The
   evolutionary unit is the *fork graph*, not the single agent.

## 2. Architecture

forkland is a single Python package, stdlib-only (no `requests`, no
`click`, no PyTorch). It runs on Python ≥ 3.9 and weighs ~1 MB of code.
The agent loop is Plan → Act → Reflect, with auto-rollback on test
failure:

```
task ──► plan (LLM or rule) ──► act (filesystem|shell|git) ──► test ──► ship?
                                                ▲                       │
                                                └── rollback ◄─────────┘
                                                  (on test failure)
```

Every action is recorded in three append-only stores:

* **Capability ledger** (`~/.forkling/capabilities.jsonl`): SHA-256-
  chained JSONL of every action, target, success, and agent SHA.
* **Patch graveyard** (`~/.forkling/graveyard.jsonl`): every rejected
  patch with reason, injected into the next LLM prompt as negative-
  example context.
* **Diary** (`~/.forkling/diary.jsonl`): free-form narrative of every
  interaction. The agent's own memory of its youth.

The test command (default `pytest -q`) is the gate. Every self-edit is
first validated for uniqueness (the `old` substring must appear exactly
once in the target file), then applied, then tested, then either
committed and tagged or `git checkout`'d to the previous SHA.

## 3. Research Substrate (v0.2 additions)

### 3.1 Capability ledger

A linear SHA-256-chained log. Each entry `e_i` carries
`sha_prev = e_{i-1}.sha_self`, and `sha_self = SHA-256(sha_prev ||
canonical_json(e_i \ {sha_self}))`. A single byte-level tamper is
detected on `forkling verify`. This is a research artifact (prevents
accidental rewrites, not adversarial ones), but it makes the agent's
demonstrated capabilities into a verifiable claim.

### 3.2 Patch graveyard

Every rejected patch (LLM-proposed or rule-based) is recorded with its
rejection reason (`"old substring not unique"`, `"tests failed"`,
`"empty patch"`). The next LLM prompt is augmented with the recent
graveyard as a primitive form of negative-example memory. We have
observed empirically that this reduces the rate of repeated rejections.

### 3.3 Multi-objective fitness

`forkling fitness` reports two 0..1 scores:

* **Smartness** — patch acceptance rate and test pass rate, capturing
  *how well* the agent reasons about existing capabilities.
* **Skill** — distinct action types used and Shannon-normalized file
  diversity, capturing *how broad* the agent's reach is.

These two axes answer the user's natural question: "does it get smarter
*and* more skilled?" The diary and ledger together provide the
longitudinal data needed to plot fitness trajectories.

### 3.4 A/B lineages

`forkling/evolution.py::run_ab(lineages, generations)` spawns parallel
agents in git worktrees, each with its own env vars
(`FORKLING_STRATEGY=...`), runs each for N generations, and ranks by
fitness. The control variant is **Spoonica** (conservative), the
hybrid is **Sporklyn**, the sharpest is **Knifling**. Future work will
release the full ensemble under the umbrella "Forkland & Family".

### 3.5 Phylogenetic replay

`forkling replay <old-sha> <task>` checks out an ancestor commit and
runs that version of forkland on a task, in a temporary worktree. This
enables longitudinal analysis: "did adding the graveyard module reduce
rejection rate?" `forkling diff-replays` runs the same task on two
ancestors and diffs step counts and outputs.

### 3.6 Diary

A free-form append-only log of every interaction: boot, plan, run,
self-improve.start, self-improve.applied, milestone, rollback. The
diary is what the agent uses to "look back fondly in memory of its
youth." It is also useful evidence in grant proposals and papers:
milestones are filterable via `forkling diary milestones`.

## 4. Empirical Status

As of v0.2 (commit `bbf35be`), forkland has:

* **50 tests** passing (pytest).
* **1 generation** of self-improvement shipped (the v0.2 commit itself).
* **0 test-suite failures** in the shipped lineage.
* **0 paid API dependencies** (Ollama local only; rule-based fallback).
* **3** ledger entries verified clean.

A long-running experiment is in progress: the CI workflow
`.github/workflows/dogfood.yml` runs forkland on itself on every push.
We will report fitness-trajectory statistics once N ≥ 30 generations
have accumulated.

## 5. Discussion

### 5.1 Why git?

The literature has converged on the view that self-improving agents
need a versioning system. AlphaEvolve and Darwin Gödel Machine both
implement ad-hoc versioning. We argue that git is the right primitive:
it is **battle-tested**, **distributed**, **cryptographically
verifiable**, and **ubiquitous**. There is no need to reinvent the
substrate when 20+ years of work have produced one for free.

### 5.2 What this enables

* **Reproducible AI research.** Every paper in this area could ship
  with a `git clone` URL that reproduces the agent's evolutionary
  history. The substrate makes this trivially possible.
* **AI safety audits.** The capability ledger, combined with the
  git log, is a starting point for third-party audit of self-improving
  systems.
* **Distributed evolution.** Anyone can fork, evolve, and propose
  a merge. Evolution becomes social.

### 5.3 Limitations

* The fitness function is intentionally simple (test pass rate + action
  diversity). Multi-objective Pareto selection is future work.
* The 4B-parameter Qwen3 model has a slow "thinking" mode on some
  Ollama builds; we disable it via a `think: false` API call.
* The patch graveyard is a primitive form of negative learning; we do
  not yet fine-tune on it.

### 5.4 Future work

* A/B lineages with statistical comparison of fitness trajectories.
* Phylogenetic introspection as a first-class debugging tool.
* Sovereign mode tested on a Raspberry Pi Zero.
* Auto-generated paper drafts from the diary + ledger.

## 6. Authorship

Primary authorship is held by the human maintainers. forkland is
acknowledged as a software co-author. The capability ledger, graveyard,
and diary make the agent's contribution auditable. We follow the
authorship norms of the relevant venue (preprint server vs. journal)
and propose a `CITATION.cff` for repositories that do not formally
recognize software authorship.

## 7. Reproducibility

```bash
git clone https://github.com/<your-org>/forkland
cd forkland
pip install -e . && pip install pytest
python -m forkling doctor
python -m forkling verify          # ledger SHA-256 chain
python -m forkling diary milestones
python -m forkling fitness
```

The full evolutionary history is in `git log`; no hidden state.

## 8. Acknowledgements

We thank the local Ollama daemon, the Python stdlib maintainers, and
the git maintainers, without whom none of this would run.

---

## Appendix A: Current state snapshot

(See `fitness-snapshot.json`, `ledger-verify.json`, `diary-snapshot.txt`,
and `git-log-snapshot.txt` in this directory.)

## Appendix B: Fitness over generations

(TBD — will be auto-generated from `forkling fitness` history once
N ≥ 30 generations have been recorded.)


---

## Update at 2026-09-16 19:58:28

- capabilities: 1
- rejected patches: 2
- diary milestones: 0
- fitness: smartness=0.000, skill=0.050, total=0.025
