import pytest

from scpi.events import EventCode
from scpi.state import InstrumentState


def test_push_error_command_error_sets_cme_bit():
    state = InstrumentState()
    state.push_error(EventCode.COMMAND_HEADER_ERROR)
    assert state.esr == 0x20
    assert state.event_queue == [EventCode.COMMAND_HEADER_ERROR]


def test_push_error_execution_error_sets_exe_bit():
    state = InstrumentState()
    state.push_error(EventCode.FILE_NAME_NOT_FOUND)
    assert state.esr == 0x10


def test_push_error_no_event_code_raises_value_error():
    state = InstrumentState()
    with pytest.raises(ValueError, match="QUEUE_EMPTY"):
        state.push_error(EventCode.QUEUE_EMPTY)
