Fix the `is_sorted(arr)` function in `buggy.py`. It returns `True` if
`arr` is sorted in non-decreasing order (every element is `<=` the one
after it), and `False` otherwise. An empty list or a single-element
list is considered sorted.

Examples:
- is_sorted([1, 2, 2, 3]) -> True
- is_sorted([1, 3, 2]) -> False
- is_sorted([5, 5, 5]) -> True
- is_sorted([1, 2, 3]) -> True

Do not change the signature.