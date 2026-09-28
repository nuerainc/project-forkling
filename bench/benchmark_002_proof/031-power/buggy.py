def power(base, exp):
    """Return base raised to a non-negative integer exp."""
    result = 1
    for _ in range(exp - 1):
        result *= base
    return result