def reverse_in_place(arr):
    """Reverse arr in place using two pointers."""
    i = 0
    j = len(arr) - 1
    while i < j:
        arr[i], arr[j] = arr[j], arr[i]
        i += 1