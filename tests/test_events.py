import pytest

from scpi.events import EventCode, message


@pytest.mark.parametrize("code", list(EventCode))
def test_message_every_event_code_has_text(code):
    assert message(code)
