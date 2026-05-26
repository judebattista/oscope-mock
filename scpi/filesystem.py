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


def register_filesystem_commands(dispatcher, state) -> None:
    dispatcher.register("FILESYSTEM:CWD",  _cwd_handler)
    dispatcher.register("FILESYSTEM:CWD?", _cwd_handler)
    dispatcher.register("FILESYSTEM:DIR?", _dir_query)
    dispatcher.register("FILESYSTEM?",     _dir_query)
