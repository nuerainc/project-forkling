Fix the `parse_csv(text)` function in `buggy.py`. It should
parse a CSV string into a list of rows, where each row is a list
of fields.

Examples:
- parse_csv("a,b\n1,2") -> [["a","b"], ["1","2"]]
- parse_csv("") -> []
- parse_csv('a,"b,c",d') -> [["a", "b,c", "d"]]
- parse_csv('"hello ""world""",x') -> [['hello "world"', 'x']]

Constraints:
- Handle quoted fields containing commas.
- Handle escaped quotes inside quoted fields (double-quote escape).
- Handle empty input (return []).
- Do NOT use the `csv` module from the standard library. Implement
  parsing from scratch.
