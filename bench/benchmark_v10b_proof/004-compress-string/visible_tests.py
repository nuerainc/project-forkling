from buggy import compress_string


def test_basic_compression():
    assert compress_string("aaabbc") == "a3b2c"


def test_no_compression_needed():
    assert compress_string("abcd") == "abcd"


def test_all_same_char():
    assert compress_string("aaaa") == "a4"
