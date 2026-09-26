from buggy import flatten


def test_tuples_nested_in_lists():
    assert flatten([(1, (2,)), [[3]]]) == [1, 2, 3]


def test_strings_are_values():
    assert flatten(["ab", ["c", ["de"]]]) == ["ab", "c", "de"]


def test_empty_nested():
    assert flatten([[], [[]], [[[]]]]) == []


def test_mixed_values_keep_order():
    assert flatten([None, [0, [False, [""]]]]) == [None, 0, False, ""]
