from collections.abc import Mapping

import pytest

from tptools.sqlmodels import Court


def test_repr(court1: Court) -> None:
    assert repr(court1) == "Court(id=1, name='C01', location.name='Sports4You')"


def test_eq(court1: Court, court1copy: Court) -> None:
    assert court1 == court1copy


def test_ne(court1: Court, court2: Court) -> None:
    assert court1 != court2


def test_lt(court1: Court, court2: Court) -> None:
    assert court1 < court2


def test_le(court1: Court, court2: Court, court1copy: Court) -> None:
    assert court1 <= court2 and court1 <= court1copy


def test_gt(court1: Court, court2: Court) -> None:
    assert court2 > court1


def test_ge(court1: Court, court2: Court, court1copy: Court) -> None:
    assert court2 >= court1 and court1 >= court1copy


def test_no_cmp(court1: Court) -> None:
    with pytest.raises(NotImplementedError):
        assert court1 == object()


def test_lt_sortorder(court1: Court, court2: Court) -> None:
    court1.sortorder = 3
    court2.sortorder = 2
    court2.location = court1.location
    assert court2 < court1


def test_model_dump_has_location(court1: Court) -> None:
    md = court1.model_dump()
    assert "locationid_" not in md
    assert isinstance(md.get("location"), Mapping)
