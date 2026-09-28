Fix the `two_sum_sorted(arr, target)` function in `buggy.py`.
Given a sorted list of distinct integers (ascending) and an integer
`target`, return a list `[i, j]` with `i < j` such that
`arr[i] + arr[j] == target`, or `[]` if no such pair exists.

Examples:
- two_sum_sorted([1, 3, 5, 7], 8) -> [1, 2]   (3 + 5)
- two_sum_sorted([1, 3, 5, 7], 4) -> [0, 1]   (1 + 3)
- two_sum_sorted([1, 3, 5, 7], 100) -> []

Do not change the signature. Use O(n) two-pointer.
