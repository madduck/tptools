import pytest

from tptools.sqlmodels import Country


@pytest.fixture
def country1() -> Country:
    return Country(id=1, name="Holland", code="NL")


@pytest.fixture
def country2() -> Country:
    return Country(id=2, name="Deutschland")


country1copy = country1


def test_repr(country1: Country) -> None:
    assert repr(country1) == "Country(id=1, name='Holland', code='NL')"


def test_str(country1: Country) -> None:
    assert str(country1) == "Holland"


def test_repr_no_code(country2: Country) -> None:
    assert repr(country2) == "Country(id=2, name='Deutschland')"


def test_eq(country1: Country, country1copy: Country) -> None:
    assert country1 == country1copy


def test_ne(country1: Country, country2: Country) -> None:
    assert country1 != country2


def test_lt(country1: Country, country2: Country) -> None:
    assert country2 < country1


def test_le(country1: Country, country2: Country, country1copy: Country) -> None:
    assert country2 <= country1 and country1 <= country1copy


def test_gt(country1: Country, country2: Country) -> None:
    assert country1 > country2


def test_ge(country1: Country, country2: Country, country1copy: Country) -> None:
    assert country1 >= country2 and country1 >= country1copy


def test_no_cmp(country1: Country) -> None:
    with pytest.raises(NotImplementedError):
        assert country1 == object()
