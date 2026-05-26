from __future__ import annotations


class Dispatcher:
    def __init__(self):
        self._handlers: dict = {}

    def register(self, key: str, handler) -> None:
        """Register handler for a canonical key. Append '?' for query variants."""
        self._handlers[key] = handler

    def dispatch(self, key: str, query: bool, args: list, state) -> str | bytes | None:
        """Dispatch a parsed command to its handler. Returns response or None."""
        lookup = key + '?' if query else key
        handler = self._handlers.get(lookup)
        if handler is None:
            state.event_queue.append(110)
            state.esr |= 0x08
            return None
        return handler(query, args, state)
