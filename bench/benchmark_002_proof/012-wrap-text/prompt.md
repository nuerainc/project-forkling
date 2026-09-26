Fix the `wrap(text, width)` function in `buggy.py`. It greedily wraps
the words of `text` (split on whitespace) into lines joined by single
spaces, each at most `width` characters. A word longer than `width`
goes on a line of its own. Return the list of lines.

Examples:
- wrap("the quick brown fox", 10) -> ["the quick", "brown fox"]
- wrap("abc de", 5) -> ["abc", "de"]
- wrap("", 5) -> []

Do not use the `textwrap` module. Do not change the signature.
