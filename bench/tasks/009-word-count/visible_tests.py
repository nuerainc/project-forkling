from buggy import word_count


def test_empty():
    # Buggy: NameError because 'wrd' is undefined. But empty input would
    # not enter the loop, so this test actually passes on buggy code
    # (and on the fix).
    assert word_count("") == {}


def test_single_word():
    assert word_count("hello") == {"hello": 1}


def test_no_repeats():
    assert word_count("a b c") == {"a": 1, "b": 1, "c": 1}
