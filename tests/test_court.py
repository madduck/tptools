from tptools import Court
from tptools.match import Match


def test_repr(court1: Court) -> None:
    assert repr(court1) == "Court(id=1, name='C01', location.name='Sports4You')"


def test_str(court1: Court) -> None:
    assert str(court1) == "C01 (Sports4You)"


def test_cmp_eq(court1: Court, court1copy: Court) -> None:
    assert court1 == court1copy


def test_cmp_ne(court1: Court, court2: Court) -> None:
    assert court1 != court2


def test_cmp_lt(court1: Court, court2: Court) -> None:
    assert court1 < court2


def test_cmp_le(court1: Court, court1copy: Court, court2: Court) -> None:
    assert court1 < court2 and court1 <= court1copy


def test_cmp_gt(court1: Court, court2: Court) -> None:
    assert court2 > court1


def test_cmp_ge(court1: Court, court1copy: Court, court2: Court) -> None:
    assert court2 > court1 and court1 >= court1copy


def test_court1_has_no_match(court1: Court) -> None:
    assert court1.current_match is None


def test_court2_has_match(court2: Court, match1: Match) -> None:
    assert court2.current_match is match1
