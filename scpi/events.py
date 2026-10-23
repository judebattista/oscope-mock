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
