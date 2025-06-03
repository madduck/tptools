import json
import pathlib
from collections.abc import Callable, Generator, Iterable, Mapping, MutableMapping
from datetime import datetime
from typing import Any

from dateutil.parser import parse as date_parser

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


def dict_key_translator[T](
    indata: Mapping[str, T], xlate: Mapping[str, str], *, strict: bool = False
) -> MutableMapping[str, T]:
    return {
        xlate.get(key, key): value
        for key, value in indata.items()
        if (key in xlate or not strict)
    }


def normalise_time(
    time: datetime | str | None, *, nodate_value: datetime
) -> None | datetime:
    ret = None
    if time is None:
        return None

    elif isinstance(time, str):
        ret = date_parser(time)

    else:
        ret = time

    if not isinstance(nodate_value, datetime):
        # screw pyright, which cannot be disabled for this line with type:ignore
        raise ValueError("nodate_value must be a datetime instance")

    return ret if ret != nodate_value else None


def zero_to_none[T](value: T) -> None | T:
    return None if value == 0 else value


def reduce_common_prefix(
    a: str | None, b: str | None, *, joinstr: str = "/"
) -> str | None:
    if a is None and b is None:
        return None
    elif a is None or len(a) == 0:
        return f"/{b}"
    elif b is None or len(b) == 0:
        return f"{a}/"

    n = 0
    for i, j in zip(a, b, strict=False):
        if i != j:
            break
        n += 1

    if len(a[n:]) != len(b[n:]):
        return f"{a[:n]}…{a[n:]}{joinstr}…{b[n:]}"
    else:
        b = b[n:]
        return f"{a}{joinstr}{b or '='}"
