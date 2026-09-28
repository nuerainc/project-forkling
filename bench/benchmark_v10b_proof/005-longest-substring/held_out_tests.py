from buggy import longest_unique_substring


def test_empty():
    assert longest_unique_substring("") == 0


def test_pwwkew():
    assert longest_unique_substring("pwwkew") == 3


def test_tmmzuxt():
    # "tmmzuxt": correct returns 5 ("mzuxt"). Buggy version moves
    # the left pointer to last_seen['t']+1 = 1 on the final 't'
    # even though that 't' is outside the current window (left=5),
    # so it over-counts and returns 6.
    assert longest_unique_substring("tmmzuxt") == 5
