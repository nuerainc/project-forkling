Fix the `is_valid_parens(s)` function in `buggy.py`. It should
return True if all parentheses in s are balanced, False
otherwise.

Examples:
- is_valid_parens("()") -> True
- is_valid_parens("(]") -> False
- is_valid_parens("([{}])") -> True
- is_valid_parens("") -> True
- is_valid_parens("(") -> False
- is_valid_parens("(((") -> False

Constraints:
- Supports three bracket types: (), [], {}.
- An empty string is valid.
- Unclosed brackets make the input invalid.
- Mismatched bracket types make the input invalid.
