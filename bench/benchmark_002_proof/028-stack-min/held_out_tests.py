from buggy import StackMin


def test_min_before_any_pop():
    s = StackMin()
    s.push(5)
    s.push(3)
    assert s.min() == 3


def test_two_pops_reveal_new_min():
    s = StackMin()
    s.push(3)
    s.push(5)
    s.push(1)
    s.pop()
    assert s.min() == 3


def test_alternating_pushes_with_pop():
    s = StackMin()
    s.push(5)
    s.push(10)
    s.push(2)
    s.push(8)
    s.pop()
    s.pop()
    assert s.min() == 5


def test_min_unaffected_when_popped_is_not_min():
    s = StackMin()
    s.push(5)
    s.push(3)
    s.push(10)
    s.pop()
    assert s.min() == 3