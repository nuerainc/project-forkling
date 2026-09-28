from buggy import StackMin


def test_after_pop_min_updates():
    s = StackMin()
    s.push(5)
    s.push(1)
    s.pop()
    assert s.min() == 5


def test_min_before_any_pop():
    s = StackMin()
    s.push(7)
    s.push(2)
    assert s.min() == 2