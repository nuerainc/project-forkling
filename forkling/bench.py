"""FORKLAND-BENCH-001 — frozen bug-fix benchmark loader and grader.

A task has the layout:

    bench/tasks/<id>/
      prompt.md           # natural-language description (visible to agent)
      buggy.py            # the buggy source the agent sees (visible)
      visible_tests.py    # tests the agent runs for selection (visible)
      held_out_tests.py   # tests the GRADER runs (NEVER visible to agent)
      expected.py         # canonical fix reference (grader-only)

The benchmark JSONL file (default bench/FORKLAND-BENCH-001.jsonl)
lists the task ids and their kinds.

Public surface:
    load_benchmark(path) -> list[BenchTask]
    grade(task, workdir) -> GradeResult
    validate_frozenness(bench_root) -> list[str]
"""
from __future__ import annotations

import ast
import dataclasses
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


@dataclasses.dataclass(frozen=True)
class BenchTask:
    id: str
    kind: str
    path: str  # relative to bench root
    prompt: str
    bench_root: Path

    def abs_path(self) -> Path:
        return self.bench_root / self.path

    def visible_dir(self) -> Path:
        """What the agent gets to see: prompt, buggy.py, visible_tests.py."""
        return self.abs_path()

    def grader_dir(self) -> Path:
        """What the grader sees: everything."""
        return self.abs_path()


@dataclasses.dataclass
class GradeResult:
    task_id: str
    visible_pass: bool
    held_out_pass: bool
    visible_failed: list[str]
    held_out_failed: list[str]
    error: str = ""
    # Added for protocol 2 (paper/hypothesis_v4r1.md): lets selectors rank
    # partial fixes and lets the in-loop prompt show test feedback.
    visible_total: int = 0
    visible_passed: int = 0
    visible_output: str = ""

    def passes_held_out(self) -> bool:
        return self.held_out_pass and not self.error


def load_benchmark(jsonl_path: str | Path) -> list[BenchTask]:
    """Load a benchmark JSONL file.

    Each line is a JSON object with keys: id, kind, path, prompt.
    """
    p = Path(jsonl_path)
    bench_root = p.parent
    tasks: list[BenchTask] = []
    with p.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as e:
                raise ValueError(
                    f"{p}:{line_no}: invalid JSON: {e}") from e
            for required in ("id", "kind", "path", "prompt"):
                if required not in obj:
                    raise ValueError(
                        f"{p}:{line_no}: missing key {required!r}")
            tasks.append(BenchTask(
                id=obj["id"],
                kind=obj["kind"],
                path=obj["path"],
                prompt=obj["prompt"],
                bench_root=bench_root,
            ))
    return tasks


def grade(task: BenchTask, patched_source: str,
          workdir: Path | None = None) -> GradeResult:
    """Apply patched_source as the new buggy.py, run visible + held-out.

    The patched_source should be the full content of the new buggy.py
    (the agent's proposed fix). We do NOT validate syntax here —
    pytest will report syntax errors as failures.

    Returns a GradeResult. The function never raises on test failure;
    it raises only on infra errors (missing files, workdir creation).
    """
    src_dir = task.abs_path()
    if not (src_dir / "buggy.py").is_file():
        return GradeResult(
            task_id=task.id, visible_pass=False, held_out_pass=False,
            visible_failed=[], held_out_failed=[],
            error=f"missing buggy.py in {src_dir}",
        )
    if not (src_dir / "visible_tests.py").is_file():
        return GradeResult(
            task_id=task.id, visible_pass=False, held_out_pass=False,
            visible_failed=[], held_out_failed=[],
            error=f"missing visible_tests.py in {src_dir}",
        )
    if not (src_dir / "held_out_tests.py").is_file():
        return GradeResult(
            task_id=task.id, visible_pass=False, held_out_pass=False,
            visible_failed=[], held_out_failed=[],
            error=f"missing held_out_tests.py in {src_dir}",
        )

    cleanup_workdir = False
    if workdir is None:
        workdir = Path(tempfile.mkdtemp(prefix=f"forkling-bench-{task.id}-"))
        cleanup_workdir = True

    try:
        # Copy the task dir into workdir so the patch is sandboxed.
        dst = workdir / task.path
        dst.mkdir(parents=True, exist_ok=True)
        for name in ("buggy.py", "visible_tests.py",
                     "held_out_tests.py", "expected.py"):
            src = src_dir / name
            if src.is_file():
                shutil.copy2(src, dst / name)
        # Apply the patch.
        (dst / "buggy.py").write_text(patched_source, encoding="utf-8")

        # Run visible tests.
        v_failed, v_err, v_out = _run_pytest_detailed(
            dst / "visible_tests.py", workdir)
        # Run held-out tests (separate process so a visible-test crash
        # cannot leak into held-out grading).
        h_failed, h_err = _run_pytest(dst / "held_out_tests.py", workdir)

        v_total = count_tests(dst / "visible_tests.py")
        v_passed = 0 if v_err else max(v_total - len(v_failed), 0)
        return GradeResult(
            task_id=task.id,
            visible_pass=(len(v_failed) == 0 and not v_err),
            held_out_pass=(len(h_failed) == 0 and not h_err),
            visible_failed=v_failed,
            held_out_failed=h_failed,
            error=v_err or h_err,
            visible_total=v_total,
            visible_passed=v_passed,
            visible_output=v_out,
        )
    finally:
        if cleanup_workdir:
            shutil.rmtree(workdir, ignore_errors=True)


