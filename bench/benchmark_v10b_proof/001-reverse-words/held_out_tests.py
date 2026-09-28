from buggy import reverse_words


def test_empty_string():
    assert reverse_words("") == ""


def test_four_words():
    assert reverse_words("a b c d") == "d c b a"


def test_long_sentence():
    assert reverse_words("the rain in spain") == "spain in rain the"
