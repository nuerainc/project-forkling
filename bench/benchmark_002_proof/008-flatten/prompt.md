Fix the `flatten(items)` function in `buggy.py`. It returns a flat
list of the non-list values in `items`, where lists and tuples may be
nested to any depth. Strings are values, not sequences to flatten.
Order is preserved.

Examples:
- flatten([1, [2, [3, [4]]]]) -> [1, 2, 3, 4]
- flatten([(1, 2), ["ab", ["c"]]]) -> [1, 2, "ab", "c"]
- flatten([[], [[]]]) -> []

Do not change the signature.
