Fix the `reverse_in_place(arr)` function in `buggy.py`. It reverses
the list `arr` IN PLACE using a two-pointer approach (one pointer
starts at the front, the other at the back; they move toward each
other and swap). The list is modified in place; nothing is returned.

Examples (the list is the same object before and after):
- reverse_in_place([1, 2, 3, 4]) -> [4, 3, 2, 1]
- reverse_in_place([])          -> []
- reverse_in_place([7])         -> [7]
- reverse_in_place([1, 2])      -> [2, 1]

Do not return a new list. Do not change the signature.