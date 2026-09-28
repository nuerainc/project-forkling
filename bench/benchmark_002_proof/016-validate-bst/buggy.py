def is_valid_bst(arr):
    """Validate a BST given as level-order values (None for missing)."""
    if not arr or arr[0] is None:
        return True
    n = len(arr)
    for i, v in enumerate(arr):
        if v is None:
            continue
        left = 2 * i + 1
        right = 2 * i + 2
        if left < n and arr[left] is not None and arr[left] >= v:
            return False
        if right < n and arr[right] is not None and arr[right] <= v:
            return False
    return True
