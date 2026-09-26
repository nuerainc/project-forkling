"""Check what models are pulled into Ollama and their sizes."""
import urllib.request, json

try:
    with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=5) as r:
        d = json.loads(r.read())
except Exception as e:
    print(f"FAIL: cannot reach Ollama: {e.__class__.__name__}: {e}")
    raise SystemExit(1)

models = d.get("models", [])
if not models:
    print("No models pulled into this Ollama instance.")
    raise SystemExit(0)

print(f"Models pulled: {len(models)}")
for m in models:
    size_gb = m.get("size", 0) / 1e9
    name = m.get("name", "?")
    details = m.get("details", {})
    fam = details.get("family", "?")
    param_size = details.get("parameter_size", "?")
    print(f"  {name:40s} {size_gb:6.2f} GB  family={fam}  params={param_size}")
