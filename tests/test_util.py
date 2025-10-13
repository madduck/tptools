import asyncio
import logging
import pathlib
from contextlib import nullcontext
from datetime import datetime
from enum import IntEnum
from pathlib import Path
from typing import Any, ContextManager

import pytest
from pytest_mock import MockerFixture
from sqlalchemy import Dialect

import tptools.util as util

type StrTable = list[list[str]]


@pytest.mark.parametrize(
    "value,result",
    [
        (None, False),
        (0, False),
        ("", False),
        ("no", False),
        ("0", False),
        (False, False),
        (True, True),
        (1, True),
        ("1", True),
        ("t", True),
        ("true", True),
        ("True", True),
        ("TRUE", True),
        ("y", True),
        ("yes", True),
        ("Yes", True),
        ("YES", True),
        ("j", True),
        ("ja", True),
        ("Ja", True),
        ("JA", True),
        ("trustme", True),
        ("anything", False),
    ],
)
def test_is_truish(value: Any, result: bool) -> None:
    assert util.is_truish(value) is result


@pytest.fixture
def columns() -> StrTable:
    return [
        ["zero", "other", "stuff"],
        ["one", "other", "stuff"],
        ["two", "other", "stuff"],
        ["three", "other", "stuff"],
    ]


def test_get_record_from_row(columns: StrTable) -> None:
    columnnames = [c[0] for c in columns]
    row = list(range(len(columnnames)))
    rec = util.get_record_from_row(columnnames, row)
    for col in columnnames:
        assert col in rec

    for i, col in enumerate(columnnames):
        assert rec[col] == i


def test_get_record_from_row_skipcols(columns: StrTable) -> None:
    columnnames = [c[0] for c in columns]
    row = list(range(len(columnnames)))
    skipcols = ["two", "zero"]
    rec = util.get_record_from_row(columnnames, row, skipcols=["two", "zero"])
    assert len(rec) == len(columnnames) - len(skipcols)


def test_get_record_from_row_skipcols_extra(columns: StrTable) -> None:
    columnnames = [c[0] for c in columns]
    row = list(range(len(columnnames)))
    skipcols = ["two", "zero", "hundred"]
    rec = util.get_record_from_row(columnnames, row, skipcols=["two", "zero"])
    assert len(rec) == len(columnnames) - len(skipcols) + 1


@pytest.mark.parametrize(
    "rowdiff,result",
    [
        (0, 4),
        (-1, 3),
        (1, 4),
    ],
)
def test_get_record_from_row_skipcols_nonstrict_rowvar(
    columns: StrTable, rowdiff: int, result: int
) -> None:
    columnnames = [c[0] for c in columns]
    row = list(range(len(columnnames) + rowdiff))
    rec = util.get_record_from_row(columnnames, row)
    assert len(rec) == result


@pytest.mark.parametrize(
    "coldiff,result",
    [
        (0, 4),
        (-1, 3),
        (1, 4),
    ],
)
def test_get_record_from_row_skipcols_nonstrict_colvar(
    columns: StrTable, coldiff: int, result: int
) -> None:
    columnnames = [c[0] for c in columns]
    row = list(range(len(columnnames)))
    rec = util.get_record_from_row(columnnames[: len(columnnames) + coldiff], row)
    assert len(rec) == result


@pytest.mark.parametrize("rowdiff", [-1, 1])
def test_get_record_from_row_skipcols_strict(columns: StrTable, rowdiff: int) -> None:
    columnnames = [c[0] for c in columns]
    row = list(range(len(columnnames) - rowdiff))
    with pytest.raises(ValueError):
        util.get_record_from_row(columnnames, row, strict=True)


@pytest.mark.parametrize("input,output", [(1, 1), ("2", 2), ("three", "three")])
def test_coerce_int(input: Any, output: Any) -> None:
    assert util.try_coerce_int(input) == output


def test_sequence_int_coercion() -> None:
    gen = util.coerce_values(
        util.try_coerce_int, {"one": 1, "two": "2", "three": "drei"}.items()
    )
    lst = [x[1] for x in gen]
    assert lst[0] == int(lst[0])
    assert lst[1] == int(lst[1])
    with pytest.raises(ValueError):
        assert lst[2] == int(lst[2])


