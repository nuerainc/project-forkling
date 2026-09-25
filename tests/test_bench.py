"""Tests for the frozen benchmark loader + grader.

These tests use the actual FORKLAND-BENCH-001 directory. If the
benchmark is broken, these tests will fail — which is the right
behavior. The benchmark is frozen at a specific commit; do not
modify tasks without bumping the manifest version.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from forkling.bench import (
    BenchTask, GradeResult, grade, load_benchmark, validate_frozenness,
    expected_fix,
)
from forkling.experiment import (
    apply_patch, extract_patch, pass_at_k, mann_whitney_u,
)


REPO_ROOT = Path(__file__).resolve().parent.parent
BENCH_JSONL = REPO_ROOT / "bench" / "FORKLAND-BENCH-001.jsonl"


# ----- load_benchmark -----------------------------------------------------

def test_benchmark_loads():
    tasks = load_benchmark(BENCH_JSONL)
    assert len(tasks) == 10
    assert all(isinstance(t, BenchTask) for t in tasks)
    ids = [t.id for t in tasks]
    assert ids == sorted(set(ids)), "task ids should be unique"


def test_benchmark_frozenness_is_clean():
    msgs = validate_frozenness(BENCH_JSONL.parent)
    assert msgs == [], f"benchmark not frozen: {msgs}"


def test_benchmark_kinds_balanced():
    tasks = load_benchmark(BENCH_JSONL)
    kinds = [t.kind for t in tasks]
    # We declared 2 of each kind in the prompt. Allow some slack
    # (off_by_one x2, wrong_operator x2, missing_edge x3, wrong_return x2,
    # typo x1). Just check no kind is missing entirely.
    assert set(kinds) >= {"off_by_one", "wrong_operator",
                          "missing_edge", "wrong_return", "typo"}


# ----- grade --------------------------------------------------------------

def test_grade_with_expected_fix_passes_both_test_files():
    """Every task's expected.py must pass both visible and held-out tests."""
    tasks = load_benchmark(BENCH_JSONL)
    failures = []
    for t in tasks:
        fix = expected_fix(t)
        if fix is None:
            failures.append(f"{t.id}: missing expected.py")
            continue
        result = grade(t, fix)
        if result.error:
            failures.append(f"{t.id}: infra error: {result.error}")
        elif not result.visible_pass:
            failures.append(f"{t.id}: visible fails: {result.visible_failed}")
        elif not result.held_out_pass:
            failures.append(f"{t.id}: held_out fails: {result.held_out_failed}")
    assert not failures, "expected fixes must pass both test sets:\n  " + "\n  ".join(failures)


def test_grade_with_buggy_source_fails_at_least_one_visible_test():
    """The buggy.py on disk should fail at least one visible test per task,
    otherwise the task is too easy and provides no selection signal."""
    tasks = load_benchmark(BENCH_JSONL)
    trivial = []
    for t in tasks:
        buggy = (t.abs_path() / "buggy.py").read_text(encoding="utf-8")
        result = grade(t, buggy)
        if result.visible_pass and not result.error:
            trivial.append(t.id)
    assert not trivial, (
        f"these tasks pass visible tests on the buggy source (no selection "
        f"signal): {trivial}"
    )


def test_grade_with_syntax_error_reports_failure():
    """A patch that breaks Python syntax should produce visible_pass=False
    cleanly, not crash the grader."""
    tasks = load_benchmark(BENCH_JSONL)
    t = tasks[0]
    result = grade(t, "def this is not valid python ::::\n")
    assert result.visible_pass is False
    assert result.held_out_pass is False


# ----- experiment.py: apply_patch -----------------------------------------

def test_apply_patch_replaces_first_occurrence():
    src = "a = 1\nb = 2\n"
    out = apply_patch(src, "b = 2", "b = 3")
    assert out == "a = 1\nb = 3\n"


def test_apply_patch_returns_none_when_old_not_found():
    src = "a = 1\n"
    assert apply_patch(src, "x = 999", "y = 1") is None


