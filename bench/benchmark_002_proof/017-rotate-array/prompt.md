Fix the `rotate(arr, k)` function in `buggy.py`. It returns a new
list containing the elements of `arr` rotated left by `k` positions
(left-rotation moves the first `k` elements to the end). `k` may be
larger than `len(arr)`; reduce it modulo `len(arr)` first.

Examples:
- rotate([1, 2, 3, 4, 5], 2) -> [3, 4, 5, 1, 2]
- rotate([1, 2, 3, 4, 5], 7) -> [3, 4, 5, 1, 2]   (7 mod 5 == 2)
- rotate([1, 2, 3], 0) -> [1, 2, 3]
- rotate([], 3) -> []

Do not change the signature. Do not modify the input list.
