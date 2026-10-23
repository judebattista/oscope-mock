import asyncio
import socket
import threading
import time

import pytest

from scpi.filesystem import create_initial_structure
from scpi.state import FileSystemState, InstrumentState
from server import build_dispatcher, handle_client, parse_args

Address = tuple[str, int]


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("", 0))
        port: int = s.getsockname()[1]
        return port


async def _run_server(port: int, fs_root: str) -> None:
    fs = FileSystemState(root=fs_root)
    create_initial_structure(fs)
    state = InstrumentState(filesystem=fs)
    d = build_dispatcher()

    server = await asyncio.start_server(
        lambda r, w: handle_client(r, w, d, state),
        host="127.0.0.1",
        port=port,
    )
    async with server:
        await server.serve_forever()


@pytest.fixture(scope="module")
def server_addr(tmp_path_factory: pytest.TempPathFactory) -> Address:
    tmp = tmp_path_factory.mktemp("srv")
    port = _free_port()

    def run() -> None:
        asyncio.run(_run_server(port, str(tmp)))

    t = threading.Thread(target=run, daemon=True)
    t.start()
    time.sleep(0.3)  # allow server to bind
    return ("127.0.0.1", port)


def send_recv(addr: Address, command: str) -> str:
    with socket.create_connection(addr, timeout=3) as sock:
        sock.sendall((command + "\n").encode())
        resp = b""
        while not resp.endswith(b"\n"):
            chunk = sock.recv(4096)
            if not chunk:
                break
            resp += chunk
        return resp.decode().rstrip("\n")


def read_until_idle(sock: socket.socket, idle: float = 0.3) -> bytes:
    """Collect bytes until the server goes quiet, for responses with no terminator."""
    sock.settimeout(idle)
    data = b""
    try:
        while chunk := sock.recv(65536):
            data += chunk
    except TimeoutError:
        pass
    return data


def ieee_block(data: bytes) -> bytes:
    length = str(len(data)).encode()
    return b"#" + str(len(length)).encode() + length + data


def test_server_idn_query_with_headers_on_returns_prefixed_identity(server_addr: Address) -> None:
    resp = send_recv(server_addr, "*IDN?")
    assert resp == ":*IDN TEKTRONIX,TDS5054B,0,CF:91.1CT FV:v2.00 TDS5054B"


def test_server_cwd_query_returns_default_cwd(server_addr: Address) -> None:
    resp = send_recv(server_addr, "FILESystem:CWD?")
    assert ":FILESYSTEM:CWD" in resp
    assert "TekScope" in resp


def test_server_mkdir_then_dir_lists_new_directory(server_addr: Address) -> None:
    with socket.create_connection(server_addr, timeout=3) as sock:
        sock.sendall(b'FILESYSTEM:MKDIR "C:\\TekScope\\IntTest"\n')
        sock.sendall(b'FILESYSTEM:CWD "C:\\TekScope"\n')
        sock.sendall(b"FILESYSTEM:DIR?\n")
        resp = b""
        while not resp.endswith(b"\n"):
            chunk = sock.recv(4096)
            if not chunk:
                break
            resp += chunk
    assert b"IntTest" in resp


def test_server_hdr_off_idn_returns_bare_identity(server_addr: Address) -> None:
    # Use a fresh connection to avoid state pollution from other tests
    with socket.create_connection(server_addr, timeout=3) as sock:
        sock.sendall(b"HDR OFF\n")
        sock.sendall(b"*IDN?\n")
        resp = b""
        while not resp.endswith(b"\n"):
            chunk = sock.recv(4096)
            if not chunk:
                break
            resp += chunk
        sock.sendall(b"HDR ON\n")
    assert resp.decode().strip() == "TEKTRONIX,TDS5054B,0,CF:91.1CT FV:v2.00 TDS5054B"


