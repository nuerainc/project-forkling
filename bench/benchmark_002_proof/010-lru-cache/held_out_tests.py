from buggy import LRUCache


def test_update_existing_key_refreshes_and_keeps_size():
    c = LRUCache(2)
    c.put("a", 1)
    c.put("b", 2)
    c.put("a", 10)
    c.put("c", 3)
    assert c.get("b") == -1
    assert c.get("a") == 10
    assert c.get("c") == 3


def test_capacity_one():
    c = LRUCache(1)
    c.put("a", 1)
    c.put("b", 2)
    assert c.get("a") == -1
    assert c.get("b") == 2


def test_repeated_gets_protect_key():
    c = LRUCache(3)
    for k in "abc":
        c.put(k, k)
    c.get("a")
    c.get("b")
    c.put("d", "d")
    assert c.get("c") == -1
    assert [c.get(k) for k in "abd"] == ["a", "b", "d"]
