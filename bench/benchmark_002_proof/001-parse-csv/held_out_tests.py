from buggy import parse_csv


def test_quoted_field_with_comma():
    assert parse_csv('a,"b,c",d') == [["a", "b,c", "d"]]


def test_escaped_quote_in_quoted_field():
    assert parse_csv('"hello ""world""",x') == [['hello "world"', 'x']]


def test_multiple_rows_no_trailing_newline():
    assert parse_csv("a,b\n1,2\n3,4") == [["a", "b"], ["1", "2"], ["3", "4"]]


def test_trailing_comma_makes_empty_field():
    # Trailing comma means the last field is empty.
    assert parse_csv("a,b,") == [["a", "b", ""]]
