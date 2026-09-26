def parse_csv(text):
    """Parse a CSV string into a list of rows."""
    rows = []
    row = []
    field = ""
    in_quotes = False
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        if in_quotes:
            if c == '"':
                if i + 1 < n and text[i + 1] == '"':
                    field += '"'
                    i += 2
                    continue
                else:
                    in_quotes = False
                    i += 1
                    continue
            else:
                field += c
                i += 1
        else:
            if c == '"':
                in_quotes = True
                i += 1
            elif c == ",":
                row.append(field)
                field = ""
                i += 1
            elif c == "\n":
                # Always flush on newline, even if row is empty
                # (preserves empty rows like "\n\n" -> [[], []]).
                row.append(field)
                rows.append(row)
                row = []
                field = ""
                i += 1
            else:
                field += c
                i += 1
    # Flush trailing row only if there's content (field non-empty OR
    # we have a partial row in progress). For text ending in newline
    # like "a\n", the loop already flushed "a" -> ['a']. For text like
    # "a" with no trailing newline, we need to flush here.
    if field or row:
        row.append(field)
        rows.append(row)
    return rows
