import pytest
from scpi.parser import resolve_node, parse_line, ParsedCommand


def test_resolve_long_form():
    assert resolve_node("FILESYSTEM") == "FILESYSTEM"


def test_resolve_long_form_mixed_case():
    assert resolve_node("FILESystem") == "FILESYSTEM"


def test_resolve_short_form():
    assert resolve_node("FILE") == "FILESYSTEM"


def test_resolve_short_form_lower():
    assert resolve_node("file") == "FILESYSTEM"


def test_resolve_copy_long():
    assert resolve_node("COPY") == "COPY"


def test_resolve_copy_short():
    assert resolve_node("COP") == "COPY"


def test_resolve_delete_long():
    assert resolve_node("DELETE") == "DELETE"


def test_resolve_delete_short():
    assert resolve_node("DELE") == "DELETE"


def test_resolve_mkdir_long():
    assert resolve_node("MKDIR") == "MKDIR"


def test_resolve_mkdir_short():
    assert resolve_node("MKD") == "MKDIR"


def test_resolve_print_long():
    assert resolve_node("PRINT") == "PRINT"


def test_resolve_print_short():
    assert resolve_node("PRI") == "PRINT"


def test_resolve_readfile_long():
    assert resolve_node("READFILE") == "READFILE"


def test_resolve_readfile_short():
    assert resolve_node("READ") == "READFILE"


def test_resolve_rename_long():
    assert resolve_node("RENAME") == "RENAME"


def test_resolve_rename_short():
    assert resolve_node("REN") == "RENAME"


def test_resolve_rmdir_long():
    assert resolve_node("RMDIR") == "RMDIR"


def test_resolve_rmdir_short():
    assert resolve_node("RMD") == "RMDIR"


def test_resolve_writefile_long():
    assert resolve_node("WRITEFILE") == "WRITEFILE"


def test_resolve_writefile_short():
    assert resolve_node("WRITE") == "WRITEFILE"


def test_resolve_header_long():
    assert resolve_node("HEADER") == "HEADER"


def test_resolve_header_short():
    assert resolve_node("HEAD") == "HEADER"


def test_resolve_hdr():
    assert resolve_node("HDR") == "HDR"


def test_resolve_cwd():
    assert resolve_node("CWD") == "CWD"


def test_resolve_dir():
    assert resolve_node("DIR") == "DIR"


def test_resolve_unknown_passthrough():
    # Unknown nodes pass through uppercased (for future commands)
    assert resolve_node("ACQUIRE") == "ACQUIRE"


# --- parse_line tests ---

def test_parse_idn_query():
    cmds = parse_line("*IDN?")
    assert cmds == [ParsedCommand(key="*IDN", query=True, args=[])]


def test_parse_rst():
    cmds = parse_line("*RST")
    assert cmds == [ParsedCommand(key="*RST", query=False, args=[])]


def test_parse_cwd_query():
    cmds = parse_line("FILESystem:CWD?")
    assert cmds == [ParsedCommand(key="FILESYSTEM:CWD", query=True, args=[])]


def test_parse_cwd_set():
    cmds = parse_line(r'FILESYSTEM:CWD "C:\TekScope\Waveforms"')
    assert cmds == [ParsedCommand(key="FILESYSTEM:CWD", query=False, args=[r"C:\TekScope\Waveforms"])]


def test_parse_short_form():
    cmds = parse_line(r'FILE:COP "a","b"')
    assert cmds == [ParsedCommand(key="FILESYSTEM:COPY", query=False, args=["a", "b"])]


def test_parse_compound_commands():
    cmds = parse_line("*CLS;FILESystem:CWD?")
    assert cmds == [
        ParsedCommand(key="*CLS", query=False, args=[]),
        ParsedCommand(key="FILESYSTEM:CWD", query=True, args=[]),
    ]


def test_parse_mkdir():
    cmds = parse_line(r'FILESYSTEM:MKDIR "C:\TekScope\NewDir"')
    assert cmds == [ParsedCommand(key="FILESYSTEM:MKDIR", query=False, args=[r"C:\TekScope\NewDir"])]


def test_parse_hdr_on():
    cmds = parse_line("HDR ON")
    assert cmds == [ParsedCommand(key="HDR", query=False, args=["ON"])]


def test_parse_header_query():
    cmds = parse_line("HEADer?")
    assert cmds == [ParsedCommand(key="HEADER", query=True, args=[])]


def test_parse_filesystem_query():
    cmds = parse_line("FILESystem?")
    assert cmds == [ParsedCommand(key="FILESYSTEM", query=True, args=[])]


def test_parse_strips_crlf():
    cmds = parse_line("*IDN?\r\n")
    assert cmds == [ParsedCommand(key="*IDN", query=True, args=[])]


def test_parse_writefile_definite_block():
    # #15hello — 1 digit of length, length=5, data="hello"
    cmds = parse_line('FILESYSTEM:WRITEFILE "path.wfm",#15hello')
    assert cmds == [ParsedCommand(key="FILESYSTEM:WRITEFILE", query=False, args=["path.wfm", b"hello"])]


def test_parse_writefile_two_digit_block():
    # #210ab — 2 digits of length, length=10, not enough data (edge case)
    data = "abcdefghij"
    cmds = parse_line(f'FILESYSTEM:WRITEFILE "f.wfm",#2{len(data)}{data}')
    assert cmds == [ParsedCommand(key="FILESYSTEM:WRITEFILE", query=False, args=["f.wfm", data.encode()])]


def test_parse_writefile_indefinite_block():
    # #0hello — indefinite, terminated by \n (stripped before parse_line is called)
    cmds = parse_line('FILESYSTEM:WRITEFILE "f.wfm",#0hello')
    assert cmds == [ParsedCommand(key="FILESYSTEM:WRITEFILE", query=False, args=["f.wfm", b"hello"])]
