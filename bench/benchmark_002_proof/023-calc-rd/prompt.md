Fix the `calc(s)` function in `buggy.py`. Evaluate a basic integer
arithmetic expression using `+`, `-`, `*`, `/` (integer division) and
parentheses. Multiplication and division bind tighter than addition
and subtraction. Whitespace may appear between tokens.

Examples:
- calc("1 + 2 * 3")        -> 7
- calc("(1 + 2) * 3")      -> 9
- calc("10 - 6 / 2")       -> 7
- calc("2 + 3 * 4 - 5")    -> 9
- calc("100")              -> 100

Do not change the signature. Do not use `eval`. Operands are
non-negative integers; the result fits in a normal Python int.
