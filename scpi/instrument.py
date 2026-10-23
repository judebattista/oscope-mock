from __future__ import annotations

from scpi.dispatcher import Dispatcher, Response
from scpi.events import EventCode, message
from scpi.parser import Arg
from scpi.state import InstrumentState

_IDN = "TEKTRONIX,TDS5054B,0,CF:91.1CT FV:v2.00 TDS5054B"


def _parse_bool(arg: Arg) -> bool | None:
    """Parse an ON/OFF/NR1 argument; None means the value is not a valid boolean."""
    if not isinstance(arg, str):
        return None
    upper = arg.strip().upper()
    if upper == "ON":
        return True
    if upper == "OFF":
        return False
    try:
        return int(upper) != 0
    except ValueError:
        return None


def _idn(query: bool, args: list[Arg], s: InstrumentState) -> Response:
    return _IDN


def _rst(query: bool, args: list[Arg], s: InstrumentState) -> Response:
    s.filesystem.cwd = r"C:\TekScope"
    s.headers = True
    s.event_queue.clear()
    return None


def _cls(query: bool, args: list[Arg], s: InstrumentState) -> Response:
    s.esr = 0
    s.stb = 0
    s.event_queue.clear()
    s.summarized_events.clear()
    return None


def _esr(query: bool, args: list[Arg], s: InstrumentState) -> Response:
    val = s.esr
    s.esr = 0
    s.summarized_events = s.event_queue
    s.event_queue = []
    return str(val)


def _evmsg(query: bool, args: list[Arg], s: InstrumentState) -> Response:
    if s.summarized_events:
        code = s.summarized_events.pop(0)
    elif s.event_queue:
        code = EventCode.NEW_EVENTS_PENDING
    else:
        code = EventCode.QUEUE_EMPTY
    return f'{code.value},"{message(code)}"'


def _stb(query: bool, args: list[Arg], s: InstrumentState) -> Response:
    return str(s.stb)


def _opc(query: bool, args: list[Arg], s: InstrumentState) -> Response:
    if query:
        return "1"
    s.esr |= 0x01
    return None


def _hdr(query: bool, args: list[Arg], s: InstrumentState) -> Response:
    if query:
        return "1" if s.headers else "0"
    if not args:
        return None
    flag = _parse_bool(args[0])
    if flag is None:
        s.push_error(EventCode.INVALID_CHARACTER_DATA)
    else:
        s.headers = flag
    return None


def register_instrument_commands(dispatcher: Dispatcher) -> None:
    dispatcher.register("*IDN?", _idn)
    dispatcher.register("*RST", _rst)
    dispatcher.register("*CLS", _cls)
    dispatcher.register("*ESR?", _esr)
    dispatcher.register("EVMSG?", _evmsg)
    dispatcher.register("*STB?", _stb)
    dispatcher.register("*OPC", _opc)
    dispatcher.register("*OPC?", _opc)
    dispatcher.register("HDR", _hdr)
    dispatcher.register("HDR?", _hdr)
    dispatcher.register("HEADER", _hdr)
    dispatcher.register("HEADER?", _hdr)
