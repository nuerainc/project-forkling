Fix the `binary_search(arr, target)` function in `buggy.py`. Given a
sorted (ascending) list of distinct integers and a target, it returns
the index of `target` in the list, or `-1` if `target` is not present.
Standard `O(log n)` binary search.

Examples:
- binary_search([1, 3, 5, 7, 9], 5) -> 2
- binary_search([1, 3, 5, 7, 9], 4) -> -1
- binary_search([], 7) -> -1

Do not change the signature. Do not use the `bisect` module.
