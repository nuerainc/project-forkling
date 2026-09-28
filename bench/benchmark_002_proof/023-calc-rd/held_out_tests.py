from buggy import calc


def test_chained_precedence():
    # 2 + 3*4 - 5 == 9, not (2+3)*4 - 5 == 15.
    assert calc("2 + 3 * 4 - 5") == 9


def test_div_before_subtract():
    assert calc("10 - 6 / 2") == 7


def test_nested_parens():
    assert calc("(2 + 3) * (4 - 1)") == 15


def test_single_number():
    assert calc("42") == 42


def test_div_before_add():
    # 1 + 8 / 2 == 5, not (1+8)/2 == 4.
    assert calc("1 + 8 / 2") == 5
