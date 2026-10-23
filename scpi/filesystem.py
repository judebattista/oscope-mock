from __future__ import annotations

import os
import shutil

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


def _dir_query(query: bool, args: list[Arg], state: InstrumentState) -> Response:
    real = virtual_to_real(state.filesystem.cwd, state.filesystem)
    entries = [".", ".."] + sorted(os.listdir(real))
    return ",".join(f'"{e}"' for e in entries)


def _cwd_handler(query: bool, args: list[Arg], state: InstrumentState) -> Response:
    if query:
        return f'"{state.filesystem.cwd}"'
    paths = _str_args(args, 1, state)
    if paths is not None:
        state.filesystem.cwd = paths[0]
    return None


def _mkdir_handler(query: bool, args: list[Arg], state: InstrumentState) -> Response:
    paths = _str_args(args, 1, state)
    if paths is None:
        return None
    real = virtual_to_real(paths[0], state.filesystem)
    if os.path.exists(real):
        state.push_error(EventCode.FILE_NAME_ERROR)
        return None
    os.makedirs(real, exist_ok=False)
    return None


def _rmdir_handler(query: bool, args: list[Arg], state: InstrumentState) -> Response:
    paths = _str_args(args, 1, state)
    if paths is None:
        return None
    real = virtual_to_real(paths[0], state.filesystem)
    try:
        os.rmdir(real)
    except FileNotFoundError:
        state.push_error(EventCode.FILE_NAME_NOT_FOUND)
    except OSError:
        state.push_error(EventCode.MASS_STORAGE_ERROR)
    return None


def _delete_handler(query: bool, args: list[Arg], state: InstrumentState) -> Response:
    paths = _str_args(args, 1, state)
    if paths is None:
        return None
    real = virtual_to_real(paths[0], state.filesystem)
    try:
        os.remove(real)
    except FileNotFoundError:
        state.push_error(EventCode.FILE_NAME_NOT_FOUND)
    return None


def _rename_handler(query: bool, args: list[Arg], state: InstrumentState) -> Response:
    paths = _str_args(args, 2, state)
    if paths is None:
        return None
    src = virtual_to_real(paths[0], state.filesystem)
    dst = virtual_to_real(paths[1], state.filesystem)
    try:
        os.rename(src, dst)
    except FileNotFoundError:
        state.push_error(EventCode.FILE_NAME_NOT_FOUND)
    return None


def _copy_handler(query: bool, args: list[Arg], state: InstrumentState) -> Response:
    paths = _str_args(args, 2, state)
    if paths is None:
        return None
    src = virtual_to_real(paths[0], state.filesystem)
    dst = virtual_to_real(paths[1], state.filesystem)
    try:
        shutil.copy2(src, dst)
    except FileNotFoundError:
        state.push_error(EventCode.FILE_NAME_NOT_FOUND)
    return None


def _read_file_handler(query: bool, args: list[Arg], state: InstrumentState) -> Response:
    paths = _str_args(args, 1, state)
    if paths is None:
        return None
    real = virtual_to_real(paths[0], state.filesystem)
    try:
        with open(real, "rb") as f:
            return f.read()
    except FileNotFoundError:
        state.push_error(EventCode.FILE_NAME_NOT_FOUND)
        return None


def _write_file_handler(query: bool, args: list[Arg], state: InstrumentState) -> Response:
    paths = _str_args(args, 1, state)
    if paths is None:
        return None
    if len(args) < 2:
        state.push_error(EventCode.MISSING_PARAMETER)
        return None
    real = virtual_to_real(paths[0], state.filesystem)
    data = args[1]
    if isinstance(data, str):
        data = data.encode("latin-1")
    try:
        with open(real, "wb") as f:
            f.write(data)
    except FileNotFoundError:
        state.push_error(EventCode.FILE_NAME_NOT_FOUND)
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
