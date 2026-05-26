from __future__ import annotations
import os
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
