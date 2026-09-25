Fix the `normalize_email(email)` function in `buggy.py`. It should
lowercase the email and strip surrounding whitespace. If the email
does NOT contain '@', it should raise ValueError("no @").

Examples:
- normalize_email("  Foo@Bar.COM  ") -> "foo@bar.com"
- normalize_email("user@example.com") -> "user@example.com"
- normalize_email("not-an-email") -> raises ValueError

You may modify the function body. Do not change the signature.
