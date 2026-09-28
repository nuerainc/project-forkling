Fix the `compress_string(s)` function in `buggy.py`. It should
compress a string using run-length encoding.

Examples:
- compress_string("aaabbc") -> "a3b2c"
- compress_string("abcd") -> "abcd"
- compress_string("aaaa") -> "a4"
- compress_string("") -> ""
- compress_string("x") -> "x"

Constraints:
- Consecutive identical characters become the character followed
  by its count.
- Single-character runs are emitted without a count suffix.
- An empty input returns an empty string.
- The last run of the input must always be flushed (not dropped).
