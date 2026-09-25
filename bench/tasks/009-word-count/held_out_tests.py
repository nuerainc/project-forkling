from buggy import word_count


def test_repeats():
    # The buggy code raises NameError on this because the loop runs and
    # `wrd` is referenced. Correct: {"a": 2, "b": 1}.
    assert word_count("a b a") == {"a": 2, "b": 1}


def test_many_repeats():
    assert word_count("x x x") == {"x": 3}


def test_multi_word_repeats():
    assert word_count("the cat the dog the") == {"the": 3, "cat": 1, "dog": 1}
