# Shared by the dispatcher and every command module, so it lives apart from all of them.
from __future__ import annotations

from dataclasses import dataclass, field

_DEVICE_ERROR_BIT = 0x08


@dataclass
class FileSystemState:
    cwd: str = r"C:\TekScope"
    root: str = ""


@dataclass
class InstrumentState:
    headers: bool = True
    esr: int = 0
    stb: int = 0
    event_queue: list[int] = field(default_factory=list)
    filesystem: FileSystemState = field(default_factory=FileSystemState)

    def push_error(self, code: int) -> None:
        """Record an event code and flag it in the Event Status Register."""
        self.event_queue.append(code)
        self.esr |= _DEVICE_ERROR_BIT
