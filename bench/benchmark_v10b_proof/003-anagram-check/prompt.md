Fix the `is_anagram(s, t)` function in `buggy.py`. It should
return True if s and t are anagrams of each other, False
otherwise.

Examples:
- is_anagram("listen", "silent") -> True
- is_anagram("hello", "world") -> False
- is_anagram("conversation", "voices rant on") -> True
- is_anagram("", "") -> True
- is_anagram("aabb", "ababcc") -> False

Constraints:
- Case-insensitive: treat "A" and "a" as equal.
- Whitespace is ignored.
- Two empty strings are anagrams.
- Strings of different lengths are not anagrams.
