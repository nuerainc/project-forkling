"""Show exp003 per-task pass@5 by arm letter (N/P/I/R)."""
import json
d = json.load(open("results/exp003.json"))

print("=== exp003 per-task pass@5 (N/P/I/R) ===")
for tid in sorted(d["per_task_pass_at_5"]):
    p = d["per_task_pass_at_5"][tid]
    print(f"{tid:>6} N={p.get('N','?'):>3} P={p.get('P','?'):>3} I={p.get('I','?'):>3} R={p.get('R','?'):>3}")

print()
print("=== pass@5 means ===")
for arm in "NPIR":
    vals = [d["per_task_pass_at_5"][tid][arm] for tid in d["per_task_pass_at_5"]]
    avg = sum(vals) / len(vals)
    print(f"arm {arm}: pass@5 = {avg:.2f}  ({sum(vals)}/{len(vals)})")

print()
print("=== stats ===")
for cmp, s in d["stats"].items():
    print(f"  {cmp}: U={s['u']:.2f} p={s['p']:.4f}")

print()
print("=== sanity checks ===")
for arm in "NPIR":
    recs = d["records"][arm]
    parsed = [r for r in recs if r["parse_ok"]]
    if arm in ("N",):
        # No-iterate: parse_ok = how many parsed
        print(f"  arm {arm}: parse_ok={len(parsed)}/{len(recs)} ({len(parsed)/len(recs):.2f})")
    elif arm in ("I",):
        committed = [r for r in parsed if r["committed"]]
        vpc = sum(1 for r in committed if r["visible_pass"])
        print(f"  arm {arm}: parse_ok={len(parsed)}/{len(recs)} ({len(parsed)/len(recs):.2f}), committed={len(committed)}, of-committed visible_pass={vpc}/{len(committed)}")
    elif arm in ("R",):
        committed = [r for r in parsed if r["committed"]]
        rate = len(committed) / max(len(parsed), 1)
        print(f"  arm {arm}: parse_ok={len(parsed)}/{len(recs)} ({len(parsed)/len(recs):.2f}), committed={len(committed)} (rate={rate:.2f})")
    elif arm in ("P",):
        committed = [r for r in recs if r["committed"]]
        print(f"  arm {arm}: parse_ok={len(parsed)}/{len(recs)} ({len(parsed)/len(recs):.2f}), committed={len(committed)} (post-hoc winner)")

print()
print("=== pre-registered interpretation (paper/hypothesis_v3.md) ===")
b_gt_a = d["per_task_pass_at_5"]  # alias for clarity
# Primary comparison: I vs P
i_pass5 = sum(d["per_task_pass_at_5"][tid]["I"] for tid in d["per_task_pass_at_5"]) / 10.0
p_pass5 = sum(d["per_task_pass_at_5"][tid]["P"] for tid in d["per_task_pass_at_5"]) / 10.0
print(f"  I pass@5: {i_pass5:.2f}")
print(f"  P pass@5: {p_pass5:.2f}")
print(f"  I > P: {i_pass5 > p_pass5}")
print(f"  I_vs_P p<0.05: {d['stats']['I_vs_P']['p'] < 0.05}")
if i_pass5 > p_pass5 and d["stats"]["I_vs_P"]["p"] < 0.05:
    print("  RESULT: POSITIVE (selection is an amplifier)")
elif abs(i_pass5 - p_pass5) < 0.05:
    print("  RESULT: NULL (selection is a filter)")
else:
    print("  RESULT: NULL (I < P direction, no significance)")
