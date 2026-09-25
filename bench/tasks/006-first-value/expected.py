def first_value(d):
    """Return the first value of dict d, or None if d is empty."""
    if not d:
        return None
    return next(iter(d.values()))
