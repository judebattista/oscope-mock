import pytest

from scpi.events import EventCode
from scpi.parser import (
    ParsedCommand,
    ParseError,
    parse_unit,
    resolve_node,
    split_message,
    split_units,
)


def parse(message: str) -> list[ParsedCommand]:
    """Parse one framed message (terminator already removed), as the server does."""
    return [parse_unit(unit) for unit in split_units(message.encode("latin-1"))]


def block(data: bytes) -> bytes:
    length = str(len(data)).encode()
    return b"#" + str(len(length)).encode() + length + data


@pytest.mark.parametrize(
    ("mnemonic", "canonical"),
    [
        ("FILESYSTEM", "FILESYSTEM"),
        ("FILESystem", "FILESYSTEM"),
        ("FILE", "FILESYSTEM"),
        ("file", "FILESYSTEM"),
        ("COPY", "COPY"),
        ("COP", "COPY"),
        ("DELETE", "DELETE"),
        ("DELE", "DELETE"),
        ("MKDIR", "MKDIR"),
        ("MKD", "MKDIR"),
        ("PRINT", "PRINT"),
        ("PRI", "PRINT"),
        ("READFILE", "READFILE"),
        ("READ", "READFILE"),
        ("RENAME", "RENAME"),
        ("REN", "RENAME"),
        ("RMDIR", "RMDIR"),
        ("RMD", "RMDIR"),
        ("WRITEFILE", "WRITEFILE"),
        ("WRITE", "WRITEFILE"),
        ("HEADER", "HEADER"),
        ("HEAD", "HEADER"),
        ("HDR", "HDR"),
        ("CWD", "CWD"),
        ("DIR", "DIR"),
        ("EVMSG", "EVMSG"),
        ("EVM", "EVMSG"),
        ("VERBOSE", "VERBOSE"),
        ("VERB", "VERBOSE"),
    ],
)
def test_resolve_node_long_or_short_form_returns_canonical_key(
    mnemonic: str, canonical: str
) -> None:
    assert resolve_node(mnemonic) == canonical


def test_resolve_node_unknown_mnemonic_returns_uppercased() -> None:
    # Unknown nodes pass through uppercased (for future commands)
    assert resolve_node("ACQUIRE") == "ACQUIRE"


# --- parse_unit / split_units ---


def test_parse_unit_common_query_returns_star_key_and_query_flag() -> None:
    cmds = parse("*IDN?")
    assert cmds == [ParsedCommand(key="*IDN", query=True, args=[])]


def test_parse_unit_common_command_returns_star_key() -> None:
    cmds = parse("*RST")
    assert cmds == [ParsedCommand(key="*RST", query=False, args=[])]


def test_parse_unit_long_form_query_returns_canonical_key() -> None:
    cmds = parse("FILESystem:CWD?")
    assert cmds == [ParsedCommand(key="FILESYSTEM:CWD", query=True, args=[])]


def test_parse_unit_quoted_path_returns_unquoted_arg() -> None:
    cmds = parse(r'FILESYSTEM:CWD "C:\TekScope\Waveforms"')
    assert cmds == [
        ParsedCommand(key="FILESYSTEM:CWD", query=False, args=[r"C:\TekScope\Waveforms"])
    ]


def test_parse_unit_short_form_returns_canonical_key_and_args() -> None:
    cmds = parse(r'FILE:COP "a","b"')
    assert cmds == [ParsedCommand(key="FILESYSTEM:COPY", query=False, args=["a", "b"])]


def test_split_units_semicolon_compound_returns_each_command() -> None:
    cmds = parse("*CLS;FILESystem:CWD?")
    assert cmds == [
        ParsedCommand(key="*CLS", query=False, args=[]),
        ParsedCommand(key="FILESYSTEM:CWD", query=True, args=[]),
    ]


def test_parse_unit_mkdir_path_returns_path_arg() -> None:
    cmds = parse(r'FILESYSTEM:MKDIR "C:\TekScope\NewDir"')
    assert cmds == [
        ParsedCommand(key="FILESYSTEM:MKDIR", query=False, args=[r"C:\TekScope\NewDir"])
    ]


def test_parse_unit_unquoted_arg_returns_token() -> None:
    cmds = parse("HDR ON")
    assert cmds == [ParsedCommand(key="HDR", query=False, args=["ON"])]


def test_parse_unit_mixed_case_query_returns_canonical_key() -> None:
    cmds = parse("HEADer?")
    assert cmds == [ParsedCommand(key="HEADER", query=True, args=[])]


def test_parse_unit_root_node_query_returns_root_key() -> None:
    cmds = parse("FILESystem?")
    assert cmds == [ParsedCommand(key="FILESYSTEM", query=True, args=[])]


def test_parse_unit_trailing_carriage_return_is_ignored() -> None:
    cmds = parse("*IDN?\r")
    assert cmds == [ParsedCommand(key="*IDN", query=True, args=[])]


