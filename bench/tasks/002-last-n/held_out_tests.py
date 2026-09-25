from buggy import last_n


def test_n_equals_len():
    # Off-by-one: -n-1 slice excludes the n-th-from-end element.
    # last_n([1,2,3], 3) should be [1,2,3], buggy returns [2,3].
    assert last_n([1, 2, 3], 3) == [1, 2, 3]


def test_strings():
    assert last_n(["a", "b", "c", "d"], 1) == ["d"]


def test_exact_one_off():
    # Specific off-by-one: 4 items, last 3.
    # Buggy: [4-3-1:] = [4-4:] = [] from items[0:].
    assert last_n([10, 20, 30, 40], 3) == [20, 30, 40]
