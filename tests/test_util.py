import logging
from datetime import datetime
from typing import Any

import pytest
from pytest_mock import MockerFixture

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
