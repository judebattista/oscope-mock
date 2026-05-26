# scpi/instrument.py
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class InstrumentState:
    headers: bool = True
    esr: int = 0
    stb: int = 0
    event_queue: list = field(default_factory=list)
    filesystem: object = field(default=None)


_IDN = "TEKTRONIX,TDS5054B,0,CF:91.1CT FV:v2.00 TDS5054B"


def _hdr_value(val: str) -> bool:
    upper = val.strip().upper()
    if upper in ("ON", "1"):
        return True
    if upper in ("OFF", "0"):
        return False
    raise ValueError(f"Invalid HDR value: {val!r}")


def register_instrument_commands(dispatcher, state: InstrumentState) -> None:
    def idn(query, args, s):
        return _IDN

    def rst(query, args, s):
        s.filesystem.cwd = r"C:\TekScope"
        s.headers = True
        s.event_queue.clear()

    def cls(query, args, s):
        s.esr = 0
        s.stb = 0
        s.event_queue.clear()

    def esr(query, args, s):
        val = s.esr
        s.esr = 0
        return str(val)

    def stb(query, args, s):
        return str(s.stb)

    def opc(query, args, s):
        if query:
            return "1"
        s.esr |= 0x01

    def hdr(query, args, s):
        if query:
            return "1" if s.headers else "0"
        if args:
            try:
                s.headers = _hdr_value(args[0])
            except ValueError:
                s.event_queue.append(110)
                s.esr |= 0x08

    dispatcher.register("*IDN?",    idn)
    dispatcher.register("*RST",     rst)
    dispatcher.register("*CLS",     cls)
    dispatcher.register("*ESR?",    esr)
    dispatcher.register("*STB?",    stb)
    dispatcher.register("*OPC",     opc)
    dispatcher.register("*OPC?",    opc)
    dispatcher.register("HDR",      hdr)
    dispatcher.register("HDR?",     hdr)
    dispatcher.register("HEADER",   hdr)
    dispatcher.register("HEADER?",  hdr)
