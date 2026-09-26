def deep_merge(a, b):
    """Recursively merge dict b into a. b takes precedence.

    Lists at the same key are concatenated. Scalars overwrite.
    Returns a new dict (does not modify inputs).
    """
    out = dict(a)
    for k, v in b.items():
        if k in out:
            # BUG: missing recursive case for nested dicts.
            # The else branch below blindly overwrites dict-with-dict,
            # losing the keys from a.
            if isinstance(out[k], list) and isinstance(v, list):
                out[k] = out[k] + v
            else:
                out[k] = v
        else:
            out[k] = v
    return out
