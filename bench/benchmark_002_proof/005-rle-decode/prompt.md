Fix the `rle_decode(s)` function in `buggy.py`. It decodes a
run-length encoded string: each character may be preceded by a
decimal count, and a character with no count appears once.

Examples:
- rle_decode("3a2b") -> "aaabb"
- rle_decode("ab") -> "ab"
- rle_decode("12x") -> "xxxxxxxxxxxx"
- rle_decode("") -> ""

Encoded characters are never digits. Do not use the `re` module.
Do not change the signature.
