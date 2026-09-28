from buggy import is_valid_parens


def test_simple_valid():
    assert is_valid_parens("()") is True


def test_simple_invalid():
    assert is_valid_parens("(]") is False


def test_unclosed_bracket():
    # Buggy version returns True whenever the loop completes without
    # an early-False; this test exposes the missing final empty-stack
    # check.
    assert is_valid_parens("(") is False
