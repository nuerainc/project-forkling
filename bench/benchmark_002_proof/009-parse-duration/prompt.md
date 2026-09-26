Fix the `parse_duration(text)` function in `buggy.py`. It converts a
duration like "1h30m15s" to a number of seconds. Units are `h`, `m`
and `s`; each is optional, but every number must be followed by a
unit. Raise ValueError for an unknown unit or a trailing number with
no unit.

Examples:
- parse_duration("1h30m") -> 5400
- parse_duration("45s") -> 45
- parse_duration("2h5s") -> 7205
- parse_duration("5x") raises ValueError

Do not use the `re` module. Do not change the signature.