def test_server_writefile_then_readfile_returns_payload(server_addr: Address) -> None:
    payload = b"WAVEFORM_DATA"
    # IEEE 488.2 definite-length block: #<n><len><data>
    # len(payload) == 13 → two digits → use #2
    n_digits = len(str(len(payload)))
    write_cmd = (
        f'FILESYSTEM:WRITEFILE "C:\\TekScope\\inttest.wfm",'
        f"#{n_digits}{len(payload)}{payload.decode()}"
    )
    with socket.create_connection(server_addr, timeout=3) as sock:
        sock.sendall((write_cmd + "\n").encode())
        time.sleep(0.1)
        sock.sendall(b'FILESYSTEM:READFILE "C:\\TekScope\\inttest.wfm",GPIb\n')
        resp = b""
        sock.settimeout(1.0)
        try:
            for _ in range(50):
                chunk = sock.recv(4096)
                if not chunk:
                    break
                resp += chunk
                if payload in resp:
                    break
        except TimeoutError:
            pass
    assert payload in resp


def test_server_unknown_command_sends_no_response(server_addr: Address) -> None:
    with socket.create_connection(server_addr, timeout=2) as sock:
        sock.sendall(b"ACQUIRE:NUMAVG 4\n")
        sock.settimeout(0.5)
        try:
            data = sock.recv(128)
        except TimeoutError:
            data = b""
    assert data == b""  # no response for unknown command


def test_parse_args_without_host_binds_loopback_only() -> None:
    assert parse_args([]).host == "127.0.0.1"


def test_parse_args_host_option_sets_bind_address() -> None:
    assert parse_args(["--host", "0.0.0.0"]).host == "0.0.0.0"


def test_server_writefile_block_with_newline_semicolon_and_spaces_roundtrips(
    server_addr: Address,
) -> None:
    payload = b"line1\nline2;semi  \n"
    with socket.create_connection(server_addr, timeout=3) as sock:
        sock.sendall(b'FILESYSTEM:WRITEFILE "C:\\TekScope\\nl.txt",' + ieee_block(payload) + b"\n")
        sock.sendall(b'FILESYSTEM:READFILE "C:\\TekScope\\nl.txt",GPIb\n')
        assert read_until_idle(sock) == payload


def test_server_block_split_across_packets_is_reassembled(server_addr: Address) -> None:
    payload = bytes(range(256)) * 4
    message = b'FILESYSTEM:WRITEFILE "C:\\TekScope\\split.bin",' + ieee_block(payload) + b"\n"
    with socket.create_connection(server_addr, timeout=3) as sock:
        sock.sendall(message[:300])
        time.sleep(0.1)
        sock.sendall(message[300:])
        sock.sendall(b'FILESYSTEM:READFILE "C:\\TekScope\\split.bin",GPIb\n')
        assert read_until_idle(sock) == payload


def test_server_semicolon_inside_quoted_path_is_not_a_separator(server_addr: Address) -> None:
    with socket.create_connection(server_addr, timeout=3) as sock:
        sock.sendall(b'HEADer 0;FILESYSTEM:MKDIR "C:\\TekScope\\a;b"\n')
        sock.sendall(b'FILESYSTEM:CWD "C:\\TekScope\\a;b";FILESYSTEM:CWD?\n')
        assert read_until_idle(sock) == b'"C:\\TekScope\\a;b"\n'


def test_server_hash_inside_quoted_path_does_not_swallow_next_command(server_addr: Address) -> None:
    with socket.create_connection(server_addr, timeout=3) as sock:
        sock.sendall(b'HEADer 0;FILESYSTEM:MKDIR "C:\\TekScope\\run#19"\n*OPC?\n')
        assert read_until_idle(sock) == b"1\n"


def test_server_unterminated_quote_reports_error_and_keeps_connection(server_addr: Address) -> None:
    with socket.create_connection(server_addr, timeout=3) as sock:
        sock.sendall(b'*CLS\nFILESystem:CWD "C:\\oops\nHEADer 0;*ESR?;EVMsg?\n')
        assert read_until_idle(sock) == b'32\n151,"Invalid string data"\n'


def test_server_parse_error_discards_rest_of_message(server_addr: Address) -> None:
    with socket.create_connection(server_addr, timeout=3) as sock:
        sock.sendall(b'HEADer 0\nFILESYSTEM:WRITEFILE "f",#x;*OPC?\n*IDN?\n')
        assert read_until_idle(sock) == b"TEKTRONIX,TDS5054B,0,CF:91.1CT FV:v2.00 TDS5054B\n"
