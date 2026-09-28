class StackMin:
    """Stack that exposes the current minimum."""

    def __init__(self):
        self._data = []
        self._total_min = None

    def push(self, x):
        self._data.append(x)
        if self._total_min is None or x < self._total_min:
            self._total_min = x

    def pop(self):
        self._data.pop()

    def min(self):
        return self._total_min