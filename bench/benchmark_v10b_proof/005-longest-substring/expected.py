def longest_unique_substring(s):
    """Return the length of the longest substring with no repeated chars.

    Uses a sliding window: expand the right pointer, then move the
    left pointer to just past the previous occurrence of the
    current character (only if that occurrence is inside the
    current window).
    """
    last_seen = {}
    left = 0
    best = 0
    for right, c in enumerate(s):
        if c in last_seen and last_seen[c] >= left:
            left = last_seen[c] + 1
        last_seen[c] = right
        if right - left + 1 > best:
            best = right - left + 1
    return best
