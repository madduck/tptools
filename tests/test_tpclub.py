import pytest

from tptools.sqlmodels import TPClub


def test_repr(tpclub1: TPClub) -> None:
    assert repr(tpclub1) == "TPClub(id=1, name='RSC')"


def test_str(tpclub1: TPClub) -> None:
    assert str(tpclub1) == "RSC"


def test_eq(tpclub1: TPClub, tpclub1copy: TPClub) -> None:
    assert tpclub1 == tpclub1copy


def test_ne(tpclub1: TPClub, tpclub2: TPClub) -> None:
    assert tpclub1 != tpclub2


def test_lt(tpclub1: TPClub, tpclub2: TPClub) -> None:
    assert tpclub1 < tpclub2


def test_le(tpclub1: TPClub, tpclub2: TPClub, tpclub1copy: TPClub) -> None:
    assert tpclub1 <= tpclub2 and tpclub1 <= tpclub1copy


def test_gt(tpclub1: TPClub, tpclub2: TPClub) -> None:
    assert tpclub2 > tpclub1


def test_ge(tpclub1: TPClub, tpclub2: TPClub, tpclub1copy: TPClub) -> None:
    assert tpclub2 >= tpclub1 and tpclub1 >= tpclub1copy


def test_no_cmp(tpclub1: TPClub) -> None:
    with pytest.raises(NotImplementedError):
        assert tpclub1 == object()
