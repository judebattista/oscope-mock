from __future__ import annotations

from typing import NamedTuple

Arg = str | bytes


class ParsedCommand(NamedTuple):
    key: str
    query: bool
    args: list[Arg]


# (long_form, short_form) pairs — short is the ALL-CAPS prefix per SCPI standard
_MNEMONICS: list[tuple[str, str]] = [
    ("FILESYSTEM", "FILE"),
    ("COPY", "COP"),
    ("CWD", "CWD"),
    ("DELETE", "DELE"),
    ("DIR", "DIR"),
    ("MKDIR", "MKD"),
    ("PRINT", "PRI"),
    ("READFILE", "READ"),
    ("RENAME", "REN"),
    ("RMDIR", "RMD"),
    ("WRITEFILE", "WRITE"),
    ("HEADER", "HEAD"),
    ("HDR", "HDR"),
]

# Build reverse lookup: both short and long forms → canonical (long) key
_RESOLVE: dict[str, str] = {}
for _long, _short in _MNEMONICS:
    _RESOLVE[_long] = _long
    _RESOLVE[_short] = _long


def resolve_node(node: str) -> str:
    """Map a SCPI mnemonic (any case, short or long) to its canonical uppercase key.
    Unknown nodes pass through uppercased."""
    return _RESOLVE.get(node.upper(), node.upper())


def _parse_quoted(args_str: str, start: int) -> tuple[str, int]:
    end = args_str.index('"', start + 1)
    return args_str[start + 1 : end], end + 1


def _parse_block(args_str: str, start: int) -> tuple[bytes, int]:
    """Parse IEEE 488.2 block data beginning at the '#' at `start`."""
    n_digits = int(args_str[start + 1])
    length_start = start + 2
    if n_digits == 0:
        # Indefinite: rest of string is data
        return args_str[length_start:].encode("latin-1"), len(args_str)
    length = int(args_str[length_start : length_start + n_digits])
    data_start = length_start + n_digits
    data_end = data_start + length
    return args_str[data_start:data_end].encode("latin-1"), data_end


def _parse_unquoted(args_str: str, start: int) -> tuple[str, int]:
    """Parse a bare token such as ON, OFF, GPIb, or an NR1 number."""
    end = start
    while end < len(args_str) and args_str[end] != "," and not args_str[end].isspace():
        end += 1
    return args_str[start:end], end


def _parse_args(args_str: str) -> list[Arg]:
    """Parse a SCPI argument string into a list of strings and bytes (for block data)."""
    args_str = args_str.strip()
    result: list[Arg] = []
    i = 0
    while i < len(args_str):
        char = args_str[i]
        value: Arg
        if char == "," or char.isspace():
            i += 1
            continue
        if char == '"':
            value, i = _parse_quoted(args_str, i)
        elif char == "#":
            value, i = _parse_block(args_str, i)
        else:
            value, i = _parse_unquoted(args_str, i)
        result.append(value)
    return result


def _parse_single(raw: str) -> ParsedCommand:
    """Parse one SCPI command string into a ParsedCommand."""
    raw = raw.strip()

    # Split header from arguments on first whitespace
    parts = raw.split(None, 1)
    header = parts[0]
    args_str = parts[1] if len(parts) > 1 else ""

    # IEEE 488.2 common commands start with *
    if header.startswith("*"):
        query = header.endswith("?")
        key = header.rstrip("?").upper()
        return ParsedCommand(key=key, query=query, args=_parse_args(args_str))

    # Strip query marker
    query = header.endswith("?")
    header = header.rstrip("?")

    # Resolve each node in the colon-separated path
    nodes = [resolve_node(n) for n in header.split(":")]
    key = ":".join(nodes)

    return ParsedCommand(key=key, query=query, args=_parse_args(args_str))


def parse_line(raw: str) -> list[ParsedCommand]:
    """Parse a raw SCPI line (possibly compound with ';') into a list of ParsedCommands."""
    raw = raw.rstrip("\r\n")
    return [_parse_single(cmd) for cmd in raw.split(";") if cmd.strip()]
