from buggy import longest_unique


def test_all_same_char():
    # "bbbbb" -> length 1.
    assert longest_unique("bbbbb") == 1


def test_empty_string():
    assert longest_unique("") == 0


def test_single_char():
    assert longest_unique("z") == 1


def test_window_must_shrink():
    # "dvdf" -> "vdf" length 3; if the window never shrinks the answer
    # blows up to 4.
    assert longest_unique("dvdf") == 3


def test_duplicate_at_end():
    assert longest_unique("abcdd") == 4