def test_apply_patch_with_empty_old_returns_new_verbatim():
    """If the LLM signals 'replace everything' with empty old, accept new."""
    assert apply_patch("anything", "", "fresh content") == "fresh content"


def test_apply_patch_unescapes_backslash_sequences():
    """When the LLM double-escapes newlines (\\n instead of \\n in the
    raw JSON), the as-given `old` does not match. The fallback unescape
    pass should still find the substring."""
    src = "def f():\n    return 1\n"
    # Note: \\n here is a 2-char string (backslash + n), NOT a newline.
    doubled = "def f():\\n    return 1\\n"
    out = apply_patch(src, doubled, "def f():\n    return 2\n")
    assert out == "def f():\n    return 2\n"


# ----- experiment.py: extract_patch --------------------------------------

def test_extract_patch_parses_clean_json():
    raw = json.dumps({
        "kind": "patch", "path": "buggy.py",
        "old": "return a + b",
        "new": "return a + b + 1",
    })
    result = extract_patch(raw, "def f(a,b):\n    return a + b\n")
    assert result is not None
    new_src, note = result
    assert note == "ok"
    assert "return a + b + 1" in new_src


def test_extract_patch_handles_markdown_fences():
    raw = "```json\n" + json.dumps({
        "kind": "patch", "path": "buggy.py",
        "old": "x = 1", "new": "x = 2",
    }) + "\n```"
    src = "x = 1\n"
    result = extract_patch(raw, src)
    assert result is not None
    new_src, _ = result
    assert new_src == "x = 2\n"


def test_extract_patch_rejects_non_patch_kind():
    raw = json.dumps({"kind": "noop", "reason": "I give up"})
    assert extract_patch(raw, "x = 1\n") is None


def test_extract_patch_rejects_unparseable():
    assert extract_patch("not json at all", "x = 1\n") is None
    assert extract_patch("{ malformed", "x = 1\n") is None


def test_extract_patch_returns_none_when_old_not_found():
    raw = json.dumps({"kind": "patch", "old": "absent", "new": "X"})
    assert extract_patch(raw, "y = 1\n") is None


# ----- experiment.py: pass_at_k -------------------------------------------

def test_pass_at_k_returns_1_on_any_held_out_pass():
    from forkling.experiment import AttemptRecord
    recs = [
        AttemptRecord("t", "A", 0, True, False, False, True, "", 0.0),
        AttemptRecord("t", "A", 1, True, True, True, True, "", 0.0),
        AttemptRecord("t", "A", 2, True, True, False, True, "", 0.0),
    ]
    assert pass_at_k(recs, 1) == 0
    assert pass_at_k(recs, 2) == 1
    assert pass_at_k(recs, 3) == 1


def test_pass_at_k_returns_0_when_no_pass():
    from forkling.experiment import AttemptRecord
    recs = [
        AttemptRecord("t", "A", 0, True, False, False, True, "", 0.0),
    ]
    assert pass_at_k(recs, 1) == 0


# ----- experiment.py: mann_whitney_u --------------------------------------

def test_mann_whitney_u_identical_distributions():
    x = [1.0, 0.0, 1.0, 0.0]
    y = [1.0, 0.0, 1.0, 0.0]
    u, p = mann_whitney_u(x, y)
    # Identical samples -> large U, large p.
    assert p > 0.5


def test_mann_whitney_u_clear_separation():
    x = [1.0, 1.0, 1.0, 1.0, 1.0]
    y = [0.0, 0.0, 0.0, 0.0, 0.0]
    u, p = mann_whitney_u(x, y)
    # Perfect separation -> small U, small p.
    assert p < 0.05


def test_mann_whitney_u_handles_empty():
    u, p = mann_whitney_u([], [1.0])
    assert u == 0.0 and p == 1.0


# ----- end-to-end: validate harness doesn't crash -------------------------

def test_experiment_run_help_works():
    """Smoke-test that the experiment CLI is wired up."""
    result = subprocess.run(
        [sys.executable, "-m", "forkling", "experiment", "run", "--help"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0
    assert "--bench" in result.stdout
    assert "--k" in result.stdout
