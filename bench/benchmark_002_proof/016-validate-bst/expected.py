def is_valid_bst(arr):
    """Validate a BST given as level-order values (None for missing)."""
    if not arr or arr[0] is None:
        return True

    def helper(i, lo, hi):
        if i >= len(arr) or arr[i] is None:
            return True
        v = arr[i]
        if v <= lo or v >= hi:
            return False
        return helper(2 * i + 1, lo, v) and helper(2 * i + 2, v, hi)

    return helper(0, float('-inf'), float('inf'))
