def compress_string(s):
    """Compress a string using run-length encoding.

    Consecutive identical characters are replaced with the
    character followed by its count. Single-character runs
    are emitted without a count suffix.
    """
    if not s:
        return ""
    result = []
    prev = s[0]
    count = 1
    for c in s[1:]:
        if c == prev:
            count += 1
        else:
            result.append(prev + (str(count) if count > 1 else ""))
            prev = c
            count = 1
    return "".join(result)
