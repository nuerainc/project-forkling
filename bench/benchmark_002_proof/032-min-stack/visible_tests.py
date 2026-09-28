from buggy import MinStack


def test_min_after_popping_min():
    s = MinStack()
    s.push(5)
    s.push(3)
    s.pop()
    assert s.getMin() == 5


def test_min_before_any_pop():
    s = MinStack()
    s.push(7)
    s.push(2)
    assert s.getMin() == 2