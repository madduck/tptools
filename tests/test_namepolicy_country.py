import pytest

from tptools.models import Country
from tptools.namepolicy import CountryNamePolicy


@pytest.fixture
def policy() -> CountryNamePolicy:
    return CountryNamePolicy()


def test_constructor(policy: CountryNamePolicy) -> None:
    _ = policy


def test_passthrough(policy: CountryNamePolicy, country1: Country) -> None:
    assert policy(country1) == "Holland"


def test_no_country(policy: CountryNamePolicy) -> None:
    _ = policy(None)
