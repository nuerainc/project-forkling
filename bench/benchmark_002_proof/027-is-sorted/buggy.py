def is_sorted(arr):
    """Return True iff arr is non-decreasing."""
    for i in range(len(arr) - 1):
        if arr[i] < arr[i + 1]:
            return False
    return True