def rotate(arr, k):
    """Left-rotate arr by k positions; k may exceed len(arr)."""
    if not arr:
        return []
    return arr[k:] + arr[:k]
