VALUES = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}


def roman_to_int(s):
    """Convert a Roman numeral to an integer."""
    total = 0
    i = 0
    while i < len(s):
        value = VALUES[s[i]]
        if s[i] == "I" and i + 1 < len(s) and s[i + 1] in "VX":
            total += VALUES[s[i + 1]] - value
            i += 2
        else:
            total += value
            i += 1
    return total
