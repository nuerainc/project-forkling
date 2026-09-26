PAIRS = {")": "(", "]": "[", "}": "{"}


def is_balanced(s):
    """True if (), [] and {} in s are balanced and properly nested."""
    stack = []
    for c in s:
        if c in "([{":
            stack.append(c)
        elif c in PAIRS:
            if stack and stack[-1] == PAIRS[c]:
                stack.pop()
    return not stack
