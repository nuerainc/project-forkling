UNITS = {"h": 3600, "m": 60, "s": 1}


def parse_duration(text):
    """Convert "1h30m15s"-style durations to seconds."""
    total = 0
    number = ""
    for c in text:
        if c.isdigit():
            number += c
        elif c in UNITS and number:
            total += int(number) * UNITS[c]
        else:
            raise ValueError(f"bad duration: {text!r}")
    if number:
        raise ValueError(f"missing unit in {text!r}")
    return total
