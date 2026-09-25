"""Verify qwen2.5-coder:3b fits fully in VRAM and follows the schema."""
import json, time, urllib.request

URL = "http://127.0.0.1:11434/api/generate"
MODEL = "qwen2.5-coder:3b"

import sys
sys.path.insert(0, ".")
from forkling.bench import load_benchmark
bench = load_benchmark("bench/FORKLAND-BENCH-001.jsonl")
task = bench[2]  # 003-is-singleton
ad = task.abs_path()
buggy = (ad / "buggy.py").read_text(encoding="utf-8")
visible = (ad / "visible_tests.py").read_text(encoding="utf-8")
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
- `old` MUST appear verbatim in buggy.py (copy-paste it; do not paraphrase).
- `new` MUST be the full replacement (include the same indentation).
- Do NOT wrap the JSON in markdown fences.
- Do NOT include prose, explanations, or code blocks around the JSON.
- Output exactly one JSON object, nothing else.

Task description:
{task.prompt}

Current buggy.py:
```python
{buggy}
```

Visible tests (these MUST still pass after your fix):
```python
{visible}
```

Constraints:
- Do NOT import anything outside the Python standard library.
- Do NOT change the function signature.
- Do NOT add new top-level definitions.
- Produce ONE patch.
"""

# Cold ping
print("[cold] first call (loads model)")
t0 = time.monotonic()
req = urllib.request.Request(
    URL,
    data=json.dumps({"model": MODEL, "prompt": prompt, "stream": False}).encode(),
    headers={"Content-Type": "application/json"},
)
with urllib.request.urlopen(req, timeout=300) as r:
    body = json.loads(r.read())
print(f"  cold time: {time.monotonic()-t0:.2f}s")
print(f"  response[:200]: {body.get('response', '')[:200]!r}")

# Warm
print()
print("[warm] second call (model resident)")
t0 = time.monotonic()
req = urllib.request.Request(
    URL,
    data=json.dumps({"model": MODEL, "prompt": prompt, "stream": False}).encode(),
    headers={"Content-Type": "application/json"},
)
with urllib.request.urlopen(req, timeout=120) as r:
    body = json.loads(r.read())
print(f"  warm time: {time.monotonic()-t0:.2f}s")
print(f"  response[:200]: {body.get('response', '')[:200]!r}")

# Check residency
print()
print("[residency] after warm call:")
with urllib.request.urlopen('http://127.0.0.1:11434/api/ps', timeout=5) as r:
    d = json.loads(r.read())
for m in d.get('models', []):
    name = m.get('name')
    size = m.get('size', 0) / 1e9
    vram = m.get('size_vram', 0) / 1e9
    print(f"  {name}: disk {size:.2f}GB  vram {vram:.2f}GB  ({vram/size*100:.0f}% in GPU)")
