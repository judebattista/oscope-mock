from scpi.instrument import InstrumentState


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
