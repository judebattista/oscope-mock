# Shared by the dispatcher and every command module, so it lives apart from all of them.
from __future__ import annotations

from dataclasses import dataclass, field

from scpi.events import EventCode

_CME_BIT = 0x20  # Command Error, ESR bit 5
_EXE_BIT = 0x10  # Execution Error, ESR bit 4


def _esr_bit(code: EventCode) -> int:
    if 100 <= code < 200:
        return _CME_BIT
    if 200 <= code < 300:
        return _EXE_BIT
    raise ValueError(f"Event code {code.name} ({code.value}) does not set an ESR error bit")


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

    def push_error(self, code: EventCode) -> None:
        """Record an event code and flag it in the Event Status Register."""
        self.event_queue.append(code)
        self.esr |= _esr_bit(code)
