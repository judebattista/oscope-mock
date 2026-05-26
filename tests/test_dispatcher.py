import pytest
from scpi.dispatcher import Dispatcher
from scpi.instrument import InstrumentState


def make_state():
    return InstrumentState()


def test_dispatch_known_command():
    d = Dispatcher()
    d.register("PING", lambda query, args, state: "PONG")
    state = make_state()
    result = d.dispatch("PING", False, [], state)
    assert result == "PONG"


def test_dispatch_known_query():
    d = Dispatcher()
    d.register("PING?", lambda query, args, state: "PONG")
    state = make_state()
    result = d.dispatch("PING", True, [], state)
    assert result == "PONG"


def test_dispatch_no_response_command():
    d = Dispatcher()
    d.register("NOP", lambda query, args, state: None)
    state = make_state()
    result = d.dispatch("NOP", False, [], state)
    assert result is None


def test_dispatch_unknown_command_pushes_error():
    d = Dispatcher()
    state = make_state()
    result = d.dispatch("UNKNOWN", False, [], state)
    assert result is None
    assert 110 in state.event_queue


def test_dispatch_unknown_command_sets_esr_bit3():
    d = Dispatcher()
    state = make_state()
    d.dispatch("UNKNOWN", False, [], state)
    assert state.esr & 0x08  # bit 3


def test_dispatch_passes_args_and_state():
    d = Dispatcher()
    received = {}
    def handler(query, args, state):
        received['query'] = query
        received['args'] = args
        received['state'] = state
        return None
    d.register("CMD", handler)
    state = make_state()
    d.dispatch("CMD", False, ["x", "y"], state)
    assert received['query'] is False
    assert received['args'] == ["x", "y"]
    assert received['state'] is state
