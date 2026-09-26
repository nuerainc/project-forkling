"""Test if qwen2.5-coder:7b follows an explicit JSON schema when given
an example in the prompt."""
import json
import time
import urllib.request

URL = "http://127.0.0.1:11434/api/generate"
MODEL = "qwen2.5-coder:7b"

import sys
sys.path.insert(0, ".")
from forkling.bench import load_benchmark

bench = load_benchmark("bench/FORKLAND-BENCH-001.jsonl")
task = bench[2]  # 003-is-singleton
ad = task.abs_path()
buggy = (ad / "buggy.py").read_text(encoding="utf-8")
visible = (ad / "visible_tests.py").read_text(encoding="utf-8")

# Tighter prompt: explicit schema with a worked example.
prompt = f"""You are fixing a small Python function. Produce a JSON patch
with this EXACT shape (no other fields, no list, just this object):

{{"kind": "patch", "path": "buggy.py",
  "old": "<the EXACT substring in buggy.py you are replacing>",
  "new": "<the replacement text>"}}

Worked example — given buggy.py:
```python
def add(a, b):
    return a - b
```
and the task "add should add", the correct response is:
{{"kind": "patch", "path": "buggy.py",
  "old": "return a - b", "new": "return a + b"}}

Rules:
- `old` MUST appear verbatim in buggy.py (copy-paste it, do not paraphrase).
- `new` MUST be the full replacement (include the same indentation).
- Do NOT wrap the JSON in markdown fences.
- Do NOT include prose, explanations, or code blocks around the JSON.
- Output exactly one JSON object, nothing else.

Task: {task.prompt}

Current buggy.py:
```python
{buggy}
```

Visible tests (your patch MUST keep these passing):
```python
{visible}
```"""

print(f"prompt size: {len(prompt)} chars")

t0 = time.monotonic()
req = urllib.request.Request(
    URL,
    data=json.dumps({
        "model": MODEL, "prompt": prompt, "stream": False,
    }).encode(),
    headers={"Content-Type": "application/json"},
)
with urllib.request.urlopen(req, timeout=120) as r:
    body = json.loads(r.read())
dt = time.monotonic() - t0
print(f"time: {dt:.2f}s")
resp = body.get("response", "")
print(f"raw response:\n{resp}\n---")

# Try to parse as JSON
try:
    obj = json.loads(resp.strip())
    print(f"parsed type: {type(obj).__name__}")
    if isinstance(obj, dict):
        print(f"keys: {list(obj.keys())}")
        if obj.get("kind") == "patch":
            print("SCHEMA OK: kind=patch")
            print(f"  old: {obj.get('old', '')[:80]!r}")
            print(f"  new: {obj.get('new', '')[:80]!r}")
        else:
            print(f"SCHEMA MISMATCH: kind={obj.get('kind')!r}")
    elif isinstance(obj, list):
        print(f"SCHEMA MISMATCH: got list of {len(obj)} items")
        print(f"first item: {obj[0] if obj else 'empty'}")
except json.JSONDecodeError as e:
    print(f"PARSE FAIL: {e}")
