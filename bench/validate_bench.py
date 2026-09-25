"""Validate FORKLAND-BENCH-001: structurally complete AND expected fixes pass both visible and held-out."""
import sys
from pathlib import Path

# Allow running as a script from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from forkling.bench import (
    load_benchmark, grade, validate_frozenness, expected_fix,
)


def main() -> int:
    bench_root = Path(__file__).resolve().parent
    jsonl = bench_root / "FORKLAND-BENCH-001.jsonl"

    msgs = validate_frozenness(bench_root)
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
        print(f"[OK]   {t.id} ({t.kind}): visible + held-out pass on expected fix")
    if fail:
        print(f"\n{fail} task(s) failed validation. Benchmark is NOT frozen.")
        return 1
    print(f"\nAll {len(tasks)} tasks validated. Benchmark IS frozen.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
