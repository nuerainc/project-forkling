from buggy import clamp


def test_in_range_middle():
    assert clamp(5, 0, 10) == 5


def test_above_hi():
    assert clamp(20, 0, 10) == 10