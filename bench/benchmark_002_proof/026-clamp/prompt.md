Fix the `clamp(x, lo, hi)` function in `buggy.py`. It should return `x`
clamped to the closed range `[lo, hi]`: if `x < lo`, return `lo`; if
`x > hi`, return `hi`; otherwise return `x` itself. It is guaranteed
that `lo <= hi`.

Examples:
- clamp(-3, 0, 10) -> 0
- clamp(5, 0, 10) -> 5
- clamp(20, 0, 10) -> 10
- clamp(0, 0, 10) -> 0
- clamp(10, 0, 10) -> 10

Do not change the signature.