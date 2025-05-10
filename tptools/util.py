import json
import pathlib
from collections.abc import Callable, Generator, Iterable, MutableMapping
from typing import Any

PACKAGE = pathlib.Path(__file__).parent.parent.name


def is_truish(value: Any) -> bool:
    if not value:
        return False

    if value is True:
        return True

    try:
        for letter in ("y", "j", "t"):
            if value.lower().startswith(letter):
                return True

    except AttributeError:
        pass

    try:
        if int(value):
            return True

    except ValueError:
        pass

    return False


def get_record_from_row(
    columns: Iterable[str],
    row: Iterable[Any],
    *,
    skipcols: Iterable[str] | None = None,
    strict: bool = False,
) -> MutableMapping[str, Any]:
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
