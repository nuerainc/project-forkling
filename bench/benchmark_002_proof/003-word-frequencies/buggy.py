def word_frequencies(text):
    """Count case-insensitive word occurrences in text."""
    counts = {}
    word = ""
    for c in text:
        if c.isalpha():
            word += c
        else:
            if word:
                key = word.lower()
                counts[key] = counts.get(key, 0) + 1
                word = ""
    # BUG: drops the last word if text ends with a letter (no
    # trailing separator). The expected behavior is to flush the
    # word at EOF.
    return counts
