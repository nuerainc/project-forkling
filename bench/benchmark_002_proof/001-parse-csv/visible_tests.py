from buggy import parse_csv


def test_basic_two_rows():
    assert parse_csv("a,b\n1,2") == [["a", "b"], ["1", "2"]]


def test_empty_input():
    assert parse_csv("") == []


def test_single_field_no_newline():
    # Buggy: drops the last field if text doesn't end with newline.
    assert parse_csv("hello") == [["hello"]]
