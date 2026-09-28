Fix the `MinStack` class in `buggy.py`. It implements a stack that can
report the minimum value currently in it, in O(1) time per operation.

- `push(x)`: push `x` onto the stack.
- `pop()`: remove and discard the top element. The stack is
  guaranteed to be non-empty when this is called.
- `getMin()`: return the minimum value currently in the stack.

Examples (fresh instance for each line):
    s = MinStack()
    s.push(5); s.push(3); s.getMin() -> 3
    s.push(1); s.getMin()             -> 1
    s.pop(); s.getMin()               -> 3
    s.pop(); s.getMin()               -> 5

Do not change the method signatures.