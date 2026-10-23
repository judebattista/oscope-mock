from scpi.dispatcher import Dispatcher
from scpi.events import EventCode
from scpi.instrument import register_instrument_commands
from scpi.state import InstrumentState


def test_instrument_state_defaults_headers_on_and_registers_clear() -> None:
    s = InstrumentState()
    assert s.headers is True
    assert s.esr == 0
    assert s.stb == 0
    assert s.event_queue == []


def test_instrument_state_instances_have_independent_event_queues() -> None:
    a = InstrumentState()
    b = InstrumentState()
    a.event_queue.append(EventCode.COMMAND_HEADER_ERROR)
    assert b.event_queue == []


def make_full_state() -> InstrumentState:
    return InstrumentState()


def make_dispatcher() -> Dispatcher:
    d = Dispatcher()
    register_instrument_commands(d)
    return d


def test_idn_query_returns_identity_string() -> None:
    state = make_full_state()
    d = make_dispatcher()
    resp = d.dispatch("*IDN", True, [], state)
    assert resp == "TEKTRONIX,TDS5054B,0,CF:91.1CT FV:v2.00 TDS5054B"


def test_rst_after_cwd_change_resets_cwd_to_default() -> None:
    state = make_full_state()
    state.filesystem.cwd = r"C:\TekScope\Waveforms"
    d = make_dispatcher()
    d.dispatch("*RST", False, [], state)
    assert state.filesystem.cwd == r"C:\TekScope"


def test_rst_with_queued_events_clears_event_queue() -> None:
    state = make_full_state()
    state.event_queue.append(EventCode.COMMAND_HEADER_ERROR)
    d = make_dispatcher()
    d.dispatch("*RST", False, [], state)
    assert state.event_queue == []


def test_cls_with_set_registers_clears_registers_and_queue() -> None:
    state = make_full_state()
    state.esr = 0xFF
    state.stb = 0xFF
    state.event_queue.append(EventCode.COMMAND_HEADER_ERROR)
    d = make_dispatcher()
    d.dispatch("*CLS", False, [], state)
    assert state.esr == 0
    assert state.stb == 0
    assert state.event_queue == []


def test_esr_query_with_bits_set_returns_value_and_clears() -> None:
    state = make_full_state()
    state.esr = 42
    d = make_dispatcher()
    resp = d.dispatch("*ESR", True, [], state)
    assert resp == "42"
    assert state.esr == 0


def test_stb_query_returns_status_byte() -> None:
    state = make_full_state()
    state.stb = 7
    d = make_dispatcher()
    resp = d.dispatch("*STB", True, [], state)
    assert resp == "7"


def test_opc_command_sets_opc_bit() -> None:
    state = make_full_state()
    d = make_dispatcher()
    d.dispatch("*OPC", False, [], state)
    assert state.esr & 0x01  # OPC bit


def test_opc_query_returns_one() -> None:
    state = make_full_state()
    d = make_dispatcher()
    resp = d.dispatch("*OPC", True, [], state)
    assert resp == "1"


def test_hdr_off_disables_headers() -> None:
    state = make_full_state()
    d = make_dispatcher()
    d.dispatch("HDR", False, ["OFF"], state)
    assert state.headers is False


def test_hdr_on_enables_headers() -> None:
    state = make_full_state()
    state.headers = False
    d = make_dispatcher()
    d.dispatch("HDR", False, ["ON"], state)
    assert state.headers is True


def test_hdr_nr1_zero_disables_headers() -> None:
    state = make_full_state()
    d = make_dispatcher()
    d.dispatch("HDR", False, ["0"], state)
    assert state.headers is False


def test_hdr_nr1_one_enables_headers() -> None:
    state = make_full_state()
    state.headers = False
    d = make_dispatcher()
    d.dispatch("HDR", False, ["1"], state)
    assert state.headers is True


def test_hdr_query_headers_on_returns_one() -> None:
    state = make_full_state()
    d = make_dispatcher()
    resp = d.dispatch("HDR", True, [], state)
    assert resp == "1"


def test_hdr_query_headers_off_returns_zero() -> None:
    state = make_full_state()
    state.headers = False
    d = make_dispatcher()
    resp = d.dispatch("HDR", True, [], state)
    assert resp == "0"


