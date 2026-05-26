# (long_form, short_form) pairs — short is the ALL-CAPS prefix per SCPI standard
_MNEMONICS: list[tuple[str, str]] = [
    ("FILESYSTEM", "FILE"),
    ("COPY",       "COP"),
    ("CWD",        "CWD"),
    ("DELETE",     "DELE"),
    ("DIR",        "DIR"),
    ("MKDIR",      "MKD"),
    ("PRINT",      "PRI"),
    ("READFILE",   "READ"),
    ("RENAME",     "REN"),
    ("RMDIR",      "RMD"),
    ("WRITEFILE",  "WRITE"),
    ("HEADER",     "HEAD"),
    ("HDR",        "HDR"),
]

# Build reverse lookup: both short and long forms → canonical (long) key
_RESOLVE: dict[str, str] = {}
for _long, _short in _MNEMONICS:
    _RESOLVE[_long]  = _long
    _RESOLVE[_short] = _long


def resolve_node(node: str) -> str:
    """Map a SCPI mnemonic (any case, short or long) to its canonical uppercase key.
    Unknown nodes pass through uppercased."""
    return _RESOLVE.get(node.upper(), node.upper())
