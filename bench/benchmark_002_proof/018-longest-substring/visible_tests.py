from buggy import longest_unique


def test_no_repeats():
    assert longest_unique("abc") == 3


def test_duplicate_in_middle():
    # "abca" -> the longest unique substring is "abc" or "bca", length 3.
    assert longest_unique("abca") == 3


def test_two_repeats():
    # "pwwkew" -> longest is "wke", length 3.
    assert longest_unique("pwwkew") == 3


def test_classic_case():
    assert longest_unique("abcabcbb") == 3
