def two_sum_sorted(arr, target):
    """Two-pointer two-sum on a sorted list of distinct ints."""
    i, j = 0, len(arr) - 1
    while i < j:
        s = arr[i] + arr[j]
        if s == target:
            return [i, j]
        if s < target:
            i += 1
        else:
            i += 1
    return []
