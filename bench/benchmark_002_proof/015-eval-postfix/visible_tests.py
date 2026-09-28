from buggy import eval_postfix


def test_simple_addition():
    assert eval_postfix([1, 2, "+"]) == 3


def test_subtraction_left_minus_right():
    # postfix 5, 3, '-': stack push 5, push 3; pop b=3, pop a=5.
    # Should yield a - b = 5 - 3 = 2. Buggy yields b - a = 3 - 5 = -2.
    assert eval_postfix([5, 3, "-"]) == 2


def test_single_operand():
    assert eval_postfix([10]) == 10


def test_multiplication():
    assert eval_postfix([3, 4, "+", 2, "*"]) == 14
