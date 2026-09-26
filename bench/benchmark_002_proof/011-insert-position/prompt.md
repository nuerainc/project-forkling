Fix the `insert_position(items, x)` function in `buggy.py`. `items` is
sorted in ascending order and may contain duplicates. Return the
leftmost index at which `x` could be inserted while keeping `items`
sorted (so every element before the index is < x). It must run in
O(log n) time.

Examples:
- insert_position([1, 3, 5], 4) -> 2
- insert_position([1, 2, 2, 2, 3], 2) -> 1
- insert_position([], 7) -> 0

Do not use the `bisect` module. Do not change the signature.
