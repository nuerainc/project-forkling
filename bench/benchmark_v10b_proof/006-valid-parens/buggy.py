def is_valid_parens(s):
    """Return True if all parentheses in s are balanced.

    Supports (), [], and {}. An empty string is valid.
    """
    pairs = {")": "(", "]": "[", "}": "{"}
    stack = []
    for c in s:
        if c in "([{":
            stack.append(c)
        elif c in pairs:
            if not stack or stack.pop() != pairs[c]:
                return False
    return True
