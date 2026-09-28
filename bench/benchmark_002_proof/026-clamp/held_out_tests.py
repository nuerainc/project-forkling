from buggy import clamp


def test_far_above_hi():
    assert clamp(50, 0, 10) == 10


def test_below_lo():
    assert clamp(-3, 0, 10) == 0


def test_x_equals_lo():
    assert clamp(0, 0, 10) == 0


def test_x_equals_hi():
    assert clamp(10, 0, 10) == 10


def test_negative_range_above_hi():
    assert clamp(7, -5, 5) == 5