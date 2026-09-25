"""Summarize exp001 results for the report."""
import json
import sys
from pathlib import Path

d = json.loads(Path("results/exp001.json").read_text(encoding="utf-8"))

print("=== per-task pass@5 ===")
header = f"{'task':>6} {'A':>3} {'B':>3} {'C':>3}"
print(header)
for tid in sorted(d["per_task_pass_at_5"]):
    p = d["per_task_pass_at_5"][tid]
    print(f"{tid:>6} {p['A']:>3} {p['B']:>3} {p['C']:>3}")

print()
print("=== arm A (baseline): parse_ok, pass@5 ===")
a_recs = d["records"]["A"]
print(f"total attempts: {len(a_recs)}")
print(f"parse_ok: {sum(1 for r in a_recs if r['parse_ok'])} ({sum(1 for r in a_recs if r['parse_ok'])/len(a_recs):.2f})")
print(f"visible_pass: {sum(1 for r in a_recs if r['visible_pass'])}")
print(f"held_out_pass: {sum(1 for r in a_recs if r['held_out_pass'])}")

print()
print("=== arm B (evolve+select): parse_ok, selection_rate ===")
b_recs = d["records"]["B"]
parsed_b = [r for r in b_recs if r["parse_ok"]]
print(f"total attempts: {len(b_recs)}, parse_ok: {len(parsed_b)}")
committed_b = [r for r in parsed_b if r["committed"]]
print(f"committed (selected): {len(committed_b)} / parse_ok ({len(parsed_b)}) = {len(committed_b)/max(len(parsed_b),1):.2f}")
visible_pass_committed = sum(1 for r in committed_b if r["visible_pass"])
print(f"of committed, visible_pass: {visible_pass_committed}/{len(committed_b)} = {visible_pass_committed/max(len(committed_b),1):.2f}")

print()
print("=== arm C (evolve+random): parse_ok, accept_rate ===")
c_recs = d["records"]["C"]
parsed_c = [r for r in c_recs if r["parse_ok"]]
print(f"total attempts: {len(c_recs)}, parse_ok: {len(parsed_c)}")
committed_c = [r for r in parsed_c if r["committed"]]
print(f"committed (accepted at 0.5): {len(committed_c)} / parse_ok ({len(parsed_c)}) = {len(committed_c)/max(len(parsed_c),1):.2f}")

print()
print("=== stats ===")
print(f"B_vs_A: U={d['stats']['B_vs_A']['u']:.2f} p={d['stats']['B_vs_A']['p']:.4f}")
print(f"B_vs_C: U={d['stats']['B_vs_C']['u']:.2f} p={d['stats']['B_vs_C']['p']:.4f}")

print()
print("=== interpretation (pre-registered) ===")
m = d["metrics"]
print(f"pass@5: A={m['A']['pass_at_5']:.2f} B={m['B']['pass_at_5']:.2f} C={m['C']['pass_at_5']:.2f}")
print(f"pass@10: A={m['A']['pass_at_10']:.2f} B={m['B']['pass_at_10']:.2f} C={m['C']['pass_at_10']:.2f}")
print()
print("Pre-registered interpretation:")
print("  - B > A AND B > C with p<0.025 -> positive")
print("  - any other outcome -> null")
p_ba = d["stats"]["B_vs_A"]["p"]
p_bc = d["stats"]["B_vs_C"]["p"]
b_gt_a = m["B"]["pass_at_5"] > m["A"]["pass_at_5"]
b_gt_c = m["B"]["pass_at_5"] > m["C"]["pass_at_5"]
print(f"  - B > A on pass@5: {b_gt_a}")
print(f"  - B > C on pass@5: {b_gt_c}")
print(f"  - B_vs_A p<0.025: {p_ba < 0.025}")
print(f"  - B_vs_C p<0.025: {p_bc < 0.025}")
if b_gt_a and b_gt_c and p_ba < 0.025 and p_bc < 0.025:
    print("  RESULT: POSITIVE")
elif b_gt_a and b_gt_c:
    print("  RESULT: directionally positive but not significant (also null per pre-registration)")
else:
    print("  RESULT: NULL")
