"""Cold-load probe: confirm that the first call after unloading takes ~60s,
which is what the original '500 error' was likely a misattribution of."""
import json
import time
import urllib.request

# 1. Ask Ollama to unload the model (keep_alive=0)
print("[unload] POST /api/generate with keep_alive=0 to evict from memory")
req = urllib.request.Request(
    "http://127.0.0.1:11434/api/generate",
    data=json.dumps({"model": "qwen2.5-coder:7b", "keep_alive": 0}).encode(),
    headers={"Content-Type": "application/json"},
    method="POST",
)
try:
    with urllib.request.urlopen(req, timeout=10) as r:
        print(f"  status={r.status}")
except Exception as e:
    print(f"  {e.__class__.__name__}: {e}")

# 2. Confirm it's unloaded by listing running models
time.sleep(2)
try:
    with urllib.request.urlopen("http://127.0.0.1:11434/api/ps", timeout=5) as r:
        ps = json.loads(r.read())
        loaded = ps.get("models", [])
        if not loaded:
            print("[confirm] no models loaded in memory")
        else:
            print(f"[confirm] still loaded: {[m.get('name') for m in loaded]}")
except Exception as e:
    print(f"[confirm] {e.__class__.__name__}: {e}")

# 3. Cold call
print("\n[cold call] first prompt after unload")
t0 = time.monotonic()
req = urllib.request.Request(
    "http://127.0.0.1:11434/api/generate",
    data=json.dumps({
        "model": "qwen2.5-coder:7b",
        "prompt": "Reply with the single word: pong",
        "stream": False,
    }).encode(),
    headers={"Content-Type": "application/json"},
)
try:
    with urllib.request.urlopen(req, timeout=180) as r:
        body = json.loads(r.read())
        dt = time.monotonic() - t0
        print(f"  status={r.status} time={dt:.2f}s response={body.get('response', '')[:100]!r}")
except urllib.error.HTTPError as e:
    dt = time.monotonic() - t0
    print(f"  status={e.code} time={dt:.2f}s body={e.read().decode(errors='replace')[:300]}")
except Exception as e:
    dt = time.monotonic() - t0
    print(f"  ERR {e.__class__.__name__}: {e} (after {dt:.2f}s)")

# 4. Warm call (immediately after)
print("\n[warm call] second prompt, model now resident")
t0 = time.monotonic()
req = urllib.request.Request(
    "http://127.0.0.1:11434/api/generate",
    data=json.dumps({
        "model": "qwen2.5-coder:7b",
        "prompt": "Reply with the single word: pong",
        "stream": False,
    }).encode(),
    headers={"Content-Type": "application/json"},
)
try:
    with urllib.request.urlopen(req, timeout=180) as r:
        body = json.loads(r.read())
        dt = time.monotonic() - t0
        print(f"  status={r.status} time={dt:.2f}s response={body.get('response', '')[:100]!r}")
except urllib.error.HTTPError as e:
    dt = time.monotonic() - t0
    print(f"  status={e.code} time={dt:.2f}s body={e.read().decode(errors='replace')[:300]}")
