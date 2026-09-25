def mean(values):
    """Return the arithmetic mean of values, or 0.0 if empty."""
    if not values:
        return 0.0
    return sum(values) / len(values)
