from buggy import reverse_words


def test_two_words():
    assert reverse_words("hello world") == "world hello"


def test_three_words():
    assert reverse_words("the quick brown") == "brown quick the"


def test_single_word():
    assert reverse_words("hello") == "hello"
