from buggy import rle_decode


def test_single_digit_counts():
    assert rle_decode("3a2b") == "aaabb"


def test_multi_digit_count():
    assert rle_decode("12x") == "x" * 12
