def is_palindrome(s):
    """Return True if s is a palindrome, False otherwise.

    Considers only alphanumeric characters and ignores case.
    An empty string is a palindrome.
    """
    filtered = "".join(c for c in s if c.isalnum())
    return filtered == filtered[::-1]
