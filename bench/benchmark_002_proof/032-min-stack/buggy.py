class MinStack:
    """Stack with O(1) min queries."""

    def __init__(self):
        self._data = []
        self._mins = []

    def push(self, x):
        self._data.append(x)
        if not self._mins or x <= self._mins[-1]:
            self._mins.append(x)

    def pop(self):
        self._data.pop()

    def getMin(self):
        return self._mins[-1]