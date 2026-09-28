def eval_postfix(tokens):
    """Evaluate a postfix expression. tokens alternates operands and operators."""
    stack = []
    for tok in tokens:
        if isinstance(tok, int):
            stack.append(tok)
        else:
            b = stack.pop()
            a = stack.pop()
            if tok == "+":
                stack.append(a + b)
            elif tok == "-":
                stack.append(b - a)
            elif tok == "*":
                stack.append(a * b)
            elif tok == "/":
                stack.append(a // b)
    return stack[-1]
