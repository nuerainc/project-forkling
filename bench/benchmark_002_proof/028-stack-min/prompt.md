Fix the `StackMin` class in `buggy.py`. It implements a stack that can
report the minimum value currently in it.

- `push(x)`: push `x` onto the stack.
- `pop()`: remove and discard the top element of the stack. The stack
  is guaranteed to be non-empty when this is called.
- `min()`: return the minimum value currently in the stack.

Examples (using a fresh instance for each line):
    s = StackMin()
    s.push(5); s.push(3); s.min()      -> 3
    s.pop(); s.min()                   -> 5
    s.push(1); s.min()                 -> 1

Do not change the method signatures.