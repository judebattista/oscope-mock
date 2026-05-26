from __future__ import annotations
import os
import shutil
from dataclasses import dataclass


@dataclass
class FileSystemState:
    cwd: str = r"C:\TekScope"
    root: str = ""


def virtual_to_real(vpath: str, fs: FileSystemState) -> str:
    """Map a Windows virtual path to a real host path under fs.root."""
    # Normalize to backslashes
    normalized = vpath.replace('/', '\\')

    # Resolve relative paths against CWD
    if not (len(normalized) >= 2 and normalized[1] == ':'):
        if normalized.startswith('.\\'):
            normalized = normalized[2:]
        normalized = fs.cwd + '\\' + normalized

    # Now absolute: extract drive letter and remaining path
    drive = normalized[0].upper()
    rest = normalized[3:] if len(normalized) > 3 else ""  # skip "X:\"

    parts = [p for p in rest.split('\\') if p]
    return os.path.join(fs.root, drive, *parts) if parts else os.path.join(fs.root, drive)


def create_initial_structure(fs: FileSystemState) -> None:
    """Create the startup virtual directory tree on the real host filesystem."""
    for vpath in [r"C:\TekScope", r"C:\TekScope\Waveforms",
                  r"C:\TekScope\Images", r"C:\TekScope\Settings"]:
        os.makedirs(virtual_to_real(vpath, fs), exist_ok=True)


def _dir_query(query, args, state) -> str:
    real = virtual_to_real(state.filesystem.cwd, state.filesystem)
    entries = ['.', '..'] + sorted(os.listdir(real))
    return ','.join(f'"{e}"' for e in entries)


def _cwd_handler(query, args, state):
    if query:
        return f'"{state.filesystem.cwd}"'
    if args:
        state.filesystem.cwd = args[0]


def _push_error(state, code: int) -> None:
    state.event_queue.append(code)
    state.esr |= 0x08


def _mkdir_handler(query, args, state):
    if not args:
        _push_error(state, 110)
        return
    real = virtual_to_real(args[0], state.filesystem)
    if os.path.exists(real):
        _push_error(state, 2004)
        return
    os.makedirs(real, exist_ok=False)


def _rmdir_handler(query, args, state):
    if not args:
        _push_error(state, 110)
        return
    real = virtual_to_real(args[0], state.filesystem)
    try:
        os.rmdir(real)
    except FileNotFoundError:
        _push_error(state, 2002)
    except OSError:
        _push_error(state, 2003)


def _delete_handler(query, args, state):
    if not args:
        _push_error(state, 110)
        return
    real = virtual_to_real(args[0], state.filesystem)
    try:
        os.remove(real)
    except FileNotFoundError:
        _push_error(state, 2002)


def _rename_handler(query, args, state):
    if len(args) < 2:
        _push_error(state, 110)
        return
    src = virtual_to_real(args[0], state.filesystem)
    dst = virtual_to_real(args[1], state.filesystem)
    try:
        os.rename(src, dst)
    except FileNotFoundError:
        _push_error(state, 2002)


def _copy_handler(query, args, state):
    if len(args) < 2:
        _push_error(state, 110)
        return
    src = virtual_to_real(args[0], state.filesystem)
    dst = virtual_to_real(args[1], state.filesystem)
    try:
        shutil.copy2(src, dst)
    except FileNotFoundError:
        _push_error(state, 2002)


def register_filesystem_commands(dispatcher, state) -> None:
    dispatcher.register("FILESYSTEM:CWD",    _cwd_handler)
    dispatcher.register("FILESYSTEM:CWD?",   _cwd_handler)
    dispatcher.register("FILESYSTEM:DIR?",   _dir_query)
    dispatcher.register("FILESYSTEM?",       _dir_query)
    dispatcher.register("FILESYSTEM:MKDIR",  _mkdir_handler)
    dispatcher.register("FILESYSTEM:RMDIR",  _rmdir_handler)
    dispatcher.register("FILESYSTEM:DELETE", _delete_handler)
    dispatcher.register("FILESYSTEM:RENAME", _rename_handler)
    dispatcher.register("FILESYSTEM:COPY",   _copy_handler)
