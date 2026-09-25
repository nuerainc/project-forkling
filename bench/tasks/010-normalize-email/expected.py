def normalize_email(email):
    """Lowercase, strip whitespace. Raise ValueError if @ is missing."""
    if "@" not in email:
        raise ValueError("no @")
    return email.lower().strip()
