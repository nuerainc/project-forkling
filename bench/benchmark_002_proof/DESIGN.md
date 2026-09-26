# FORKLAND-BENCH-002 — Proof of Concept

**Status:** PROOF OF CONCEPT — not yet a frozen benchmark. 3 sample
tasks designed to validate the approach. exp003 (in flight) uses
FORKLAND-BENCH-001, not this one.

## Why a second benchmark

FORKAND-BENCH-001 is too easy. With `qwen2.5-coder:3b` and the
worked-example prompt, exp002 reached pass@10 = 1.00 on arm C
(random-accept iteration) and pass@10 = 0.80 on arms A and B
(one-shot and in-loop select). There's no room for arms to
separate.

A second benchmark should be calibrated so pass@5 in arm A is
~0.2–0.4, leaving real room for selection / iteration to matter.

## What's harder about this benchmark

| | FORKLAND-BENCH-001 | FORKLAND-BENCH-002 (proof) |
|---|---|---|
| Task scope | one-liner functions (~5 LOC) | multi-line functions (~30–60 LOC) |
| Bug class | off-by-one, wrong op, missing edge, wrong return, typo | state-machine bugs, recursive merging, character-class parsing |
| Stdlib banned | n/a | explicitly bans `re`, `csv` (forces hand-rolled parsing, where the bugs live) |
| Visible tests cover | happy path | happy path + 1-2 edge cases |
| Held-out tests | 2-4 specific cases | 3-4 specific cases targeting the bug class |

## Sample tasks

### 001-parse-csv (state-machine bug)

`parse_csv(text)` hand-rolls CSV parsing. The buggy version drops
the trailing field if text doesn't end with a newline. Visible test
catches it (single field, no newline). Held-out tests cover
quoted fields, escaped quotes, and trailing commas.

### 002-deep-merge (recursive data-structure bug)

`deep_merge(a, b)` recursively merges dicts. The buggy version
overwrites dict-with-dict at the same key, losing keys from `a`.
Visible test catches it (`deep_merge({"x": {"a": 1}}, {"x":
{"b": 2}})` should be `{"x": {"a": 1, "b": 2}}` but buggy gives
`{"x": {"b": 2}}`). Held-out tests cover input mutation,
type-mismatch, and deeply-nested merges.

### 003-word-frequencies (parser bug)

`word_frequencies(text)` counts case-insensitive word occurrences.
The buggy version drops the last word if text ends with a letter
(no trailing separator). Same shape as 001-parse-csv but in a
slightly different domain (character-class parsing, not field
parsing).

## Validation status

All 3 sample tasks pass structural validation:
- expected.py passes visible + held-out tests (frozen)
- buggy.py fails visible tests (selection signal present)
- expected.py and buggy.py are NOT identical (real bug, not
  tautology)

This validates the calibration target: these tasks are solvable
(by an LLM that writes the right fix) but require real reasoning
about edge cases.

## Open work to make this a full benchmark

- **5–10 more tasks** in similar spirit (state machines, parsers,
  recursive data structures, string algorithms, small numerical
  algorithms)
- **Calibration run** on the candidate tasks using arm A with
  current model — drop tasks where pass@1 ≥ 0.7 (too easy) or
  pass@1 ≤ 0.05 (impossible) until the 8–10 remaining tasks have
  arm A pass@5 in [0.2, 0.4]
- **Freeze benchmark** at that point and re-register exp004 with
  the new benchmark + same arm structure as exp003
- **Write benchmark validator** that mirrors `bench/validate_bench.py`
  for FORKLAND-BENCH-002 specifically

## Open question

Is the calibration target (`arm A pass@5 in [0.2, 0.4]`) the right
one? If `qwen2.5-coder:3b` lands in a different range on these
tasks, the calibration needs adjustment. The proof-of-concept
tasks will be the first place to test this.

## Pre-registration note

This is **not** a pre-registered experiment. The pre-registration
in `paper/hypothesis_v3.md` specifies exp003 on FORKLAND-BENCH-001
with the I-vs-P comparison. FORKLAND-BENCH-002 is for a future
experiment (e.g., exp004) that needs its own pre-registration.
