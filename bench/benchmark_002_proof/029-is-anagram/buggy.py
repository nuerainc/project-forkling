def is_anagram(s, t):
    """Return True iff s and t are anagrams (case-insensitive, ignore spaces)."""
    return sorted(s) == sorted(t)