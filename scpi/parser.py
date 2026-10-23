from __future__ import annotations

from itertools import pairwise
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
    ("EVMSG", "EVM"),
    ("MKDIR", "MKD"),
    ("PRINT", "PRI"),
    ("READFILE", "READ"),
    ("RENAME", "REN"),
    ("RMDIR", "RMD"),
    ("WRITEFILE", "WRITE"),
    ("HEADER", "HEAD"),
    ("HDR", "HDR"),
    ("VERBOSE", "VERB"),
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


def parse_unit(unit: bytes) -> ParsedCommand:
    """Parse one message unit (a single ';'-separated command) into a ParsedCommand."""
    # latin-1 maps every byte to one character, so block data survives the round trip.
    text = unit.decode("latin-1").lstrip()

    # Split header from arguments on first whitespace; the arguments keep their trailing
    # bytes because they may end in block data.
    parts = text.split(None, 1)
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


_NEWLINE, _QUOTE, _SEMICOLON, _HASH = b"\n"[0], b'"'[0], b";"[0], b"#"[0]


def _quoted_end(data: bytes, start: int) -> int:
    """Index just past the string opened at `start`; an unterminated string stops at newline."""
    close = data.find(b'"', start + 1)
    newline = data.find(b"\n", start + 1)
    if close != -1 and (newline == -1 or close < newline):
        return close + 1
    return len(data) if newline == -1 else newline


def _block_end(data: bytes, start: int) -> int | None:
    """Index just past the block whose '#' is at `start`, or None if more bytes are needed.

    Definite-length blocks may hold any byte, so they are skipped by their declared length. An
    indefinite (#0) block runs to the next newline. A malformed header is skipped over here and
    left for parse_unit to reject.
    """
    if start + 1 >= len(data):
        return None
    n_digits = data[start + 1] - ord("0")
    if n_digits == 0:
        newline = data.find(b"\n", start)
        return len(data) if newline == -1 else newline
    if not 1 <= n_digits <= 9:
        return start + 1
    length_end = start + 2 + n_digits
    if length_end > len(data):
        return None
    length = data[start + 2 : length_end]
    if not length.isdigit():
        return start + 1
    data_end = length_end + int(length)
    return data_end if data_end <= len(data) else None


def _scan(data: bytes) -> tuple[list[int], int | None]:
    """Locate top-level ';' separators and the newline that ends the first message in `data`.

    Quoted strings and blocks hide ';' and '#'; only block data can hide a newline. The
    terminator is None while the message is still incomplete.
    """
    separators: list[int] = []
    i = 0
    while i < len(data):
        byte = data[i]
        if byte == _NEWLINE:
            return separators, i
        if byte == _QUOTE:
            i = _quoted_end(data, i)
            continue
        if byte == _HASH:
            end = _block_end(data, i)
            if end is None:
                return separators, None
            i = end
            continue
        if byte == _SEMICOLON:
            separators.append(i)
        i += 1
    return separators, None


def split_message(buffer: bytes) -> tuple[bytes, bytes] | None:
    """Split off the first complete program message, or return None if more bytes are needed.

    Returns the message without its newline terminator, and the unconsumed remainder.
    """
    _, end = _scan(buffer)
    if end is None:
        return None
    return buffer[:end], buffer[end + 1 :]


def split_units(message: bytes) -> list[bytes]:
    """Split a framed message into its ';'-separated message units, dropping empty ones."""
    separators, _ = _scan(message)
    bounds = [-1, *separators, len(message)]
    units = [message[start + 1 : end] for start, end in pairwise(bounds)]
    return [unit for unit in units if unit.strip()]
