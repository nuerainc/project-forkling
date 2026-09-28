def is_valid_sudoku(board):
    """Return True iff the 9x9 board is consistent (rows + cols + boxes)."""
    for r in range(9):
        row = [board[r][c] for c in range(9) if board[r][c] != '.']
        if len(row) != len(set(row)):
            return False
        col = [board[c][r] for c in range(9) if board[c][r] != '.']
        if len(col) != len(set(col)):
            return False
    return True
