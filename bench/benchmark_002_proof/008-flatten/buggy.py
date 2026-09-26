def flatten(items):
    """Flatten nested lists/tuples into one list; strings stay whole."""
    out = []
    for item in items:
        if isinstance(item, (list, tuple)):
            out.extend(item)
        else:
            out.append(item)
    return out
