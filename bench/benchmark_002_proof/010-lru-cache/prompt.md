Fix the `LRUCache` class in `buggy.py`. `LRUCache(capacity)` stores
at most `capacity` key/value pairs. `get(key)` returns the value, or
-1 if the key is absent. `put(key, value)` inserts or updates a key.
When inserting a new key into a full cache, the least recently used
key is evicted first. Both `get` (on a hit) and `put` count as a use.

Example:
    c = LRUCache(2)
    c.put("a", 1); c.put("b", 2)
    c.get("a")      # -> 1, "a" is now most recently used
    c.put("c", 3)   # evicts "b"
    c.get("b")      # -> -1

Standard library only. Do not change the method signatures.
