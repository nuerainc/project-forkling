from buggy import wrap


def test_long_word_on_own_line():
    assert wrap("a abcdefgh b", 3) == ["a", "abcdefgh", "b"]


def test_whitespace_collapses():
    assert wrap("  one   two\nthree ", 20) == ["one two three"]


def test_empty():
    assert wrap("", 5) == []


def test_exact_fit_and_every_line_within_width():
    lines = wrap("aa bb cc dd ee", 5)
    assert lines == ["aa bb", "cc dd", "ee"]
    assert all(len(l) <= 5 for l in lines)
