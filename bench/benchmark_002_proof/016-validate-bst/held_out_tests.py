from buggy import is_valid_bst


def test_deep_violation_left_subtree():
    # 8 sits in 5's left subtree (via 3 -> 8), but 8 > 5.
    assert is_valid_bst([5, 3, 7, 2, 8, None, None]) is False


def test_full_balanced_bst():
    # All 7 nodes line up as a perfectly balanced BST.
    assert is_valid_bst([4, 2, 6, 1, 3, 5, 7]) is True


def test_immediate_violation_left_too_big():
    assert is_valid_bst([5, 7, 3]) is False


def test_two_node_valid():
    assert is_valid_bst([5, 3]) is True
