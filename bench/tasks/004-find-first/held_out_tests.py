from buggy import find_first


def test_equal_but_not_identical():
    # `is` checks identity. Build two strings that are EQUAL but built
    # at runtime so they cannot be folded to the same constant by the
    # peephole optimizer (which is what bit the previous version of
    # this test).
    a = "hello world"
    parts = ["hello ", "world"]
    b = "".join(parts)
    assert a == b
    assert a is not b, "string interning collapsed our test case"
    assert find_first([a], b) == 0


def test_equal_int_arithmetic():
    # 256 == 256 but `is` depends on small-int caching. Force a case
    # where they may differ: arithmetic.
    assert find_first([100 + 1], 101) == 0


def test_returns_correct_index():
    items = ["x", "y", "z"]
    target = "y"
    assert find_first(items, target) == 1


def test_list_of_lists_by_equality():
    # Lists compare by value with == but never by identity. The buggy
    # `is` will always miss these; the correct `==` will find them.
    assert find_first([[1, 2], [3, 4]], [3, 4]) == 1
