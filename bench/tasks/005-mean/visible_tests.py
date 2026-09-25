from buggy import mean


def test_basic():
    assert mean([1, 2, 3]) == 2.0


def test_single():
    assert mean([5]) == 5.0


def test_empty_returns_zero():
    # Buggy: ZeroDivisionError. Correct: 0.0.
    assert mean([]) == 0.0


def test_floats():
    assert mean([1.0, 2.0]) == 1.5
