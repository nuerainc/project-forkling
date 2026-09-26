from buggy import roman_to_int


def test_simple_additive():
    assert roman_to_int("VIII") == 8


def test_subtractive_i():
    assert roman_to_int("IX") == 9


def test_subtractive_x():
    assert roman_to_int("XLII") == 42
