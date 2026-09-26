from buggy import roman_to_int


def test_full_year():
    assert roman_to_int("MCMXCIV") == 1994


def test_subtractive_c_before_d():
    assert roman_to_int("CDXLIV") == 444


def test_subtractive_c_before_m():
    assert roman_to_int("CM") == 900


def test_repeated_symbols():
    assert roman_to_int("MMMCCCXXXIII") == 3333