def test_parse_unit_definite_block_returns_bytes_arg() -> None:
    # #15hello — 1 digit of length, length=5, data="hello"
    cmds = parse('FILESYSTEM:WRITEFILE "path.wfm",#15hello')
    assert cmds == [
        ParsedCommand(key="FILESYSTEM:WRITEFILE", query=False, args=["path.wfm", b"hello"])
    ]


def test_parse_unit_two_digit_block_length_returns_bytes_arg() -> None:
    # #210abcdefghij — 2 digits of length, length=10
    data = "abcdefghij"
    cmds = parse(f'FILESYSTEM:WRITEFILE "f.wfm",#2{len(data)}{data}')
    assert cmds == [
        ParsedCommand(key="FILESYSTEM:WRITEFILE", query=False, args=["f.wfm", data.encode()])
    ]


def test_parse_unit_indefinite_block_returns_rest_as_bytes() -> None:
    # #0hello — indefinite; the framing newline has already been removed
    cmds = parse('FILESYSTEM:WRITEFILE "f.wfm",#0hello')
    assert cmds == [
        ParsedCommand(key="FILESYSTEM:WRITEFILE", query=False, args=["f.wfm", b"hello"])
    ]


def test_parse_unit_space_after_comma_ignores_whitespace() -> None:
    # The manual writes READFile as `"<file>", GPIb` — with a space after the comma.
    cmds = parse('FILESystem:READFile "x", GPIb')
    assert cmds == [ParsedCommand(key="FILESYSTEM:READFILE", query=False, args=["x", "GPIb"])]


def test_parse_unit_definite_block_keeps_trailing_whitespace_and_newlines() -> None:
    payload = b"line1\nline2;semi  \n"
    cmds = [parse_unit(u) for u in split_units(b'FILESYSTEM:WRITEFILE "f",' + block(payload))]
    assert cmds == [ParsedCommand(key="FILESYSTEM:WRITEFILE", query=False, args=["f", payload])]


def test_split_units_semicolon_inside_quotes_is_not_a_separator() -> None:
    assert split_units(b'MKDIR "a;b";*IDN?') == [b'MKDIR "a;b"', b"*IDN?"]


def test_split_units_semicolon_inside_definite_block_is_data() -> None:
    unit = b'WRITE "f",' + block(b"a;b")
    assert split_units(unit + b";*IDN?") == [unit, b"*IDN?"]


def test_split_units_semicolon_inside_indefinite_block_is_data() -> None:
    assert split_units(b'WRITE "f",#0a;b') == [b'WRITE "f",#0a;b']


# --- split_message ---


def test_split_message_without_newline_returns_none() -> None:
    assert split_message(b"*IDN?") is None


def test_split_message_complete_message_returns_message_and_rest() -> None:
    assert split_message(b"*IDN?\n*CLS") == (b"*IDN?", b"*CLS")


def test_split_message_newline_inside_definite_block_is_data() -> None:
    message = b'WRITE "f",' + block(b"a\nb")
    assert split_message(message + b"\n*IDN?\n") == (message, b"*IDN?\n")


def test_split_message_incomplete_definite_block_returns_none() -> None:
    partial = b'WRITE "f",' + block(b"a\nbcdef")[:-3]
    assert split_message(partial + b"\n") is None


def test_split_message_incomplete_block_length_returns_none() -> None:
    assert split_message(b'WRITE "f",#2') is None


def test_split_message_hash_inside_quotes_is_not_a_block() -> None:
    assert split_message(b'MKDIR "run#19"\n*IDN?\n') == (b'MKDIR "run#19"', b"*IDN?\n")


def test_split_message_indefinite_block_ends_at_newline() -> None:
    assert split_message(b'WRITE "f",#0a;"b\nNEXT') == (b'WRITE "f",#0a;"b', b"NEXT")


def test_parse_unit_unterminated_quote_raises_invalid_string_data() -> None:
    with pytest.raises(ParseError) as excinfo:
        parse_unit(b'FILESYSTEM:CWD "C:\\oops')
    assert excinfo.value.code == EventCode.INVALID_STRING_DATA


@pytest.mark.parametrize(
    "unit",
    [
        b'FILESYSTEM:WRITEFILE "f",#x',
        b'FILESYSTEM:WRITEFILE "f",#2ab',
        b'FILESYSTEM:WRITEFILE "f",#15abc',
        b'FILESYSTEM:WRITEFILE "f",#',
        b'FILESYSTEM:WRITEFILE "f",#\xb2ab',
    ],
    ids=[
        "non-digit-header",
        "non-numeric-length",
        "shorter-than-declared",
        "bare-hash",
        "latin-1-superscript-digit",
    ],
)
def test_parse_unit_malformed_block_raises_invalid_block_data(unit: bytes) -> None:
    with pytest.raises(ParseError) as excinfo:
        parse_unit(unit)
    assert excinfo.value.code == EventCode.INVALID_BLOCK_DATA
