import pytest

from tptools.sqlmodels import TPCountry


@pytest.fixture
def country1() -> TPCountry:
    return TPCountry(id=1, name="Holland", code="NL")


@pytest.fixture
def country2() -> TPCountry:
    return TPCountry(id=2, name="Deutschland")


country1copy = country1


def test_repr(country1: TPCountry) -> None:
    assert repr(country1) == "TPCountry(id=1, name='Holland', code='NL')"


def test_str(country1: TPCountry) -> None:
    assert str(country1) == "Holland"


def test_repr_no_code(country2: TPCountry) -> None:
    assert repr(country2) == "TPCountry(id=2, name='Deutschland')"


def test_eq(country1: TPCountry, country1copy: TPCountry) -> None:
    assert country1 == country1copy


def test_ne(country1: TPCountry, country2: TPCountry) -> None:
    assert country1 != country2


def test_lt(country1: TPCountry, country2: TPCountry) -> None:
    assert country2 < country1


def test_le(country1: TPCountry, country2: TPCountry, country1copy: TPCountry) -> None:
    assert country2 <= country1 and country1 <= country1copy


def test_gt(country1: TPCountry, country2: TPCountry) -> None:
    assert country1 > country2


def test_ge(country1: TPCountry, country2: TPCountry, country1copy: TPCountry) -> None:
    assert country1 >= country2 and country1 >= country1copy


def test_no_cmp(country1: TPCountry) -> None:
    with pytest.raises(NotImplementedError):
        assert country1 == object()
