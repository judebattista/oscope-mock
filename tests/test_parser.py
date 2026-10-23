import pytest

from scpi.parser import ParsedCommand, parse_line, resolve_node


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
def test_resolve_node_long_or_short_form_returns_canonical_key(mnemonic, canonical):
    assert resolve_node(mnemonic) == canonical


def test_resolve_node_unknown_mnemonic_returns_uppercased():
    # Unknown nodes pass through uppercased (for future commands)
    assert resolve_node("ACQUIRE") == "ACQUIRE"


# --- parse_line tests ---


def test_parse_line_common_query_returns_star_key_and_query_flag():
    cmds = parse_line("*IDN?")
    assert cmds == [ParsedCommand(key="*IDN", query=True, args=[])]


def test_parse_line_common_command_returns_star_key():
    cmds = parse_line("*RST")
    assert cmds == [ParsedCommand(key="*RST", query=False, args=[])]


def test_parse_line_long_form_query_returns_canonical_key():
    cmds = parse_line("FILESystem:CWD?")
    assert cmds == [ParsedCommand(key="FILESYSTEM:CWD", query=True, args=[])]


def test_parse_line_quoted_path_returns_unquoted_arg():
    cmds = parse_line(r'FILESYSTEM:CWD "C:\TekScope\Waveforms"')
    assert cmds == [
        ParsedCommand(key="FILESYSTEM:CWD", query=False, args=[r"C:\TekScope\Waveforms"])
    ]


def test_parse_line_short_form_returns_canonical_key_and_args():
    cmds = parse_line(r'FILE:COP "a","b"')
    assert cmds == [ParsedCommand(key="FILESYSTEM:COPY", query=False, args=["a", "b"])]


def test_parse_line_semicolon_compound_returns_each_command():
    cmds = parse_line("*CLS;FILESystem:CWD?")
    assert cmds == [
        ParsedCommand(key="*CLS", query=False, args=[]),
        ParsedCommand(key="FILESYSTEM:CWD", query=True, args=[]),
    ]


def test_parse_line_mkdir_path_returns_path_arg():
    cmds = parse_line(r'FILESYSTEM:MKDIR "C:\TekScope\NewDir"')
    assert cmds == [
        ParsedCommand(key="FILESYSTEM:MKDIR", query=False, args=[r"C:\TekScope\NewDir"])
    ]


def test_parse_line_unquoted_arg_returns_token():
    cmds = parse_line("HDR ON")
    assert cmds == [ParsedCommand(key="HDR", query=False, args=["ON"])]


def test_parse_line_mixed_case_query_returns_canonical_key():
    cmds = parse_line("HEADer?")
    assert cmds == [ParsedCommand(key="HEADER", query=True, args=[])]


def test_parse_line_root_node_query_returns_root_key():
    cmds = parse_line("FILESystem?")
    assert cmds == [ParsedCommand(key="FILESYSTEM", query=True, args=[])]


def test_parse_line_crlf_terminator_is_stripped():
    cmds = parse_line("*IDN?\r\n")
    assert cmds == [ParsedCommand(key="*IDN", query=True, args=[])]


def test_parse_line_definite_block_returns_bytes_arg():
    # #15hello — 1 digit of length, length=5, data="hello"
    cmds = parse_line('FILESYSTEM:WRITEFILE "path.wfm",#15hello')
    assert cmds == [
        ParsedCommand(key="FILESYSTEM:WRITEFILE", query=False, args=["path.wfm", b"hello"])
    ]


def test_parse_line_two_digit_block_length_returns_bytes_arg():
    # #210abcdefghij — 2 digits of length, length=10
    data = "abcdefghij"
    cmds = parse_line(f'FILESYSTEM:WRITEFILE "f.wfm",#2{len(data)}{data}')
    assert cmds == [
        ParsedCommand(key="FILESYSTEM:WRITEFILE", query=False, args=["f.wfm", data.encode()])
    ]


def test_parse_line_indefinite_block_returns_rest_as_bytes():
    # #0hello — indefinite, terminated by \n (stripped before parse_line is called)
    cmds = parse_line('FILESYSTEM:WRITEFILE "f.wfm",#0hello')
    assert cmds == [
        ParsedCommand(key="FILESYSTEM:WRITEFILE", query=False, args=["f.wfm", b"hello"])
    ]


def test_parse_line_space_after_comma_ignores_whitespace():
    # The manual writes READFile as `"<file>", GPIb` — with a space after the comma.
    cmds = parse_line('FILESystem:READFile "x", GPIb')
    assert cmds == [ParsedCommand(key="FILESYSTEM:READFILE", query=False, args=["x", "GPIb"])]
