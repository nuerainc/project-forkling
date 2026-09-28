from buggy import eval_postfix


def test_division():
    # 8 / 4 = 2
    assert eval_postfix([8, 4, "/"]) == 2


def test_division_with_uneven_result():
    # tokens [7, 3, '/']: push 7, push 3; pop b=3, pop a=7.
    # Should yield 7 // 3 = 2 (floor).
    assert eval_postfix([7, 3, "/"]) == 2


def test_chained_division_after_subtraction():
    # (10 - 4) / 2 = 3
    assert eval_postfix([10, 4, "-", 2, "/"]) == 3


def test_zero_on_stack():
    # (0 + 5) * 2 = 10
    assert eval_postfix([0, 5, "+", 2, "*"]) == 10
