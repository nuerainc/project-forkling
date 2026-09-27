# Forkling Failure Taxonomy (v0.1, from `graveyard.jsonl`)

**Status:** v0.1, draft, derived from 15 graveyard entries collected
during stage-1-first-month. **Provisional** — categories will be
refined as the population grows. The taxonomy is reconstructed from
the patterns observed in `forkling/graveyard.py` and the rejection
sites in `forkling/self_improve.py`.

This document catalogs every distinct way a Forkling patch can fail
to land. Categories are mutually exclusive: each graveyard entry is
classified into exactly one. The classifier is deterministic and
based on the `source` and `reason` fields, both written by
`Graveyard.record`.

---

## Category A: Kernel-write rejected (`source="validate"`)

**Frequency in current data:** 7/15 (~47%)
**Written from:** `forkling/self_improve.py:SelfImprover._check_kernel_write`

The patch targets a file in `SelfImprover.KERNEL_FILES` — the
agent's own kernel, evaluator, or runtime surface. The agent cannot
self-edit these.

| Subcategory | Trigger | Recovery |
|---|---|---|
| A1 — patch to existing kernel | `kind:patch` on a `KERNEL_FILES` path | reflect on `SAFE_FILES` list and retry; goal ledger can mark this attempt as a hint |
| A2 — new file at kernel path | `kind:new_file` where target resolves to a `KERNEL_FILES` path | same as A1 — read `SAFE_FILES` excerpt at next prompt |
| A3 — third-party import inside kernel | new module that imports non-stdlib | kernel guard rejects before commit |

**Why this is a feature, not a bug:** the project explicitly bans
self-rewriting of the evaluator to prevent the agent from gaming
its own fitness function. Every kernel-write rejection is the
guard working as designed.

---

## Category B: Rule-based fallback (`source="self"`)

**Frequency in current data:** 3/15 (~20%)
**Written from:** `forkling/self_improve.py:SelfImprover.propose_and_apply` when LLM is unavailable or returned nothing

The proposal pipeline ran rule-based heuristics because either the
LLM endpoint was unreachable, returned an empty response, or the
post-processor found nothing to apply. The patch produced is empty.

**Recovery:** next reflection cycle (`reflect_every` generations)
asks the LLM to propose a plan; if connectivity restored, the
loop continues.

---

## Category C: Validator rejection — patch shape (`source="validate"`)

**Frequency in current data:** 4/15 (~27%)
**Written from:** `forkling/self_improve.py:SelfImprover` pre-`apply_patch` checks

The LLM produced a patch proposal, but the `old`/`new` substring
shape is wrong.

| Subcategory | Current count | Trigger |
|---|---|---|
| C1 — `old` not unique | 3/15 | `old` matches more than one location in the source. |
| C2 — `old` not found (0 occurrences) | 0/15 in current data | `old` doesn't appear in source at all. (Seen in early-stage data.) |
| C3 — empty / no-op patch | 1/15 | `old == new` (no actual change proposed). |

**Root cause for all C-class:** the LLM misread the source. The
graveyard excerpt is appended to the next proposal prompt so the
model gets a negative-example memory of its own mistakes. This is
the single largest opportunity for prompt engineering.

---

## Category D: Test-gate rejection (`source="test-gate"`)

**Frequency in current data:** 1/15 (~7%)
**Written from:** `forkling/evolve.py:Evolver.run_forever` after `pytest -q` exits non-zero

The patch *applied* and pytest ran, but at least one test failed.
Pytest stdout (truncated) goes into `reason`. The commit is rolled
back via `git checkout` and the patch is recorded here.

This is the *good* rejection class — selection pressure working.
The agent's proposal passed shape validation but didn't move the
fitness floor.

---

## Category E: JSON parse failure (currently co-mingled with B)

**Frequency in current data:** not directly counted; logged via
`Diary.write(kind="self-improve.rejected", ...)` rather than
`Graveyard` records because no path was ever assigned.

The LLM returned a non-JSON response (or the structured extractor
failed). Currently these go to the diary under
`kind="self-improve.rejected"` rather than the graveyard because
the `path` field is unknown. **Not yet in scope** for this
taxonomy; a v0.2 revision should classify these into a fifth
graveyard source, `source="parse"`.

---

## Category F: Unknown `kind` (currently co-mingled with B)

The LLM returned a `kind` value outside `{patch, new_file, noop}`.
Currently rejected to diary with `patch_summary="rejected:
unknown kind {...}"`. Treatment identical to E — planned for v0.2
split-out.

---

## Empirical observations from the current 15 entries

| Source | Count | Note |
|---|---|---|
| `validate` (A + C) | 11 | dominated by kernel-write + duplicate-old |
| `self` (B) | 3 | rule-based fallback — usually means LLM cold-start or downtime |
| `test-gate` (D) | 1 | the only patch that *landed-but-then-rolled-back* |

The mix is informative. Out of 15 LLM-initiated proposals, only
**1** (~7%) made it past shape validation, reached the working
tree, and was caught by selection. The other 14 were rejected
before any code ever moved. This means:

