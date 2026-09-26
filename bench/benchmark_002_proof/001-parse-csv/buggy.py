def parse_csv(text):
    """Parse a CSV string into a list of rows.

    Each row is a list of string fields. Fields may be quoted with
    double quotes. A quoted field may contain commas. A double
    quote inside a quoted field is escaped as two double quotes.

    Empty input returns an empty list.
    """
    rows = []
    row = []
    field = ""
    in_quotes = False
    i = 0
    while i < len(text):
        c = text[i]
        if in_quotes:
            if c == '"':
                # Look ahead for escaped quote ("")
                if i + 1 < len(text) and text[i + 1] == '"':
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
                row.append(field)
                rows.append(row)
                row = []
                field = ""
                i += 1
            else:
                field += c
                i += 1
    return rows
