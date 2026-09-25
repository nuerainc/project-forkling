def sum_range(start, stop):
    """Return the sum of all integers from start to stop, inclusive."""
    total = 0
    for i in range(start, stop + 1):
        total += i
    return total
