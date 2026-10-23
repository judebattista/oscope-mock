from __future__ import annotations

from enum import IntEnum


class EventCode(IntEnum):
    """Event codes from the manual's Messages tables.

    The manual's execution-error table (200-series) is missing from both the PDF and its
    markdown conversion. Its command errors (100-series) match SCPI-99 exactly with the sign
    dropped, so the 2xx codes below assume the same of SCPI-99's mass-storage errors.
    """

    QUEUE_EMPTY = 0
    NEW_EVENTS_PENDING = 1
    DATA_TYPE_ERROR = 104
    MISSING_PARAMETER = 109
    COMMAND_HEADER_ERROR = 110
    INVALID_CHARACTER_DATA = 141
    MASS_STORAGE_ERROR = 250
    FILE_NAME_NOT_FOUND = 256
    FILE_NAME_ERROR = 257


_MESSAGES: dict[EventCode, str] = {
    EventCode.QUEUE_EMPTY: "No events to report; queue empty",
    EventCode.NEW_EVENTS_PENDING: "No events to report; new events pending *ESR?",
    EventCode.DATA_TYPE_ERROR: "Data type error",
    EventCode.MISSING_PARAMETER: "Missing parameter",
    EventCode.COMMAND_HEADER_ERROR: "Command header error",
    EventCode.INVALID_CHARACTER_DATA: "Invalid character data",
    EventCode.MASS_STORAGE_ERROR: "Mass storage error",
    EventCode.FILE_NAME_NOT_FOUND: "File name not found",
    EventCode.FILE_NAME_ERROR: "File name error",
}


def message(code: EventCode) -> str:
    """Return the manual's explanatory text for an event code."""
    return _MESSAGES[code]
