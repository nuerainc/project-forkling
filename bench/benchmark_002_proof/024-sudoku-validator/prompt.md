Fix the `is_valid_sudoku(board)` function in `buggy.py`. It should
return `True` iff `board` (a 9x9 list of lists of single-character
strings) is a valid in-progress Sudoku board: each row, each column,
and each of the nine 3x3 sub-grids must contain no repeated digits
(`'1'`-`'9'`). Empty cells are represented by `'.'`. Pre-filled
digits must be consistent with all three constraints.

Examples (using `.` for empties):
- A board with no repeated digits in any row, column, or 3x3 box
  -> True
- A board with a digit repeated inside a single 3x3 box but not in
  the same row or column -> False

Do not change the signature. Do not solve the puzzle; just check
the constraints. The input is always exactly 9 lists of 9 strings.
