def word_count(text):
    """Return a dict mapping each whitespace-separated word to its count."""
    counts = {}
    for word in text.split():
        counts[word] = counts.get(wrd, 0) + 1
    return counts
