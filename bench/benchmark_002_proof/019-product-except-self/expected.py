def product_except_self(arr):
    """Product of all other elements for each index. O(n)."""
    n = len(arr)
    out = [1] * n
    left = 1
    for i in range(n):
        out[i] = left
        left *= arr[i]
    right = 1
    for i in range(n - 1, -1, -1):
        out[i] *= right
        right *= arr[i]
    return out
