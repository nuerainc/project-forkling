def binary_search(arr, target):
    """Standard binary search on a sorted list of distinct ints."""
    lo = 0
    hi = len(arr) - 1
    while lo < hi:
        mid = (lo + hi) // 2
        if arr[mid] == target:
            return mid
        if arr[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1