@pytest.mark.parametrize(
    "input,output",
    [
        (False, False),
        (True, True),
        ("t", True),
        ("true", True),
        ("True", True),
        ("TRUE", True),
        ("T", True),
        ("TrUe", True),
        ("false", False),
        ("False", False),
        ("FALSE", False),
        ("F", False),
        ("FaLsE", False),
        ("f", False),
        ("nonboolean", "nonboolean"),
        (None, None),
        (3, 3),
    ],
)
def test_coerce_bool(input: Any, output: Any) -> None:
    assert util.try_coerce_bool(input) == output


def test_sequence_bool_coercion() -> None:
    gen = util.coerce_values(
        util.try_coerce_bool, {"one": "t", "two": True, "three": ""}.items()
    )
    assert next(gen)[1] is True
    assert next(gen)[1] is True
    assert next(gen)[1] not in (True, False)


@pytest.mark.parametrize(
    "input,output", [("", None), ("string", "string"), (None, None)]
)
def test_coerce_emptystring(input: Any, output: Any) -> None:
    assert util.try_coerce_emptystring(input) == output


def test_sequence_emptystring_coercion() -> None:
    gen = util.coerce_values(
        util.try_coerce_emptystring,
        {"one": "", "two": None, "three": "drei"}.items(),
    )
    assert next(gen)[1] is None
    assert next(gen)[1] is None
    assert next(gen)[1] is not None


def test_dict_key_translator() -> None:
    source = {"a": 1, "b": 2}
    translation = {"a": "A"}
    result = util.dict_key_translator(source, translation)
    assert result["A"] == source["a"]
    assert "b" in result


def test_dict_key_translator_strict() -> None:
    source = {"a": 1, "b": 2}
    translation = {"a": "A"}
    result = util.dict_key_translator(source, translation, strict=True)
    assert result["A"] == source["a"]
    assert "b" not in result


_DT = datetime(1970, 1, 2, 3, 4, 5)
_DTx = datetime(1976, 5, 4, 3, 2, 1)


@pytest.mark.parametrize(
    "input,result", [(None, None), (_DT, _DT), (_DTx, None), (_DT.isoformat(), _DT)]
)
def test_normalise_time(input: Any, result: Any) -> None:
    assert util.normalise_time(input, nodate_value=_DTx) == result


def test_normalise_time_nodate_datetime() -> None:
    with pytest.raises(ValueError, match="nodate_value must be a datetime instance"):
        util.normalise_time(_DT, nodate_value="1970-01-02 03:04:05")  # type: ignore


@pytest.mark.parametrize(
    "input,result", [(None, None), (1, 1), (-1, -1), ("str", "str"), (0, None)]
)
def test_normalise_zero_to_none(input: Any, result: Any) -> None:
    assert util.zero_to_none(input) == result


@pytest.mark.parametrize(
    "a,b,joinstr,result",
    [
        ("11", "11", None, "11/="),
        ("11", "12", None, "11/2"),
        ("11", "12", "@", "11@2"),
        ("11", "22", None, "11/22"),
        ("12", "34", None, "12/34"),
        ("12", "13", None, "12/3"),
        ("12", "134", None, "1…2/…34"),
        ("12", "134", "…", "1…2……34"),
        ("12", "1", None, "1…2/…"),
        ("", "34", None, "/34"),
        ("12", "", None, "12/"),
        ("1", "1", None, "1/="),
        ("1", None, None, "1/"),
        (None, "1", None, "/1"),
        (None, None, None, None),
        (None, None, "@", None),
    ],
)
def test_reduce_common_prefix(a: str, b: str, joinstr: str | None, result: str) -> None:
    if joinstr is None:
        assert util.reduce_common_prefix(a, b) == result
    else:
        assert util.reduce_common_prefix(a, b, joinstr=joinstr) == result


class DummyEnum(IntEnum):
    ONE = 1
    TWO = 2


type DummyEnumAsInteger = util.EnumAsInteger[DummyEnum]


@pytest.fixture
def EnumAsIntegerInstance() -> DummyEnumAsInteger:
    return util.EnumAsInteger(DummyEnum)


def test_enumasinteger_bind(EnumAsIntegerInstance: DummyEnumAsInteger) -> None:
    assert (
        EnumAsIntegerInstance.process_bind_param(DummyEnum.ONE, Dialect())
        == DummyEnum.ONE.value
    )


