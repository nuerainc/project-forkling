def is_anagram(s, t):
    """Return True iff s and t are anagrams (case-insensitive, ignore spaces)."""
    def normalize(x):
        return sorted(c for c in x.lower() if not c.isspace())
    return normalize(s) == normalize(t)