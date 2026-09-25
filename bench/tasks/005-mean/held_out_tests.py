from buggy import mean


def test_empty_returns_zero():
    # Buggy: ZeroDivisionError. Correct: 0.0.
    assert mean([]) == 0.0


def test_negative_only():
    assert mean([-2, -4]) == -3.0


def test_mixed_signs():
    assert mean([-1, 0, 1]) == 0.0
