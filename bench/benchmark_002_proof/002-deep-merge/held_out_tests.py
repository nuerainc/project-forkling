from buggy import deep_merge


def test_does_not_mutate_inputs():
    a = {"x": {"y": 1}}
    b = {"x": {"z": 2}}
    snapshot_a = {"x": {"y": 1}}
    snapshot_b = {"x": {"z": 2}}
    _ = deep_merge(a, b)
    assert a == snapshot_a, "input a was mutated"
    assert b == snapshot_b, "input b was mutated"


def test_type_mismatch_b_wins():
    # a has dict, b has scalar. b should win without TypeError.
    assert deep_merge({"x": {"a": 1}}, {"x": 5}) == {"x": 5}
    # a has scalar, b has dict.
    assert deep_merge({"x": 5}, {"x": {"a": 1}}) == {"x": {"a": 1}}


def test_deeply_nested():
    a = {"l1": {"l2": {"l3": {"old": 1, "shared": "a"}}}}
    b = {"l1": {"l2": {"l3": {"new": 2, "shared": "b"}}}}
    expected = {"l1": {"l2": {"l3": {"old": 1, "shared": "b", "new": 2}}}}
    assert deep_merge(a, b) == expected


def test_disjoint_keys():
    assert deep_merge({"a": 1}, {"b": 2}) == {"a": 1, "b": 2}
