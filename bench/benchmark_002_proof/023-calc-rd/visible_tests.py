from buggy import calc


def test_mul_before_add():
    # Classic precedence: 1 + 2*3 == 7, not 9.
    assert calc("1 + 2 * 3") == 7


def test_mul_before_subtract():
    assert calc("10 - 2 * 3") == 4


def test_parens_override():
    assert calc("(1 + 2) * 3") == 9


def test_simple_addition():
    assert calc("1 + 2") == 3
