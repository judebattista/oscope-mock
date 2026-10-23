import argparse
import asyncio
import logging
import tempfile

from scpi.dispatcher import Dispatcher
from scpi.filesystem import create_initial_structure, register_filesystem_commands
from scpi.instrument import register_instrument_commands
from scpi.parser import parse_line
from scpi.state import FileSystemState, InstrumentState

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger(__name__)


def build_dispatcher() -> Dispatcher:
    d = Dispatcher()
    register_instrument_commands(d)
    register_filesystem_commands(d)
    return d


def format_response(key: str, response: str | bytes, headers: bool) -> bytes:
    if isinstance(response, bytes):
        return response  # binary file data: send raw, no header prefix
    if headers:
        formatted = f":{key} {response}\n"
    else:
        formatted = f"{response}\n"
    return formatted.encode()


async def handle_client(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    dispatcher: Dispatcher,
    state: InstrumentState,
) -> None:
    addr = writer.get_extra_info("peername")
    log.info("Connection from %s", addr)
    try:
        while True:
            try:
                line = await reader.readline()
            except asyncio.IncompleteReadError:
                break
            if not line:
                break
            raw = line.decode("latin-1", errors="replace")
            log.info("< %s", raw.rstrip())
            for cmd in parse_line(raw):
                response = dispatcher.dispatch(cmd.key, cmd.query, cmd.args, state)
                if response is not None:
                    data = format_response(cmd.key, response, state.headers)
                    writer.write(data)
                    await writer.drain()
    finally:
        log.info("Disconnected %s", addr)
        writer.close()


async def main(host: str, port: int, fs_root: str) -> None:
    fs = FileSystemState(root=fs_root)
    create_initial_structure(fs)
    state = InstrumentState(filesystem=fs)
    dispatcher = build_dispatcher()

    server = await asyncio.start_server(
        lambda r, w: handle_client(r, w, dispatcher, state),
        host=host,
        port=port,
    )
    log.info("Listening on %s:%d, fs-root: %s", host, port, fs_root)
    async with server:
        await server.serve_forever()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="TDS5000B Mock Oscilloscope")
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Address to listen on; use 0.0.0.0 to accept LAN clients (default: %(default)s)",
    )
    parser.add_argument("--port", type=int, default=4000)
    parser.add_argument("--fs-root", default=None)
    return parser.parse_args(argv)


if __name__ == "__main__":
    args = parse_args()

    fs_root = args.fs_root or tempfile.mkdtemp(prefix="tds5000b_mock_")
    if not args.fs_root:
        print(f"fs-root: {fs_root}")

    asyncio.run(main(args.host, args.port, fs_root))
