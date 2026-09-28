Fix the `longest_unique(s)` function in `buggy.py`. It returns the
length of the longest substring of `s` that contains no repeated
characters.

Examples:
- longest_unique("abcabcbb") -> 3   ("abc")
- longest_unique("bbbbb")    -> 1   ("b")
- longest_unique("pwwkew")   -> 3   ("wke")
- longest_unique("")         -> 0

Do not change the signature. ASCII letters are enough; do not
over-engineer for unicode.
