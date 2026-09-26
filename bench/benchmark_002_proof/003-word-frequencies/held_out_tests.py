from buggy import word_frequencies


def test_text_ends_with_word_no_trailing_separator():
    # Buggy: drops the last word if text ends with a letter.
    assert word_frequencies("hello world") == {"hello": 1, "world": 1}


def test_punctuation_separators():
    assert word_frequencies("hello, world! hello.") == {"hello": 2, "world": 1}


def test_digits_as_separators():
    assert word_frequencies("abc123def abc") == {"abc": 2, "def": 1}


def test_mixed_punctuation_no_spaces():
    assert word_frequencies("foo,bar;baz.qux") == {"foo": 1, "bar": 1, "baz": 1, "qux": 1}
