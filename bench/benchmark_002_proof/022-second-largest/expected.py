def second_largest(arr):
    """Return the second-largest distinct value, or None."""
    if not arr:
        return None
    distinct = sorted(set(arr))
    if len(distinct) < 2:
        return None
    return distinct[-2]
