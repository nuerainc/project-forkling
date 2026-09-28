from buggy import longest_unique_substring


def test_basic():
    assert longest_unique_substring("abcabcbb") == 3


def test_all_unique():
    assert longest_unique_substring("abcdef") == 6


def test_repeat_outside_window():
    # "abba": with correct logic, the trailing 'a' is a repeat of an
    # occurrence that is OUTSIDE the current window, so it does NOT
    # move the left pointer. Result should be 2 ("ab" or "bb" or "ba").
    # Buggy version moves left to last_seen['a']+1 = 1, returning 3 ("bba").
    assert longest_unique_substring("abba") == 2
