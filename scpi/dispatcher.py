from __future__ import annotations

from collections.abc import Callable

from scpi.events import EventCode
from scpi.parser import Arg
from scpi.state import InstrumentState

Response = str | bytes | None
Handler = Callable[[bool, list[Arg], InstrumentState], Response]


class Dispatcher:
    def __init__(self) -> None:
        self._handlers: dict[str, Handler] = {}

    def register(self, key: str, handler: Handler) -> None:
        """Register handler for a canonical key. Append '?' for query variants."""
        self._handlers[key] = handler

    def dispatch(self, key: str, query: bool, args: list[Arg], state: InstrumentState) -> Response:
        """Dispatch a parsed command to its handler. Returns response or None."""
        lookup = key + "?" if query else key
        handler = self._handlers.get(lookup)
        if handler is None:
            state.push_error(EventCode.COMMAND_HEADER_ERROR)
            return None
        return handler(query, args, state)
