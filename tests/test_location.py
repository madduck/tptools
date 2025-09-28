import pytest

from tptools.sqlmodels import TPLocation


def test_repr(tplocation1: TPLocation) -> None:
    assert repr(tplocation1) == "TPLocation(id=1, name='Sports4You', numcourts=0)"


def test_str(tplocation1: TPLocation) -> None:
    assert str(tplocation1) == "Sports4You"


def test_eq(tplocation1: TPLocation, tplocation1copy: TPLocation) -> None:
    assert tplocation1 == tplocation1copy


def test_ne(tplocation1: TPLocation, tplocation2: TPLocation) -> None:
    assert tplocation1 != tplocation2


def test_lt(tplocation1: TPLocation, tplocation2: TPLocation) -> None:
    assert tplocation1 < tplocation2


def test_le(
    tplocation1: TPLocation, tplocation2: TPLocation, tplocation1copy: TPLocation
) -> None:
    assert tplocation1 <= tplocation2 and tplocation1 <= tplocation1copy


def test_gt(tplocation1: TPLocation, tplocation2: TPLocation) -> None:
    assert tplocation2 > tplocation1


def test_ge(
    tplocation1: TPLocation, tplocation2: TPLocation, tplocation1copy: TPLocation
) -> None:
    assert tplocation2 >= tplocation1 and tplocation1 >= tplocation1copy


def test_no_cmp(tplocation1: TPLocation) -> None:
    with pytest.raises(NotImplementedError):
        assert tplocation1 == object()
