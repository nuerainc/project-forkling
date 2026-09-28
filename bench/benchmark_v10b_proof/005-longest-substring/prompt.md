Fix the `longest_unique_substring(s)` function in `buggy.py`.
It should return the length of the longest substring with no
repeated characters.

Examples:
- longest_unique_substring("abcabcbb") -> 3
- longest_unique_substring("abcdef") -> 6
- longest_unique_substring("aaaa") -> 1
- longest_unique_substring("") -> 0
- longest_unique_substring("dvdf") -> 3

Constraints:
- An empty input returns 0.
- Use a sliding-window approach: track the last seen index of each
  character; only move the left pointer forward if the previous
  occurrence is *inside* the current window.
