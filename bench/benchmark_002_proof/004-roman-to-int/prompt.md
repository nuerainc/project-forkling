Fix the `roman_to_int(s)` function in `buggy.py`. It should convert
a Roman numeral string (uppercase, standard subtractive notation) to
an integer.

Symbols: I=1, V=5, X=10, L=50, C=100, D=500, M=1000. When a symbol is
immediately followed by a larger one, it is subtracted instead of
added (IV=4, IX=9, XL=40, XC=90, CD=400, CM=900).

Examples:
- roman_to_int("III") -> 3
- roman_to_int("XLII") -> 42
- roman_to_int("MCMXCIV") -> 1994

Do not change the signature. Standard library only.
