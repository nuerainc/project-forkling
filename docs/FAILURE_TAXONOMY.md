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
