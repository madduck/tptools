import asyncio
import logging
import os
import pathlib
from collections.abc import Callable, Generator, Iterable, Mapping, MutableMapping
from datetime import datetime
from enum import IntEnum
from typing import Any, Never, TextIO

from dateutil.parser import parse as date_parser
from sqlalchemy import Dialect, Integer, TypeDecorator

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


class EnumAsInteger[EnumType: IntEnum](TypeDecorator[EnumType]):
    impl = Integer  # underlying database type

    def __init__(self, enum_type: type[EnumType]):
        super().__init__()
        self._enum_type = enum_type

    def process_bind_param(self, value: EnumType | None, dialect: Dialect) -> int:
        _ = dialect
        if isinstance(value, self._enum_type):
            return value.value
        raise ValueError(
            f"expected {self._enum_type.__name__} value, got {value.__class__.__name__}"
        )

    def process_result_value(self, value: Any | None, dialect: Dialect) -> EnumType:
        _ = dialect
        if isinstance(value, int):
            return self._enum_type(value)
        raise ValueError(f"expected an integer, got {value.__class__.__name__}")

    def copy(self, **_: Any) -> "EnumAsInteger[EnumType]":
        return EnumAsInteger(self._enum_type)


def make_mdb_odbc_connstring(
    path: pathlib.Path,
    *,
    uid: str | None = None,
    pwd: str | None = None,
    driver: str = "{Microsoft Access Driver (*.mdb, *.accdb)}",
    exclusive: bool = False,
) -> str:
    params = {
        "DRIVER": driver,
        "DBQ": path.absolute(),
    }

    if pwd is not None:
        params["Pwd"] = pwd

    if uid is not None and uid != "Admin":
        params["Uid"] = uid

    if exclusive:
        params["Exclusive"] = 1

    return ";".join(f"{k}={v}" for k, v in params.items())


def silence_logger(
    loggername: str,
    *,
    level: int = logging.WARNING,
    get_logger_fn: Callable[[str], logging.Logger] = logging.getLogger,
) -> None:
    logger = get_logger_fn(loggername)
    logger.setLevel(level)
    logger.propagate = False


async def sleep_forever(sleep: float = 1, *, forever: bool = True) -> Never | None:
    while await asyncio.sleep(sleep, forever):
        pass
    return None


def nonblocking_write(s: str, /, *, file: TextIO, eol: str | None = None) -> int:
    written = 0

    if eol is not None:
        s += eol

    bytes = s.encode()

    while written < len(bytes):
        try:
            written += os.write(file.fileno(), bytes[written:])

        except OSError:  # pragma: nocover TODO: how do I test for this branch?
            pass

    return written
