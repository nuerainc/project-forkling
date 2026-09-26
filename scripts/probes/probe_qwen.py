"""Send a minimal prompt to qwen2.5-coder:7b to reproduce the 500 error."""
import json
import time
import urllib.request
import urllib.error

URL = "http://127.0.0.1:11434/api/generate"
MODEL = "qwen2.5-coder:7b"


def call(prompt: str, timeout: float = 60.0, label: str = "") -> tuple[int, str, float]:
    body = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
    }
    req = urllib.request.Request(
        URL,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            status = r.status
            text = r.read().decode("utf-8", errors="replace")
        elapsed = time.monotonic() - t0
        return status, text, elapsed
    except urllib.error.HTTPError as e:
        elapsed = time.monotonic() - t0
        return e.code, e.read().decode("utf-8", errors="replace"), elapsed
    except urllib.error.URLError as e:
        elapsed = time.monotonic() - t0
        return -1, f"URLError: {e.reason}", elapsed
    except Exception as e:
        elapsed = time.monotonic() - t0
        return -2, f"{e.__class__.__name__}: {e}", elapsed


# 1. Minimal ping
status, body, dt = call("Hi", label="ping")
print(f"[ping] status={status} time={dt:.2f}s")
if status != 200:
    print(f"       body[:500]={body[:500]}")
else:
    try:
        obj = json.loads(body)
        print(f"       response[:200]={obj.get('response', '')[:200]}")
    except Exception:
        print(f"       body[:500]={body[:500]}")

# 2. Slightly larger
status, body, dt = call(
    "Write a Python function that adds two numbers.",
    timeout=120.0,
    label="small-task",
)
print(f"[small-task] status={status} time={dt:.2f}s")
if status != 200:
    print(f"             body[:500]={body[:500]}")
else:
    try:
        obj = json.loads(body)
        print(f"             response[:200]={obj.get('response', '')[:200]}")
    except Exception:
        print(f"             body[:500]={body[:500]}")
