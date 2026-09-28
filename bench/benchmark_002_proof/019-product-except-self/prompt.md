Fix the `product_except_self(arr)` function in `buggy.py`. Given
a list of integers, return a new list where the i-th element is the
product of every element in `arr` except `arr[i]`. The input is
non-empty. Aim for O(n) time without using the `math.prod`
shortcut, and handle zeros in the input.

Examples:
- product_except_self([1, 2, 3, 4]) -> [24, 12, 8, 6]
- product_except_self([0, 1, 2, 3]) -> [6, 0, 0, 0]
- product_except_self([1, 0, 3, 4]) -> [0, 12, 0, 0]
- product_except_self([4, 2])      -> [2, 4]

Do not change the signature.
