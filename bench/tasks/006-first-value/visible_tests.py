from buggy import first_value


def test_basic():
    assert first_value({"a": 1, "b": 2}) == 1


def test_single():
    assert first_value({"only": 99}) == 99


def test_empty_returns_none():
    # Buggy: StopIteration. Correct: None.
    assert first_value({}) is None


def test_strings():
    assert first_value({"x": "hello"}) == "hello"
