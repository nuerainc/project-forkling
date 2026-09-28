class StackMin:
    """Stack that exposes the current minimum."""

    def __init__(self):
        self._data = []
        self._mins = []

    def push(self, x):
        self._data.append(x)
        if not self._mins or x <= self._mins[-1]:
            self._mins.append(x)

    def pop(self):
        x = self._data.pop()
        if self._mins and self._mins[-1] == x:
            self._mins.pop()

    def min(self):
        return self._mins[-1]