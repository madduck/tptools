import pytest

from tptools.sqlmodels import TPEvent


def test_repr(event1: TPEvent) -> None:
    event1.abbreviation = None
    assert repr(event1) == "TPEvent(id=1, name='Herren 1', gender=2)"


def test_repr_abbreviation(event2: TPEvent) -> None:
    assert repr(event2) == "TPEvent(id=2, name='D1', gender=1)"


def test_str(event1: TPEvent) -> None:
    assert str(event1) == "Herren 1"


def test_eq(event1: TPEvent, event1copy: TPEvent) -> None:
    assert event1 == event1copy


def test_ne(event1: TPEvent, event2: TPEvent) -> None:
    assert event2 != event1


def test_lt(event1: TPEvent, event2: TPEvent) -> None:
    assert event2 < event1


def test_le(event1: TPEvent, event2: TPEvent, event1copy: TPEvent) -> None:
    assert event2 <= event1 and event1 <= event1copy


def test_gt(event1: TPEvent, event2: TPEvent) -> None:
    assert event1 > event2


def test_ge(event1: TPEvent, event2: TPEvent, event1copy: TPEvent) -> None:
    assert event1 >= event2 and event1 >= event1copy


def test_no_cmp(event1: TPEvent) -> None:
    with pytest.raises(NotImplementedError):
        assert event1 == object()
