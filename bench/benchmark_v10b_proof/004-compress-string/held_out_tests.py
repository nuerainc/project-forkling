from buggy import compress_string


def test_empty_string():
    assert compress_string("") == ""


def test_single_char():
    assert compress_string("x") == "x"


def test_long_pattern():
    assert compress_string("aaabbbcccdddeee") == "a3b3c3d3e3"
