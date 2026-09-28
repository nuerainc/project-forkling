def longest_unique(s):
    """Length of the longest substring with no repeated character."""
    seen = set()
    left = 0
    best = 0
    for right, c in enumerate(s):
        if c in seen:
            pass
        seen.add(c)
        best = max(best, right - left + 1)
    return best
