from buggy import wrap


def test_simple_wrap():
    assert wrap("the quick brown fox", 10) == ["the quick", "brown fox"]


def test_space_counts_toward_width():
    assert wrap("abc de", 5) == ["abc", "de"]
