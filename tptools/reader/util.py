# needed < 3.14 so that annotations aren't evaluated
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .interfaces import RecordType

if TYPE_CHECKING:
    from collections.abc import Generator
    from typing import Callable, Iterable


def get_record_from_row(
    columns: list[str],
    row: list[Any],
    *,
    skipcols: list[str] | None = None,
    strict: bool = False,
) -> RecordType:
    return {
        col: field
        for col, field in zip(columns, row, strict=strict)
        if col not in (skipcols or [])
    }


def try_coerce_int[T](value: T) -> int | T:
    try:
        return int(value)  # type:ignore
    except (ValueError, TypeError):
        return value


def try_coerce_bool[T](value: T) -> bool | T:
    if isinstance(value, bool):
        return value

    elif isinstance(value, str):
        if value.lower() in ("true", "t"):
            return True
        elif value.lower() in ("false", "f"):
            return False

    return value


def try_coerce_emptystring[T](value: T) -> None | T:
    return None if value == "" else value


def coerce_values(
    coerce_fn: Callable[[Any], Any], seq: Iterable[tuple[str, Any]]
) -> Generator[tuple[str, Any]]:
    return ((k, coerce_fn(v)) for k, v in seq)
