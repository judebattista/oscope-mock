from __future__ import annotations

import os
import shutil
from collections.abc import Iterator
from contextlib import contextmanager

from scpi.dispatcher import Dispatcher, Response
from scpi.events import EventCode
from scpi.parser import Arg
from scpi.state import FileSystemState, InstrumentState


def _normalize(components: list[str]) -> list[str]:
    parts: list[str] = []
    for component in components:
        if component in ("", "."):
            continue
        if component == "..":
            if parts:
                parts.pop()
            continue
        parts.append(component)
    return parts


def _resolve(vpath: str, cwd: str) -> tuple[str, list[str]]:
    """Resolve a Windows path against `cwd` into its drive letter and normalized components.

    As on Windows, `..` never climbs above the drive root, which also keeps every path
    inside the mock's fs-root.
    """
    path = vpath.replace("/", "\\")
    cwd_drive, cwd_rest = cwd[0].upper(), cwd[2:]
    if len(path) >= 2 and path[1] == ":":
        drive, components = path[0].upper(), path[2:].split("\\")
    elif path.startswith("\\"):
        drive, components = cwd_drive, path.split("\\")
    else:
        drive, components = cwd_drive, cwd_rest.split("\\") + path.split("\\")
    return drive, _normalize(components)


def _absolute_virtual(vpath: str, cwd: str) -> str:
    drive, parts = _resolve(vpath, cwd)
    return f"{drive}:\\" + "\\".join(parts)


def virtual_to_real(vpath: str, fs: FileSystemState) -> str:
    """Map a Windows virtual path to a real host path under fs.root."""
    drive, parts = _resolve(vpath, fs.cwd)
    return os.path.join(fs.root, drive, *parts)


def create_initial_structure(fs: FileSystemState) -> None:
    """Create the startup virtual directory tree on the real host filesystem."""
    for vpath in [
        r"C:\TekScope",
        r"C:\TekScope\Waveforms",
        r"C:\TekScope\Images",
        r"C:\TekScope\Settings",
    ]:
        os.makedirs(virtual_to_real(vpath, fs), exist_ok=True)


def _str_args(args: list[Arg], count: int, state: InstrumentState) -> list[str] | None:
    """Return the first `count` args as strings; push an error if any is missing or block data."""
    if len(args) < count:
        state.push_error(EventCode.MISSING_PARAMETER)
        return None
    strings = [arg for arg in args[:count] if isinstance(arg, str)]
    if len(strings) < count:
        state.push_error(EventCode.DATA_TYPE_ERROR)
        return None
    return strings


# Most specific first: each entry must precede any of its base classes.
_OS_ERROR_EVENTS: list[tuple[type[OSError], EventCode]] = [
    (FileNotFoundError, EventCode.FILE_NAME_NOT_FOUND),
    (NotADirectoryError, EventCode.FILE_NAME_NOT_FOUND),
    (IsADirectoryError, EventCode.FILE_NAME_ERROR),
    (FileExistsError, EventCode.FILE_NAME_ERROR),
]


def _event_for(exc: OSError) -> EventCode:
    for exc_type, code in _OS_ERROR_EVENTS:
        if isinstance(exc, exc_type):
            return code
    return EventCode.MASS_STORAGE_ERROR


@contextmanager
def _os_errors_as_events(state: InstrumentState) -> Iterator[None]:
    """Report host filesystem failures through the event queue, as the instrument does."""
    try:
        yield
    except OSError as exc:
        state.push_error(_event_for(exc))


def _dir_query(query: bool, args: list[Arg], state: InstrumentState) -> Response:
    real = virtual_to_real(state.filesystem.cwd, state.filesystem)
    entries = [".", ".."] + sorted(os.listdir(real))
    return ",".join(f'"{e}"' for e in entries)


