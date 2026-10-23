import asyncio
import socket
import threading
import time

import pytest

from scpi.filesystem import create_initial_structure
from scpi.state import FileSystemState, InstrumentState
from server import build_dispatcher, handle_client, parse_args


def _free_port():
    with socket.socket() as s:
        s.bind(("", 0))
        return s.getsockname()[1]


async def _run_server(port, fs_root):
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
def server_addr(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("srv")
    port = _free_port()

    def run():
        asyncio.run(_run_server(port, str(tmp)))

    t = threading.Thread(target=run, daemon=True)
    t.start()
    time.sleep(0.3)  # allow server to bind
    return ("127.0.0.1", port)


def send_recv(addr, command: str) -> str:
    with socket.create_connection(addr, timeout=3) as sock:
        sock.sendall((command + "\n").encode())
        resp = b""
        while not resp.endswith(b"\n"):
            chunk = sock.recv(4096)
            if not chunk:
                break
            resp += chunk
        return resp.decode().rstrip("\n")


def test_server_idn_query_with_headers_on_returns_prefixed_identity(server_addr):
    resp = send_recv(server_addr, "*IDN?")
    assert resp == ":*IDN TEKTRONIX,TDS5054B,0,CF:91.1CT FV:v2.00 TDS5054B"


def test_server_cwd_query_returns_default_cwd(server_addr):
    resp = send_recv(server_addr, "FILESystem:CWD?")
    assert ":FILESYSTEM:CWD" in resp
    assert "TekScope" in resp


def test_server_mkdir_then_dir_lists_new_directory(server_addr):
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


def test_server_hdr_off_idn_returns_bare_identity(server_addr):
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


def test_server_writefile_then_readfile_returns_payload(server_addr):
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


def test_server_unknown_command_sends_no_response(server_addr):
    with socket.create_connection(server_addr, timeout=2) as sock:
        sock.sendall(b"ACQUIRE:NUMAVG 4\n")
        sock.settimeout(0.5)
        try:
            data = sock.recv(128)
        except TimeoutError:
            data = b""
    assert data == b""  # no response for unknown command


def test_parse_args_without_host_binds_loopback_only():
    assert parse_args([]).host == "127.0.0.1"


def test_parse_args_host_option_sets_bind_address():
    assert parse_args(["--host", "0.0.0.0"]).host == "0.0.0.0"