1. **The kernel guard is the dominant gate** (A: 47%). The
   agent is over-eager to propose kernel edits; SAFE_FILES
   guidance needs to be louder in the prompt.
2. **Shape validation is the second gate** (C: 27%). This
   is an LLM-attention problem, not an architecture problem.
3. **Selection is the rarest gate** (D: 7%). Almost every
   shape-valid patch gets to pytest. When pytest runs, the
   *good* news is that it's actually exercising the agent's
   proposals; the *bad* news is that the proposal stream is
   so over-filtered upstream that selection rarely sees
   serious candidates.

This is the publication-worthy finding: **most rejection
happens before selection pressure can be measured.** The
exp001/002/003 selection-pressure results are confounded by
this upstream filtering. A clean test would need to bypass A
and C temporarily and measure selection pressure against the
stream of shape-valid patches directly.

---

## What this taxonomy does NOT promise

- **It is not a label-checked ground truth.** A v0.2 classifier
  will be released alongside more data; expect reclassification.
- **It does not currently distinguish E and F.** A future
  patch should add a `source="parse"` and `source="kind"`
  field to separate JSON parse failure from unknown kind.
- **It cannot catch *successful* patches that introduce
  silent bugs.** A patch can pass pytest, land a commit, and
  introduce a regression that doesn't surface until later.
  The capability ledger's SHA chain is the only structural
  defense; downstream testing (replay, evals) handles the rest.

---

## v0.2 addendum (2026-09-26): a new failure class — measurement failure

The taxonomy above classifies **proposal-side** failures: things
the agent did wrong when proposing a patch. The post-exp003
audit ([`paper/exp003_results.md` "Validity caveat"](https://github.com/nuerainc/project-forkling/blob/main/paper/exp003_results.md))
revealed a fifth, distinct failure class that this v0.1
taxonomy does not cover:

**Class M — measurement failure.** The patch is fine; the
harness cannot detect the effect we asked it to detect.

| Subclass | Symptom | Fix in protocol 2 |
|---|---|---|
| M1 — endpoint blind to selection | pass@k returns 1 if any draw held-out-passes, so arm N and arm P score identically under protocol 1. | primary endpoint is `returned_pass` (the patch the arm actually returns), mean of S=5 replicates. |
| M2 — in-loop prompt decoupled from running source | I and R see the original buggy.py but patches apply to the evolved source; most post-attempt-0 patches fail to apply (`parse_ok` drops ~0.9 → ~0.3). | in-loop prompt now shows the current source + feedback block from the previous attempt (patch tried, kept?, visible failure output, 2000 chars). |
| M3 — re-ranker resolution | `visible_pass` is boolean; partial fixes (visible 1/2) tied wrong-but-parseable fixes (visible 0/2). | `bench.grade` reports `visible_passed` / `visible_total`; P ranks on the count; I accepts iff strictly more visible tests pass. |
| M4 — non-reproducible seeds | sub-seeds came from `hash((arm, task.id))`, which Python randomizes per process unless `PYTHONHASHSEED` is set. | sub-seeds from `zlib.crc32(seed, arm, task, replicate)`; Ollama `options` carry `temperature=0.8` and the derived per-call `seed`, both recorded in `config`. |
| M5 — wrong statistical test | `mann_whitney_u` is unpaired; for arms run on the same tasks, a paired test is correct. | paired exact Wilcoxon signed-rank on per-task signed differences + 10,000-resample bootstrap CI. |

**Why M-class failures are the most important to flag.** A
v0.1-style taxonomy only audits proposal-side failures. M-class
failures leave the graveyard empty; everything passes through
to commit (or to "committed-but-no-effect"), and the run looks
fine in the diary while the headline result is uninterpretable.
exp001–003 each "ran end to end" and each produced a clean
writeup; none of them could answer the question they pre-registered.
That is what M-class failures look like.

**The protocol-2 defence against M-class.** Three structural
gates:

1. **Harness self-test (`tests/test_experiment_power.py`)** —
   runs protocol 2 against scripted fake LLMs (filter,
   amplifier, null) and requires the harness to detect each.
   If the self-test cannot distinguish them, the harness
   cannot answer the question and no exp004 data is
   produced. This is the v4r1 §7 gate.
2. **No silent fallback in experiment mode.** Ollama
   errors record `infra: ...` (not model output). Calls
   that fail via the rule-based fallback are still counted
   as LLM calls but recorded with `used_llm=False`. If any
   arm exceeds the 20%-infra abort rule, the run aborts.
3. **Strict bench validation
   (`bench/validate_bench.py --strict`).** Fails any candidate
   whose `buggy.py` passes every held-out test, because the
   "unfixed" file would be graded as a fix and silently inflate
   the pass rate. All 12 FORKLAND-BENCH-002 candidates pass
   `--strict` at sign-off.

**Reading v0.1 and v0.2 together.** v0.1 is the taxonomy
you'd use to debug the agent ("why didn't this patch land?").
v0.2 is the taxonomy you'd use to debug the harness ("why
did this run look clean but produce no answer?"). Future
revisions should treat M-class as a first-class citizen with
its own counter, since a run without M-class failures is a
*necessary* condition for any exp004-era headline result to be
interpretable.