def test_enumasinteger_bind_wrong_type(
    EnumAsIntegerInstance: DummyEnumAsInteger,
) -> None:
    with pytest.raises(ValueError, match="expected DummyEnum value"):
        _ = EnumAsIntegerInstance.process_bind_param("string", Dialect())  # type: ignore[arg-type]


def test_enumasinteger_result(EnumAsIntegerInstance: DummyEnumAsInteger) -> None:
    assert (
        EnumAsIntegerInstance.process_result_value(DummyEnum.ONE.value, Dialect())
        == DummyEnum.ONE
    )


def test_enumasinteger_result_wrong_type(
    EnumAsIntegerInstance: DummyEnumAsInteger,
) -> None:
    with pytest.raises(ValueError, match="expected an integer"):
        _ = EnumAsIntegerInstance.process_result_value("string", Dialect())


def test_enumasinteger_copy(EnumAsIntegerInstance: DummyEnumAsInteger) -> None:
    assert isinstance(EnumAsIntegerInstance.copy(), util.EnumAsInteger)


def test_mdb_odbc_connstr() -> None:
    assert util.make_mdb_odbc_connstring(Path("/path/to/db"), uid="uid", pwd="pwd") == (
        "DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};"
        "DBQ=/path/to/db;Pwd=pwd;Uid=uid"
    )


def test_mdb_odbc_connstr_no_uid() -> None:
    assert util.make_mdb_odbc_connstring(Path("/path/to/db"), pwd="pwd") == (
        "DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=/path/to/db;Pwd=pwd"
    )


def test_mdb_odbc_connstr_no_pwd() -> None:
    assert util.make_mdb_odbc_connstring(Path("/path/to/db"), uid="uid") == (
        "DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=/path/to/db;Uid=uid"
    )


def test_mdb_odbc_connstr_admin_no_uid() -> None:
    assert util.make_mdb_odbc_connstring(
        Path("/path/to/db"), uid="Admin", pwd="pwd"
    ) == ("DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=/path/to/db;Pwd=pwd")


def test_mdb_odbc_connstr_exclusive() -> None:
    assert "Exclusive=" in util.make_mdb_odbc_connstring(
        Path("/path/to/db"), exclusive=True
    )


@pytest.mark.parametrize("level", [None, logging.ERROR])
def test_silence_logger(level: int | None, mocker: MockerFixture) -> None:
    logger = mocker.MagicMock(spec=logging.Logger)

    kwargs: dict[str, Any] = {"get_logger_fn": lambda _: logger}
    if level is not None:
        kwargs["level"] = level
    util.silence_logger("test", **kwargs)

    assert logger.propagate is False
    assert logger.setLevel.call_count == 1
    assert logger.setLevel.call_args.args[0] == level or logging.WARNING


@pytest.mark.asyncio
async def test_sleep_not_forever() -> None:
    assert await util.sleep_forever(0, forever=False) is None


@pytest.mark.asyncio
async def test_sleep_forever() -> None:
    task = asyncio.create_task(util.sleep_forever(0.001))
    await asyncio.sleep(0.01)
    task.cancel()
    assert task.cancelling() == 1


@pytest.mark.parametrize(
    "instr, eol, exp",
    [
        ("foobar", None, nullcontext(6)),
        ("foobar", "\n", nullcontext(7)),
        # TODO:test data that would block…
    ],
)
def test_nonblocking_write(
    tmp_path: pathlib.Path,
    instr: str,
    eol: str | None,
    exp: ContextManager[int | Exception],
) -> None:
    with open(tmp_path / "file", "wb", buffering=0) as f, exp as res:
        assert util.nonblocking_write(instr, file=f, eol=eol) == res  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "inp, present, exp",
    [
        (None, False, None),
        (42, True, 42),
        (3.14, True, 3.14),
        ("str", True, "str"),
        (True, True, 1),
        (False, True, 0),
    ],
)
def test_dict_value_replace_bool_with_int(inp: Any, present: bool, exp: Any) -> None:
    res = util.normalise_dict_values_for_query_string({"value": inp})
    if present:
        assert res.pop("value") == exp
    else:
        assert "value" not in res
