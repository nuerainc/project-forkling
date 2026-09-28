def longest_unique(s):
    """Length of the longest substring with no repeated character."""
    last = {}
    left = 0
    best = 0
    for right, c in enumerate(s):
        if c in last and last[c] >= left:
            left = last[c] + 1
        last[c] = right
        if right - left + 1 > best:
            best = right - left + 1
    return best
