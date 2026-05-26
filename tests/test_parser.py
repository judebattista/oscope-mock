import pytest
from scpi.parser import resolve_node


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
