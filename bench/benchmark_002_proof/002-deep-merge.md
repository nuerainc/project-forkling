Fix the `deep_merge(a, b)` function in `buggy.py`. It should
recursively merge two dicts, with values from `b` taking precedence
over values from `a`. Lists at the same key are concatenated.
Scalars at the same key are overwritten.

Examples:
- deep_merge({"x": 1}, {"x": 2}) -> {"x": 2}
- deep_merge({"x": {"a": 1}}, {"x": {"b": 2}}) -> {"x": {"a": 1, "b": 2}}
- deep_merge({"k": [1, 2]}, {"k": [3]}) -> {"k": [1, 2, 3]}
- deep_merge({}, {"a": 1}) -> {"a": 1}

Constraints:
- Do not modify either input dict in place.
- Handle the case where the same key has different types in a and b
  (b wins; no TypeError).
- Nested dicts merge recursively; lists concatenate; scalars
  overwrite.