def test_header_long_form_off_disables_headers() -> None:
    state = make_full_state()
    d = make_dispatcher()
    d.dispatch("HEADER", False, ["OFF"], state)
    assert state.headers is False


def test_header_long_form_query_returns_header_state() -> None:
    state = make_full_state()
    d = make_dispatcher()
    resp = d.dispatch("HEADER", True, [], state)
    assert resp == "1"


def test_hdr_invalid_value_pushes_error_and_keeps_headers() -> None:
    state = make_full_state()
    d = make_dispatcher()
    d.dispatch("HDR", False, ["INVALID"], state)
    assert EventCode.INVALID_CHARACTER_DATA in state.event_queue
    assert state.headers is True  # unchanged


def test_rst_with_headers_off_restores_headers_on() -> None:
    state = make_full_state()
    state.headers = False
    d = make_dispatcher()
    d.dispatch("*RST", False, [], state)
    assert state.headers is True


def test_evmsg_query_after_esr_read_returns_code_and_message() -> None:
    state = make_full_state()
    d = make_dispatcher()
    state.push_error(EventCode.COMMAND_HEADER_ERROR)
    d.dispatch("*ESR", True, [], state)
    resp = d.dispatch("EVMSG", True, [], state)
    assert resp == '110,"Command header error"'


def test_evmsg_query_after_reading_event_reports_queue_empty() -> None:
    state = make_full_state()
    d = make_dispatcher()
    state.push_error(EventCode.COMMAND_HEADER_ERROR)
    d.dispatch("*ESR", True, [], state)
    d.dispatch("EVMSG", True, [], state)
    resp = d.dispatch("EVMSG", True, [], state)
    assert resp == '0,"No events to report; queue empty"'


def test_evmsg_query_without_esr_read_reports_new_events_pending() -> None:
    state = make_full_state()
    d = make_dispatcher()
    state.push_error(EventCode.COMMAND_HEADER_ERROR)
    resp = d.dispatch("EVMSG", True, [], state)
    assert resp == '1,"No events to report; new events pending *ESR?"'


def test_evmsg_query_no_events_reports_queue_empty() -> None:
    state = make_full_state()
    d = make_dispatcher()
    resp = d.dispatch("EVMSG", True, [], state)
    assert resp == '0,"No events to report; queue empty"'


def test_esr_query_discards_events_summarized_by_previous_read() -> None:
    state = make_full_state()
    d = make_dispatcher()
    state.push_error(EventCode.COMMAND_HEADER_ERROR)
    d.dispatch("*ESR", True, [], state)
    state.push_error(EventCode.FILE_NAME_NOT_FOUND)
    d.dispatch("*ESR", True, [], state)
    first = d.dispatch("EVMSG", True, [], state)
    second = d.dispatch("EVMSG", True, [], state)
    assert first == '256,"File name not found"'
    assert second == '0,"No events to report; queue empty"'


def test_cls_after_esr_read_discards_summarized_events() -> None:
    state = make_full_state()
    d = make_dispatcher()
    state.push_error(EventCode.COMMAND_HEADER_ERROR)
    d.dispatch("*ESR", True, [], state)
    d.dispatch("*CLS", False, [], state)
    resp = d.dispatch("EVMSG", True, [], state)
    assert resp == '0,"No events to report; queue empty"'


def test_hdr_nonzero_nr1_enables_headers() -> None:
    state = make_full_state()
    state.headers = False
    d = make_dispatcher()
    d.dispatch("HDR", False, ["5"], state)
    assert state.headers is True


def test_verbose_query_initially_returns_one() -> None:
    state = make_full_state()
    d = make_dispatcher()
    resp = d.dispatch("VERBOSE", True, [], state)
    assert resp == "1"


def test_verbose_off_then_query_returns_zero() -> None:
    state = make_full_state()
    d = make_dispatcher()
    d.dispatch("VERBOSE", False, ["OFF"], state)
    resp = d.dispatch("VERBOSE", True, [], state)
    assert resp == "0"
    assert state.event_queue == []


def test_verbose_invalid_value_pushes_invalid_character_data() -> None:
    state = make_full_state()
    d = make_dispatcher()
    d.dispatch("VERBOSE", False, ["LOUD"], state)
    assert EventCode.INVALID_CHARACTER_DATA in state.event_queue
