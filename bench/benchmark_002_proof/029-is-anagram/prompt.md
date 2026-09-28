Fix the `is_anagram(s, t)` function in `buggy.py`. It returns `True` iff
`s` and `t` are anagrams of each other after stripping whitespace and
folding case to lowercase. In other words, ignoring spaces and
ignoring case, both strings must contain the same multiset of letters.

Examples:
- is_anagram("listen", "silent") -> True
- is_anagram("Hello", "hello")   -> True
- is_anagram("a b c", "abc")     -> True
- is_anagram("hello", "world")   -> False

Do not use the `collections` module. Do not change the signature.