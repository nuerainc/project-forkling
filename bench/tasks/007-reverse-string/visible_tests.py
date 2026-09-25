from buggy import reverse_string


def test_basic():
    assert reverse_string("hello") == "olleh"


def test_single():
    assert reverse_string("a") == "a"
