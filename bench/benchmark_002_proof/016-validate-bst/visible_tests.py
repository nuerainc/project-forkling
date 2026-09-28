from buggy import is_valid_bst


def test_simple_valid():
    assert is_valid_bst([2, 1, 3]) is True


def test_deep_violation_in_right_subtree():
    # 6 sits in 10's right subtree (via 15 -> 6), but 6 < 10.
    # The local parent-child checks all pass, but the global invariant fails.
    assert is_valid_bst([10, 5, 15, None, None, 6, 20]) is False


def test_single_node():
    assert is_valid_bst([42]) is True


def test_empty_tree():
    assert is_valid_bst([]) is True
