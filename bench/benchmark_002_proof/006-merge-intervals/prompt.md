Fix the `merge_intervals(intervals)` function in `buggy.py`. Given a
list of closed intervals `[start, end]` (start <= end) in any order,
return a new sorted list in which overlapping or touching intervals
are merged.

Examples:
- merge_intervals([[1, 3], [2, 6], [8, 10]]) -> [[1, 6], [8, 10]]
- merge_intervals([[1, 2], [2, 3]]) -> [[1, 3]]
- merge_intervals([]) -> []

Do not modify the input list. Do not change the signature.
