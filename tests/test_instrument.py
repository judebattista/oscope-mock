from scpi.dispatcher import Dispatcher
from scpi.instrument import register_instrument_commands
from scpi.state import InstrumentState


def test_default_state():
    s = InstrumentState()
    assert s.headers is True
    assert s.esr == 0
    assert s.stb == 0
    assert s.event_queue == []


def test_event_queue_is_independent():
    a = InstrumentState()
    b = InstrumentState()
    a.event_queue.append(110)
    assert b.event_queue == []


def make_full_state():
    return InstrumentState()


def make_dispatcher(state):
    d = Dispatcher()
    register_instrument_commands(d)
    return d


def test_idn_query():
    state = make_full_state()
    d = make_dispatcher(state)
    resp = d.dispatch("*IDN", True, [], state)
    assert resp == "TEKTRONIX,TDS5054B,0,CF:91.1CT FV:v2.00 TDS5054B"


def test_rst_resets_cwd():
    state = make_full_state()
    state.filesystem.cwd = r"C:\TekScope\Waveforms"
    d = make_dispatcher(state)
    d.dispatch("*RST", False, [], state)
    assert state.filesystem.cwd == r"C:\TekScope"


def test_rst_clears_event_queue():
    state = make_full_state()
    state.event_queue.append(110)
    d = make_dispatcher(state)
    d.dispatch("*RST", False, [], state)
    assert state.event_queue == []


def test_cls_clears_registers():
    state = make_full_state()
    state.esr = 0xFF
    state.stb = 0xFF
    state.event_queue.append(110)
    d = make_dispatcher(state)
    d.dispatch("*CLS", False, [], state)
    assert state.esr == 0
    assert state.stb == 0
    assert state.event_queue == []


def test_esr_query_returns_and_clears():
    state = make_full_state()
    state.esr = 42
    d = make_dispatcher(state)
    resp = d.dispatch("*ESR", True, [], state)
    assert resp == "42"
    assert state.esr == 0


def test_stb_query():
    state = make_full_state()
    state.stb = 7
    d = make_dispatcher(state)
    resp = d.dispatch("*STB", True, [], state)
    assert resp == "7"


def test_opc_sets_bit():
    state = make_full_state()
    d = make_dispatcher(state)
    d.dispatch("*OPC", False, [], state)
    assert state.esr & 0x01  # OPC bit


def test_opc_query_returns_1():
    state = make_full_state()
    d = make_dispatcher(state)
    resp = d.dispatch("*OPC", True, [], state)
    assert resp == "1"


def test_hdr_off():
    state = make_full_state()
    d = make_dispatcher(state)
    d.dispatch("HDR", False, ["OFF"], state)
    assert state.headers is False


def test_hdr_on():
    state = make_full_state()
    state.headers = False
    d = make_dispatcher(state)
    d.dispatch("HDR", False, ["ON"], state)
    assert state.headers is True


def test_hdr_nr1_zero():
    state = make_full_state()
    d = make_dispatcher(state)
    d.dispatch("HDR", False, ["0"], state)
    assert state.headers is False


def test_hdr_nr1_one():
    state = make_full_state()
    state.headers = False
    d = make_dispatcher(state)
    d.dispatch("HDR", False, ["1"], state)
    assert state.headers is True


def test_hdr_query_on():
    state = make_full_state()
    d = make_dispatcher(state)
    resp = d.dispatch("HDR", True, [], state)
    assert resp == "1"


def test_hdr_query_off():
    state = make_full_state()
    state.headers = False
    d = make_dispatcher(state)
    resp = d.dispatch("HDR", True, [], state)
    assert resp == "0"


def test_header_alias():
    state = make_full_state()
    d = make_dispatcher(state)
    d.dispatch("HEADER", False, ["OFF"], state)
    assert state.headers is False


def test_header_query_alias():
    state = make_full_state()
    d = make_dispatcher(state)
    resp = d.dispatch("HEADER", True, [], state)
    assert resp == "1"


def test_hdr_invalid_value_pushes_error():
    state = make_full_state()
    d = make_dispatcher(state)
    d.dispatch("HDR", False, ["INVALID"], state)
    assert 110 in state.event_queue
    assert state.headers is True  # unchanged


def test_rst_resets_headers():
    state = make_full_state()
    state.headers = False
    d = make_dispatcher(state)
    d.dispatch("*RST", False, [], state)
    assert state.headers is True
