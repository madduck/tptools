import pytest

import tptools.reader.util as util


@pytest.fixture
def columns():
    return [
        ["zero", "other", "stuff"],
        ["one", "other", "stuff"],
        ["two", "other", "stuff"],
        ["three", "other", "stuff"],
    ]


def test_get_record_from_row(columns):
    columns = [c[0] for c in columns]
    row = list(range(len(columns)))
    rec = util.get_record_from_row(columns, row)
    for col in columns:
        assert col in rec

    for i, col in enumerate(columns):
        assert rec[col] == i


def test_get_record_from_row_skipcols(columns):
    columns = [c[0] for c in columns]
    row = list(range(len(columns)))
    skipcols = ["two", "zero"]
    rec = util.get_record_from_row(columns, row, skipcols=["two", "zero"])
    assert len(rec) == len(columns) - len(skipcols)


def test_get_record_from_row_skipcols_extra(columns):
    columns = [c[0] for c in columns]
    row = list(range(len(columns)))
    skipcols = ["two", "zero", "hundred"]
    rec = util.get_record_from_row(columns, row, skipcols=["two", "zero"])
    assert len(rec) == len(columns) - len(skipcols) + 1


@pytest.mark.parametrize(
    "rowdiff,result",
    [
        (0, 4),
        (-1, 3),
        (1, 4),
    ],
)
def test_get_record_from_row_skipcols_nonstrict_rowvar(columns, rowdiff, result):
    columns = [c[0] for c in columns]
    row = list(range(len(columns) + rowdiff))
    rec = util.get_record_from_row(columns, row)
    assert len(rec) == result


@pytest.mark.parametrize(
    "coldiff,result",
    [
        (0, 4),
        (-1, 3),
        (1, 4),
    ],
)
def test_get_record_from_row_skipcols_nonstrict_colvar(columns, coldiff, result):
    columns = [c[0] for c in columns]
    row = list(range(len(columns)))
    rec = util.get_record_from_row(columns[: len(columns) + coldiff], row)
    assert len(rec) == result


@pytest.mark.parametrize("rowdiff", [-1, 1])
def test_get_record_from_row_skipcols_strict(columns, rowdiff):
    columns = [c[0] for c in columns]
    row = list(range(len(columns) - rowdiff))
    with pytest.raises(ValueError):
        util.get_record_from_row(columns, row, strict=True)


@pytest.mark.parametrize("input,output", [(1, 1), ("2", 2), ("three", "three")])
def test_coerce_int(input, output):
    assert util.try_coerce_int(input) == output


def test_sequence_int_coercion():
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
def test_coerce_bool(input, output):
    assert util.try_coerce_bool(input) == output


def test_sequence_bool_coercion():
    gen = util.coerce_values(
        util.try_coerce_bool, {"one": "t", "two": True, "three": ""}.items()
    )
    assert next(gen)[1] is True
    assert next(gen)[1] is True
    assert next(gen)[1] not in (True, False)


@pytest.mark.parametrize(
    "input,output", [("", None), ("string", "string"), (None, None)]
)
def test_coerce_emptystring(input, output):
    assert util.try_coerce_emptystring(input) == output


def test_sequence_emptystring_coercion():
    gen = util.coerce_values(
        util.try_coerce_emptystring,
        {"one": "", "two": None, "three": "drei"}.items(),
    )
    assert next(gen)[1] is None
    assert next(gen)[1] is None
    assert next(gen)[1] is not None
