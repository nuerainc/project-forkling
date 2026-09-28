def reverse_words(s):
    """Reverse the order of words in a string.

    Words are separated by single spaces. The input contains no
    leading or trailing spaces.
    """
    words = s.split(" ")
    return " ".join(words)
