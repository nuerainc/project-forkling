from buggy import is_valid_parens


def test_empty_string():
    assert is_valid_parens("") is True


def test_only_opens():
    assert is_valid_parens("(((") is False


def test_unclosed_mixed():
    assert is_valid_parens("([") is False
