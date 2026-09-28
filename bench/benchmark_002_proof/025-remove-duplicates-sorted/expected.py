def remove_duplicates(arr):
    """Return a sorted list of distinct values from a sorted input."""
    result = []
    for x in arr:
        if not result or result[-1] != x:
            result.append(x)
    return result
