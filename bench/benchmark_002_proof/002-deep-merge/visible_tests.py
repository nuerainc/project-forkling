from buggy import deep_merge


def test_scalar_overwrite():
    # Buggy: returns scalar OK, but ...
    assert deep_merge({"x": 1}, {"x": 2}) == {"x": 2}


def test_dict_merge():
    assert deep_merge({"x": {"a": 1}}, {"x": {"b": 2}}) == {"x": {"a": 1, "b": 2}}


def test_list_concat():
    assert deep_merge({"k": [1, 2]}, {"k": [3]}) == {"k": [1, 2, 3]}
