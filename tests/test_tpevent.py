import pytest

from tptools.sqlmodels import TPEvent


def test_repr(tpevent1: TPEvent) -> None:
    tpevent1.abbreviation = None
    assert repr(tpevent1) == "TPEvent(id=1, name='Herren 1', gender=2)"


def test_repr_abbreviation(tpevent2: TPEvent) -> None:
    assert repr(tpevent2) == "TPEvent(id=2, name='D1', gender=1)"


def test_str(tpevent1: TPEvent) -> None:
    assert str(tpevent1) == "Herren 1"


def test_eq(tpevent1: TPEvent, tpevent1copy: TPEvent) -> None:
    assert tpevent1 == tpevent1copy


def test_ne(tpevent1: TPEvent, tpevent2: TPEvent) -> None:
    assert tpevent2 != tpevent1


def test_lt(tpevent1: TPEvent, tpevent2: TPEvent) -> None:
    assert tpevent2 < tpevent1


def test_le(tpevent1: TPEvent, tpevent2: TPEvent, tpevent1copy: TPEvent) -> None:
    assert tpevent2 <= tpevent1 and tpevent1 <= tpevent1copy


def test_gt(tpevent1: TPEvent, tpevent2: TPEvent) -> None:
    assert tpevent1 > tpevent2


def test_ge(tpevent1: TPEvent, tpevent2: TPEvent, tpevent1copy: TPEvent) -> None:
    assert tpevent1 >= tpevent2 and tpevent1 >= tpevent1copy


def test_no_cmp(tpevent1: TPEvent) -> None:
    with pytest.raises(NotImplementedError):
        assert tpevent1 == object()
