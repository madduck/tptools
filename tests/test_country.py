import pytest

from tptools.sqlmodels import TPCountry


@pytest.fixture
def tpcountry1() -> TPCountry:
    return TPCountry(id=1, name="Holland", code="NL")


@pytest.fixture
def tpcountry2() -> TPCountry:
    return TPCountry(id=2, name="Deutschland")


tpcountry1copy = tpcountry1


def test_repr(tpcountry1: TPCountry) -> None:
    assert repr(tpcountry1) == "TPCountry(id=1, name='Holland', code='NL')"


def test_str(tpcountry1: TPCountry) -> None:
    assert str(tpcountry1) == "Holland"


def test_repr_no_code(tpcountry2: TPCountry) -> None:
    assert repr(tpcountry2) == "TPCountry(id=2, name='Deutschland')"


def test_eq(tpcountry1: TPCountry, tpcountry1copy: TPCountry) -> None:
    assert tpcountry1 == tpcountry1copy


def test_ne(tpcountry1: TPCountry, tpcountry2: TPCountry) -> None:
    assert tpcountry1 != tpcountry2


def test_lt(tpcountry1: TPCountry, tpcountry2: TPCountry) -> None:
    assert tpcountry2 < tpcountry1


def test_le(
    tpcountry1: TPCountry, tpcountry2: TPCountry, tpcountry1copy: TPCountry
) -> None:
    assert tpcountry2 <= tpcountry1 and tpcountry1 <= tpcountry1copy


def test_gt(tpcountry1: TPCountry, tpcountry2: TPCountry) -> None:
    assert tpcountry1 > tpcountry2


def test_ge(
    tpcountry1: TPCountry, tpcountry2: TPCountry, tpcountry1copy: TPCountry
) -> None:
    assert tpcountry1 >= tpcountry2 and tpcountry1 >= tpcountry1copy


def test_no_cmp(tpcountry1: TPCountry) -> None:
    with pytest.raises(NotImplementedError):
        assert tpcountry1 == object()
