import pytest

from tptools.sqlmodels import TPClub


def test_repr(club1: TPClub) -> None:
    assert repr(club1) == "TPClub(id=1, name='RSC')"


def test_str(club1: TPClub) -> None:
    assert str(club1) == "RSC"


def test_eq(club1: TPClub, club1copy: TPClub) -> None:
    assert club1 == club1copy


def test_ne(club1: TPClub, club2: TPClub) -> None:
    assert club1 != club2


def test_lt(club1: TPClub, club2: TPClub) -> None:
    assert club1 < club2


def test_le(club1: TPClub, club2: TPClub, club1copy: TPClub) -> None:
    assert club1 <= club2 and club1 <= club1copy


def test_gt(club1: TPClub, club2: TPClub) -> None:
    assert club2 > club1


def test_ge(club1: TPClub, club2: TPClub, club1copy: TPClub) -> None:
    assert club2 >= club1 and club1 >= club1copy


def test_no_cmp(club1: TPClub) -> None:
    with pytest.raises(NotImplementedError):
        assert club1 == object()
