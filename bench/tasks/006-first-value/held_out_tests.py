from buggy import first_value


def test_empty_returns_none():
    # Buggy: StopIteration. Correct: None.
    assert first_value({}) is None


def test_none_value_present():
    # If the first VALUE happens to be None, return it (not the special
    # empty-dict None).
    assert first_value({"a": None, "b": 2}) is None


def test_multiple_keys_first_is_first():
    d = {"a": 10, "b": 20, "c": 30}
    assert first_value(d) == 10
