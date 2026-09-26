"""Validate FORKLAND-BENCH-001: structurally complete AND expected fixes pass both visible and held-out."""
import argparse
import sys
from pathlib import Path

# Allow running as a script from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from forkling.bench import (
    load_benchmark, grade, validate_frozenness, expected_fix, count_tests,
)

HINT_WORDS = ("bug", "fixme", "todo", "xxx", "hack", "wrong", "should")


def hint_comments(source: str) -> list[str]:
    """Comment lines in buggy.py that could point the model at the bug."""
    hits = []
    for line in source.splitlines():
        comment = line.partition("#")[2].strip().lower()
        if comment and any(w in comment for w in HINT_WORDS):
            hits.append(line.strip())
    return hits


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--bench", default=None,
                   help="Path to a specific benchmark JSONL. "
                        "Default: validate FORKLAND-BENCH-001.jsonl "
                        "in this script's parent directory.")
    p.add_argument("--jsonl-name", default="FORKLAND-BENCH-001.jsonl",
                   help="If --bench is not given, look for this filename "
                        "in the bench/ directory (default: FORKLAND-BENCH-001.jsonl).")
    p.add_argument("--strict", action="store_true",
                   help="Also enforce the FORKLAND-BENCH-002 authoring rules "
                        "(paper/hypothesis_v4r1.md §6): >=2 visible and >=3 "
                        "held-out tests, and no comments in buggy.py that "
                        "hint at the bug.")
    args = p.parse_args()

    bench_root = Path(__file__).resolve().parent
    if args.bench:
        jsonl = Path(args.bench)
        bench_root = jsonl.parent
    else:
        jsonl = bench_root / args.jsonl_name

    msgs = validate_frozenness(bench_root, jsonl_name=jsonl.name)
    if msgs:
        print("FROZENNESS FAILED:")
        for m in msgs:
            print(f"  - {m}")
        return 1
    print(f"[OK] bench frozen: {len(load_benchmark(jsonl))} tasks structurally complete")

    tasks = load_benchmark(jsonl)
    fail = 0
    for t in tasks:
        fix = expected_fix(t)
        if fix is None:
            print(f"[FAIL] {t.id}: missing expected.py")
            fail += 1
            continue
        result = grade(t, fix)
        if result.error:
            print(f"[FAIL] {t.id}: infra error: {result.error}")
            fail += 1
            continue
        if not result.visible_pass:
            print(f"[FAIL] {t.id}: visible tests still fail on expected fix: {result.visible_failed}")
            fail += 1
            continue
        if not result.held_out_pass:
            print(f"[FAIL] {t.id}: held-out tests fail on expected fix: {result.held_out_failed}")
            fail += 1
            continue
        buggy_src = (t.abs_path() / "buggy.py").read_text(encoding="utf-8")
        buggy_result = grade(t, buggy_src)
        if buggy_result.visible_pass:
            print(f"[FAIL] {t.id}: buggy.py passes every visible test "
                  "(no selection signal)")
            fail += 1
            continue
        if buggy_result.held_out_pass:
            print(f"[FAIL] {t.id}: buggy.py passes every held-out test "
                  "(an unfixed file would be graded as a fix)")
            fail += 1
            continue
        if args.strict:
            n_vis = count_tests(t.abs_path() / "visible_tests.py")
            n_held = count_tests(t.abs_path() / "held_out_tests.py")
            hints = hint_comments(buggy_src)
            problems = []
            if n_vis < 2:
                problems.append(f"{n_vis} visible tests (need >= 2)")
            if n_held < 3:
                problems.append(f"{n_held} held-out tests (need >= 3)")
            if hints:
                problems.append(f"hint comments in buggy.py: {hints}")
            if problems:
                print(f"[FAIL] {t.id}: " + "; ".join(problems))
                fail += 1
                continue
        print(f"[OK]   {t.id} ({t.kind}): expected fix passes visible + held-out; "
              "buggy.py fails visible + held-out")
    if fail:
        print(f"\n{fail} task(s) failed validation. Benchmark is NOT frozen.")
        return 1
    print(f"\nAll {len(tasks)} tasks validated. Benchmark IS frozen.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