def _cwd_handler(query: bool, args: list[Arg], state: InstrumentState) -> Response:
    if query:
        return f'"{state.filesystem.cwd}"'
    paths = _str_args(args, 1, state)
    if paths is None:
        return None
    if not os.path.isdir(virtual_to_real(paths[0], state.filesystem)):
        state.push_error(EventCode.FILE_NAME_NOT_FOUND)
        return None
    state.filesystem.cwd = _absolute_virtual(paths[0], state.filesystem.cwd)
    return None


def _mkdir_handler(query: bool, args: list[Arg], state: InstrumentState) -> Response:
    paths = _str_args(args, 1, state)
    if paths is None:
        return None
    with _os_errors_as_events(state):
        os.mkdir(virtual_to_real(paths[0], state.filesystem))
    return None


def _rmdir_handler(query: bool, args: list[Arg], state: InstrumentState) -> Response:
    paths = _str_args(args, 1, state)
    if paths is None:
        return None
    with _os_errors_as_events(state):
        os.rmdir(virtual_to_real(paths[0], state.filesystem))
    return None


def _delete_handler(query: bool, args: list[Arg], state: InstrumentState) -> Response:
    paths = _str_args(args, 1, state)
    if paths is None:
        return None
    with _os_errors_as_events(state):
        os.remove(virtual_to_real(paths[0], state.filesystem))
    return None


def _rename_handler(query: bool, args: list[Arg], state: InstrumentState) -> Response:
    paths = _str_args(args, 2, state)
    if paths is None:
        return None
    src = virtual_to_real(paths[0], state.filesystem)
    dst = virtual_to_real(paths[1], state.filesystem)
    with _os_errors_as_events(state):
        os.rename(src, dst)
    return None


def _copy_handler(query: bool, args: list[Arg], state: InstrumentState) -> Response:
    paths = _str_args(args, 2, state)
    if paths is None:
        return None
    src = virtual_to_real(paths[0], state.filesystem)
    dst = virtual_to_real(paths[1], state.filesystem)
    with _os_errors_as_events(state):
        shutil.copy2(src, dst)
    return None


def _read_file_handler(query: bool, args: list[Arg], state: InstrumentState) -> Response:
    path_and_port = _str_args(args, 2, state)
    if path_and_port is None:
        return None
    path, port = path_and_port
    if port.upper() not in ("GPIB", "GPI"):
        state.push_error(EventCode.INVALID_CHARACTER_DATA)
        return None
    data: bytes | None = None
    with _os_errors_as_events(state), open(virtual_to_real(path, state.filesystem), "rb") as f:
        data = f.read()
    return data


def _write_file_handler(query: bool, args: list[Arg], state: InstrumentState) -> Response:
    paths = _str_args(args, 1, state)
    if paths is None:
        return None
    if len(args) < 2:
        state.push_error(EventCode.MISSING_PARAMETER)
        return None
    data = args[1]
    if isinstance(data, str):
        data = data.encode("latin-1")
    with _os_errors_as_events(state), open(virtual_to_real(paths[0], state.filesystem), "wb") as f:
        f.write(data)
    return None


def register_filesystem_commands(dispatcher: Dispatcher) -> None:
    dispatcher.register("FILESYSTEM:CWD", _cwd_handler)
    dispatcher.register("FILESYSTEM:CWD?", _cwd_handler)
    dispatcher.register("FILESYSTEM:DIR?", _dir_query)
    dispatcher.register("FILESYSTEM?", _dir_query)
    dispatcher.register("FILESYSTEM:MKDIR", _mkdir_handler)
    dispatcher.register("FILESYSTEM:RMDIR", _rmdir_handler)
    dispatcher.register("FILESYSTEM:DELETE", _delete_handler)
    dispatcher.register("FILESYSTEM:RENAME", _rename_handler)
    dispatcher.register("FILESYSTEM:COPY", _copy_handler)
    dispatcher.register("FILESYSTEM:READFILE", _read_file_handler)
    dispatcher.register("FILESYSTEM:PRINT", _read_file_handler)
    dispatcher.register("FILESYSTEM:WRITEFILE", _write_file_handler)
