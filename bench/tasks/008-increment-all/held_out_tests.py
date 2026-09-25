from buggy import increment_all


def test_negative():
    # Buggy returns [-1, 0], correct is [0, 1].
    assert increment_all([-1, 0]) == [0, 1]


def test_large_numbers():
    assert increment_all([99, 100, 101]) == [100, 101, 102]


def test_returns_new_object():
    src = [1, 2, 3]
    out = increment_all(src)
    assert out is not src
