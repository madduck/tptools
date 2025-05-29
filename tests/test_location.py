import pytest

from tptools.models import Location


def test_repr(location1: Location) -> None:
    assert repr(location1) == "Location(id=1, name='Sports4You', numcourts=0)"


def test_str(location1: Location) -> None:
    assert str(location1) == "Sports4You"


def test_eq(location1: Location, location1copy: Location) -> None:
    assert location1 == location1copy


def test_ne(location1: Location, location2: Location) -> None:
    assert location1 != location2


def test_lt(location1: Location, location2: Location) -> None:
    assert location1 < location2


def test_le(location1: Location, location2: Location, location1copy: Location) -> None:
    assert location1 <= location2 and location1 <= location1copy


def test_gt(location1: Location, location2: Location) -> None:
    assert location2 > location1


def test_ge(location1: Location, location2: Location, location1copy: Location) -> None:
    assert location2 >= location1 and location1 >= location1copy


def test_no_cmp(location1: Location) -> None:
    with pytest.raises(NotImplementedError):
        assert location1 == object()
