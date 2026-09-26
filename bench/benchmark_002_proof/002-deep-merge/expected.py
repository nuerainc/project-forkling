def deep_merge(a, b):
    """Recursively merge dict b into a. b takes precedence."""
    out = dict(a)
    for k, v in b.items():
        if k in out:
            if isinstance(out[k], dict) and isinstance(v, dict):
                out[k] = deep_merge(out[k], v)
            elif isinstance(out[k], list) and isinstance(v, list):
                out[k] = out[k] + v
            else:
                # Type mismatch or scalar: b wins.
                out[k] = v
        else:
            out[k] = v
    return out