def count_tests(test_path: Path) -> int:
    """Number of module-level ``test_*`` functions in a test file."""
    try:
        tree = ast.parse(test_path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return 0
    return sum(1 for node in tree.body
               if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
               and node.name.startswith("test_"))


def _run_pytest(test_path: Path, workdir: Path) -> tuple[list[str], str]:
    """Run pytest on test_path inside workdir. Return (failed_names, error).

    failed_names: list of "<file>::<testname>" for each failing test.
    error: stderr if pytest itself crashed (collection error, etc.).
    """
    failed, error, _ = _run_pytest_detailed(test_path, workdir, tb="no")
    return failed, error


def _run_pytest_detailed(test_path: Path, workdir: Path, tb: str = "short"
                         ) -> tuple[list[str], str, str]:
    """Like _run_pytest, plus pytest's stdout (empty when all tests pass).

    The pass/fail outcome does not depend on ``tb``; it only controls how
    much traceback text ends up in the returned output.
    """
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", str(test_path),
             f"--tb={tb}", "-q", "--no-header", "-p", "no:cacheprovider"],
            cwd=str(workdir),
            capture_output=True,
            text=True,
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        return [], "pytest timeout", ""
    except Exception as e:  # pragma: no cover
        return [], f"pytest launch failed: {e}", ""

    if result.returncode == 0:
        return [], "", ""

    # Parse "FAILED <file>::<test>" lines from stdout.
    failed: list[str] = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if line.startswith("FAILED "):
            failed.append(line[len("FAILED "):].split(" - ")[0])

    # If pytest returned non-zero but we couldn't parse FAILED lines,
    # it's likely a collection error or crash.
    if not failed and result.returncode != 0:
        return [], (result.stderr or result.stdout).strip()[:500], result.stdout

    return failed, "", result.stdout


def validate_frozenness(bench_root: Path,
                        jsonl_name: str = "FORKLAND-BENCH-001.jsonl"
                        ) -> list[str]:
    """Validate that the benchmark on disk is structurally well-formed.

    Returns a list of human-readable warnings. Empty list = OK.

    This is run BEFORE any agent sees the benchmark. If this raises,
    the benchmark is not frozen and must not be used.

    jsonl_name defaults to FORKLAND-BENCH-001.jsonl for backward
    compatibility; pass a different name to validate a sibling
    benchmark (e.g., "FORKLAND-BENCH-002.jsonl").
    """
    msgs: list[str] = []
    if not bench_root.is_dir():
        return [f"bench root does not exist: {bench_root}"]

    jsonl = bench_root / jsonl_name
    if not jsonl.is_file():
        return [f"missing benchmark manifest: {jsonl}"]

    try:
        tasks = load_benchmark(jsonl)
    except Exception as e:
        return [f"failed to load manifest: {e}"]

    if not tasks:
        return ["benchmark manifest is empty"]

    seen_ids: set[str] = set()
    for t in tasks:
        if t.id in seen_ids:
            msgs.append(f"duplicate task id: {t.id}")
        seen_ids.add(t.id)

        ad = t.abs_path()
        if not ad.is_dir():
            msgs.append(f"{t.id}: missing task dir {ad}")
            continue
        for fname in ("prompt.md", "buggy.py", "visible_tests.py",
                      "held_out_tests.py"):
            if not (ad / fname).is_file():
                msgs.append(f"{t.id}: missing {fname}")

    return msgs


def expected_fix(task: BenchTask) -> str | None:
    """Return the canonical fix content if present (grader-only)."""
    p = task.abs_path() / "expected.py"
    if p.is_file():
        return p.read_text(encoding="utf-8")
    return None


__all__ = [
    "BenchTask",
    "GradeResult",
    "load_benchmark",
    "grade",
    "count_tests",
    "validate_frozenness",
    "expected_fix",
]
