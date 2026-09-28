Fix the `eval_postfix(tokens)` function in `buggy.py`. Evaluate a
postfix (Reverse Polish) expression given as a list of integer
operands and string operators `+`, `-`, `*`, `/`. Each integer
division should use Python's default `//` (floor division).
Operands are non-negative ints.

Examples:
- eval_postfix([1, 2, "+"]) -> 3
- eval_postfix([3, 4, "+", 2, "*"]) -> 14
- eval_postfix([10]) -> 10
- eval_postfix([8, 4, "/"]) -> 2

Do not change the signature.
