import pytest

from tptools.sqlmodels import TPLocation


def test_repr(location1: TPLocation) -> None:
    assert repr(location1) == "TPLocation(id=1, name='Sports4You', numcourts=0)"


def test_str(location1: TPLocation) -> None:
    assert str(location1) == "Sports4You"


def test_eq(location1: TPLocation, location1copy: TPLocation) -> None:
    assert location1 == location1copy


def test_ne(location1: TPLocation, location2: TPLocation) -> None:
    assert location1 != location2


def test_lt(location1: TPLocation, location2: TPLocation) -> None:
    assert location1 < location2


def test_le(
    location1: TPLocation, location2: TPLocation, location1copy: TPLocation
) -> None:
    assert location1 <= location2 and location1 <= location1copy


def test_gt(location1: TPLocation, location2: TPLocation) -> None:
    assert location2 > location1


def test_ge(
    location1: TPLocation, location2: TPLocation, location1copy: TPLocation
) -> None:
    assert location2 >= location1 and location1 >= location1copy


def test_no_cmp(location1: TPLocation) -> None:
    with pytest.raises(NotImplementedError):
        assert location1 == object()
