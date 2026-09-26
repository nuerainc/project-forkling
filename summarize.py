"""Summarize any results/exp*.json. Args: path to JSON."""
import json
import sys
from pathlib import Path

p = Path(sys.argv[1] if len(sys.argv) > 1 else "results/exp001.json")
d = json.loads(p.read_text(encoding="utf-8"))

print(f"=== {p.name} summary ===")
cfg = d.get("config", {})
print(f"model: {cfg.get('model', '?')}  k_per_task: {cfg.get('k_per_task', '?')}  seed: {cfg.get('seed', '?')}")
print()
print("=== per-task pass@5 ===")
header = "{:>6} {:>3} {:>3} {:>3}".format("task", "A", "B", "C")
print(header)
for tid in sorted(d["per_task_pass_at_5"]):
    p_ = d["per_task_pass_at_5"][tid]
    print("{:>6} {:>3} {:>3} {:>3}".format(tid, p_["A"], p_["B"], p_["C"]))
print()
print("=== arm metrics ===")
m = d["metrics"]
for arm in "ABC":
    mm = m[arm]
    print("  arm {}: pass@1={:.2f} pass@5={:.2f} pass@10={:.2f} parse_ok={:.2f} commit={:.2f} n_records={}".format(
        arm, mm["pass_at_1"], mm["pass_at_5"], mm["pass_at_10"],
        mm["parse_ok_rate"], mm["commit_rate"], mm["n_records"]))
print()
print("=== stats ===")
for cmp, s in d["stats"].items():
    print("  {}: U={:.2f} p={:.4f}".format(cmp, s["u"], s["p"]))

# Per-arm parse + visible_pass + held_out_pass breakdown
print()
print("=== sanity checks (replicated from exp001 sanity) ===")
for arm in "ABC":
    recs = d["records"][arm]
    parsed = [r for r in recs if r["parse_ok"]]
    if arm == "A":
        print("  arm A: parse_ok={}/{}".format(len(parsed), len(recs)))
    elif arm == "B":
        committed = [r for r in parsed if r["committed"]]
        vpc = sum(1 for r in committed if r["visible_pass"])
        print("  arm B: parse_ok={}/{}, committed={}, of-committed-visible_pass={}/{}".format(
            len(parsed), len(recs), len(committed), vpc, max(len(committed),1)))
    elif arm == "C":
        committed = [r for r in parsed if r["committed"]]
        print("  arm C: parse_ok={}/{}, committed={} (rate={:.2f})".format(
            len(parsed), len(recs), len(committed), len(committed)/max(len(parsed),1)))

# Pre-registered interpretation
print()
print("=== pre-registered interpretation ===")
b_gt_a = m["B"]["pass_at_5"] > m["A"]["pass_at_5"]
b_gt_c = m["B"]["pass_at_5"] > m["C"]["pass_at_5"]
print("  B > A on pass@5: {}".format(b_gt_a))
print("  B > C on pass@5: {}".format(b_gt_c))
print("  B_vs_A p<0.025: {}".format(d["stats"]["B_vs_A"]["p"] < 0.025))
print("  B_vs_C p<0.025: {}".format(d["stats"]["B_vs_C"]["p"] < 0.025))
if b_gt_a and b_gt_c and d["stats"]["B_vs_A"]["p"] < 0.025 and d["stats"]["B_vs_C"]["p"] < 0.025:
    print("  RESULT: POSITIVE")
elif b_gt_a and b_gt_c:
    print("  RESULT: directionally positive but not significant (null per pre-registration)")
else:
    print("  RESULT: NULL")
