from scpi.dispatcher import Dispatcher
from scpi.parser import Arg
from scpi.state import InstrumentState


def make_state() -> InstrumentState:
    return InstrumentState()


def test_dispatch_registered_command_returns_handler_response() -> None:
    d = Dispatcher()
    d.register("PING", lambda query, args, state: "PONG")
    state = make_state()
    result = d.dispatch("PING", False, [], state)
    assert result == "PONG"


def test_dispatch_registered_query_returns_handler_response() -> None:
    d = Dispatcher()
    d.register("PING?", lambda query, args, state: "PONG")
    state = make_state()
    result = d.dispatch("PING", True, [], state)
    assert result == "PONG"


def test_dispatch_handler_without_response_returns_none() -> None:
    d = Dispatcher()
    d.register("NOP", lambda query, args, state: None)
    state = make_state()
    result = d.dispatch("NOP", False, [], state)
    assert result is None


def test_dispatch_unknown_command_pushes_command_header_error() -> None:
    d = Dispatcher()
    state = make_state()
    result = d.dispatch("UNKNOWN", False, [], state)
    assert result is None
    assert 110 in state.event_queue


def test_dispatch_unknown_command_sets_esr_error_bit() -> None:
    d = Dispatcher()
    state = make_state()
    d.dispatch("UNKNOWN", False, [], state)
    assert state.esr == 0x20  # CME, bit 5


def test_dispatch_registered_command_passes_query_args_and_state() -> None:
    d = Dispatcher()
    received: dict[str, object] = {}

    def handler(query: bool, args: list[Arg], state: InstrumentState) -> None:
        received["query"] = query
        received["args"] = args
        received["state"] = state
        return None

    d.register("CMD", handler)
    state = make_state()
    d.dispatch("CMD", False, ["x", "y"], state)
    assert received["query"] is False
    assert received["args"] == ["x", "y"]
    assert received["state"] is state
