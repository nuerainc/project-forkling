def product_except_self(arr):
    """Product of all other elements for each index. O(n)."""
    total = 1
    for x in arr:
        total *= x
    return [total // x for x in arr]
