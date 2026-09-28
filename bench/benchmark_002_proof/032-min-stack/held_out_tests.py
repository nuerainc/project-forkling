from buggy import MinStack


def test_min_recovers_after_two_pops():
    s = MinStack()
    s.push(5)
    s.push(3)
    s.push(1)
    s.pop()
    assert s.getMin() == 3


def test_min_unaffected_when_popped_is_not_min():
    s = MinStack()
    s.push(5)
    s.push(3)
    s.push(10)
    s.pop()
    assert s.getMin() == 3


def test_min_then_pop_then_min():
    s = MinStack()
    s.push(2)
    s.push(4)
    s.push(1)
    assert s.getMin() == 1
    s.pop()
    assert s.getMin() == 2