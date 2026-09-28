def calc(s):
    """Evaluate basic arithmetic with +,-,*,/, parens. Integer math."""
    tokens = []
    i = 0
    while i < len(s):
        c = s[i]
        if c.isspace():
            i += 1
        elif c.isdigit():
            j = i
            while j < len(s) and s[j].isdigit():
                j += 1
            tokens.append(('num', int(s[i:j])))
            i = j
        elif c in '+-*/()':
            tokens.append(('op', c))
            i += 1
        else:
            raise ValueError("bad char: " + c)

    p = [0]
    END = ('end', '')

    def peek():
        if p[0] < len(tokens):
            return tokens[p[0]]
        return END

    def parse_atom():
        t = peek()
        if t is END:
            raise ValueError("expected number, got end")
        if t[0] == 'op' and t[1] == '(':
            p[0] += 1
            v = parse_expr()
            if peek() is not END and peek()[0] == 'op' and peek()[1] == ')':
                p[0] += 1
            return v
        if t[0] != 'num':
            raise ValueError("expected number")
        p[0] += 1
        return t[1]

    def parse_term():
        v = parse_atom()
        while True:
            t = peek()
            if t is END or t[0] != 'op' or t[1] not in '*/':
                break
            op = t[1]
            p[0] += 1
            r = parse_atom()
            v = v * r if op == '*' else int(v / r) if r != 0 else 0
        return v

    def parse_expr():
        v = parse_term()
        while True:
            t = peek()
            if t is END or t[0] != 'op' or t[1] not in '+-':
                break
            op = t[1]
            p[0] += 1
            r = parse_term()
            v = v + r if op == '+' else v - r
        return v

    return parse_expr()
