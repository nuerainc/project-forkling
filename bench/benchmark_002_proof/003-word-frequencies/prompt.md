Fix the `word_frequencies(text)` function in `buggy.py`. It should
return a dict mapping each word to the number of times it appears,
where "word" is a maximal sequence of letters (a-z, A-Z), and the
matching is case-insensitive ("The" and "the" count as the same
word). Non-letter characters are separators.

Examples:
- word_frequencies("hello world") -> {"hello": 1, "world": 1}
- word_frequencies("The the THE") -> {"the": 3}
- word_frequencies("hello, world! hello.") -> {"hello": 2, "world": 1}
- word_frequencies("") -> {}

Constraints:
- Words are sequences of ASCII letters only; digits, punctuation,
  and whitespace are separators.
- Match is case-insensitive; output keys are lowercase.
- Do NOT use the `re` module from the standard library. Implement
  parsing from scratch.
