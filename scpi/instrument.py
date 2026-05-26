from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class InstrumentState:
    headers: bool = True
    esr: int = 0
    stb: int = 0
    event_queue: list = field(default_factory=list)
    filesystem: object = field(default=None)  # set to FileSystemState after import
