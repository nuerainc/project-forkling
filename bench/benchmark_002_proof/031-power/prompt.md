Fix the `power(base, exp)` function in `buggy.py`. It returns
`base ** exp` for a non-negative integer `exp`. By convention, any
non-zero `base` raised to `0` is `1`, and `0 ** 0` is `1`.

Examples:
- power(2, 3)  -> 8
- power(5, 0)  -> 1
- power(0, 5)  -> 0
- power(1, 10) -> 1

Do not use the `**` operator. Do not change the signature.