"""Probe qwen2.5-coder:7b with progressively larger prompts to find the failure mode."""
import json
import time
import urllib.request
import urllib.error

URL = "http://127.0.0.1:11434/api/generate"
MODEL = "qwen2.5-coder:7b"


def call(prompt: str, timeout: float = 60.0) -> tuple[int, str, float]:
    body = {"model": MODEL, "prompt": prompt, "stream": False}
    req = urllib.request.Request(
        URL,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            text = r.read().decode("utf-8", errors="replace")
        elapsed = time.monotonic() - t0
        return r.status, text, elapsed
    except urllib.error.HTTPError as e:
        elapsed = time.monotonic() - t0
        return e.code, e.read().decode("utf-8", errors="replace"), elapsed
    except urllib.error.URLError as e:
        elapsed = time.monotonic() - t0
        return -1, f"URLError: {e.reason}", elapsed
    except Exception as e:
        elapsed = time.monotonic() - t0
        return -2, f"{e.__class__.__name__}: {e}", elapsed


# Real-world experiment prompt shape: include prompt.md + buggy.py + visible_tests.py
# Build an example from task 003.
import sys
sys.path.insert(0, ".")
from forkling.bench import load_benchmark

bench = load_benchmark("bench/FORKLAND-BENCH-001.jsonl")
task = bench[2]  # 003-is-singleton
ad = task.abs_path()
buggy = (ad / "buggy.py").read_text(encoding="utf-8")
visible = (ad / "visible_tests.py").read_text(encoding="utf-8")
prompt = f"""You are fixing a small Python function. Produce a JSON patch.

Task: {task.prompt}

Current buggy.py:
```python
{buggy}
```

Visible tests:
```python
{visible}
```

Respond with JSON only."""

print(f"prompt size: {len(prompt)} chars")
print(f"estimated tokens: {len(prompt) // 4}")
print()

# Three runs to check for flakiness.
for i in range(3):
    status, body, dt = call(prompt, timeout=180.0)
    print(f"[run {i+1}] status={status} time={dt:.2f}s")
    if status != 200:
        print(f"  body[:500]={body[:500]}")
    else:
        try:
            obj = json.loads(body)
            resp = obj.get("response", "")
            print(f"  response[:200]={resp[:200]}")
            print(f"  response_len={len(resp)}")
        except Exception:
            print(f"  body[:500]={body[:500]}")
