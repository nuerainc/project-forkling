from buggy import word_frequencies


def test_basic_two_words():
    assert word_frequencies("hello world") == {"hello": 1, "world": 1}


def test_empty():
    assert word_frequencies("") == {}


def test_case_insensitive():
    assert word_frequencies("The the THE") == {"the": 3}
