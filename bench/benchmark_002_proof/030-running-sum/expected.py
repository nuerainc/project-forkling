def running_sum(arr):
    """Return running (inclusive) sums of arr."""
    result = []
    total = 0
    for x in arr:
        total += x
        result.append(total)
    return result