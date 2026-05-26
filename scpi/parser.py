from __future__ import annotations
from typing import NamedTuple


class ParsedCommand(NamedTuple):
    key: str
    query: bool
    args: list


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


def _parse_args(args_str: str) -> list:
    """Parse a SCPI argument string into a list of strings and bytes (for block data)."""
    args_str = args_str.strip()
    if not args_str:
        return []

    result = []
    i = 0
    while i < len(args_str):
        if args_str[i] == '"':
            # Quoted string
            j = args_str.index('"', i + 1)
            result.append(args_str[i + 1:j])
            i = j + 1
            # Skip trailing comma
            if i < len(args_str) and args_str[i] == ',':
                i += 1
        elif args_str[i] == '#':
            # IEEE 488.2 block data
            i += 1  # skip '#'
            n = int(args_str[i])  # number of digits in the length field
            i += 1
            if n == 0:
                # Indefinite: rest of string is data
                result.append(args_str[i:].encode('latin-1'))
                break
            else:
                length = int(args_str[i:i + n])
                i += n
                result.append(args_str[i:i + length].encode('latin-1'))
                i += length
        elif args_str[i] == ',':
            i += 1
        else:
            # Unquoted token (e.g. ON, OFF, GPIB, NR1 number)
            j = i
            while j < len(args_str) and args_str[j] not in (',', ' '):
                j += 1
            result.append(args_str[i:j])
            i = j
            if i < len(args_str) and args_str[i] == ',':
                i += 1
    return result


def _parse_single(raw: str) -> ParsedCommand:
    """Parse one SCPI command string into a ParsedCommand."""
    raw = raw.strip()

    # Split header from arguments on first whitespace
    parts = raw.split(None, 1)
    header = parts[0]
    args_str = parts[1] if len(parts) > 1 else ""

    # IEEE 488.2 common commands start with *
    if header.startswith('*'):
        query = header.endswith('?')
        key = header.rstrip('?').upper()
        return ParsedCommand(key=key, query=query, args=_parse_args(args_str))

    # Strip query marker
    query = header.endswith('?')
    header = header.rstrip('?')

    # Resolve each node in the colon-separated path
    nodes = [resolve_node(n) for n in header.split(':')]
    key = ':'.join(nodes)

    return ParsedCommand(key=key, query=query, args=_parse_args(args_str))


def parse_line(raw: str) -> list[ParsedCommand]:
    """Parse a raw SCPI line (possibly compound with ';') into a list of ParsedCommands."""
    raw = raw.rstrip('\r\n')
    return [_parse_single(cmd) for cmd in raw.split(';') if cmd.strip()]
