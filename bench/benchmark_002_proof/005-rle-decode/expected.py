def rle_decode(s):
    """Decode a run-length encoded string like "3a2b" -> "aaabb"."""
    out = []
    count = ""
    for c in s:
        if c.isdigit():
            count += c
        else:
            out.append(c * (int(count) if count else 1))
            count = ""
    return "".join(out)
