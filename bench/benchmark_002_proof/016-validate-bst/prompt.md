Fix the `is_valid_bst(arr)` function in `buggy.py`. Validate a
binary search tree given as a level-order list of node values
(use `None` for missing children). Return `True` iff the structure
is a valid BST (left descendants strictly less than the node,
right descendants strictly greater than the node).

Examples:
- is_valid_bst([2, 1, 3]) -> True
- is_valid_bst([5, 1, 4, None, None, 3, 6]) -> False   (3 < 5 but
  3 sits in 5's right subtree)
- is_valid_bst([1]) -> True
- is_valid_bst([]) -> True
- is_valid_bst([5, 4, 7]) -> True

Do not change the signature. Do not use any third-party libraries.
