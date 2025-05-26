import pytest

from tptools.models import Club


def test_repr(club1: Club) -> None:
    assert repr(club1) == "Club(id=1, name='RSC')"


def test_str(club1: Club) -> None:
    assert str(club1) == "RSC"


def test_eq(club1: Club, club1copy: Club) -> None:
    assert club1 == club1copy


def test_ne(club1: Club, club2: Club) -> None:
    assert club1 != club2


def test_lt(club1: Club, club2: Club) -> None:
    assert club1 < club2


def test_le(club1: Club, club2: Club, club1copy: Club) -> None:
    assert club1 <= club2 and club1 <= club1copy


def test_gt(club1: Club, club2: Club) -> None:
    assert club2 > club1


def test_ge(club1: Club, club2: Club, club1copy: Club) -> None:
    assert club2 >= club1 and club1 >= club1copy


def test_no_cmp(club1: Club) -> None:
    with pytest.raises(NotImplementedError):
        assert club1 == object()
