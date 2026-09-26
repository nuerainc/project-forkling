from buggy import rle_decode


def test_no_counts():
    assert rle_decode("abc") == "abc"


def test_mixed_counts_and_bare_chars():
    assert rle_decode("a10b2c") == "a" + "b" * 10 + "cc"


def test_empty():
    assert rle_decode("") == ""


def test_count_with_zero_digit_inside():
    assert rle_decode("101z") == "z" * 101
