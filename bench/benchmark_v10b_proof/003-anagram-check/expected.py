def is_anagram(s, t):
    """Return True if s and t are anagrams of each other.

    Considers lowercase letters only and is case-insensitive.
    Whitespace is ignored.
    """
    s_clean = "".join(c for c in s.lower() if not c.isspace())
    t_clean = "".join(c for c in t.lower() if not c.isspace())
    return sorted(s_clean) == sorted(t_clean)
