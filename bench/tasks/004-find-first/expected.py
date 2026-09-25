def find_first(items, target):
    """Return the index of the first item equal to target, or -1."""
    for i, v in enumerate(items):
        if v == target:
            return i
    return -1
