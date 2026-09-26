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
    # Flush trailing word at EOF.
    if word:
        key = word.lower()
        counts[key] = counts.get(key, 0) + 1
    return counts
