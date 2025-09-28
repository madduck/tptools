import pytest

from tptools.namepolicy import CountryNamePolicy
from tptools.sqlmodels import TPCountry


@pytest.fixture
def policy() -> CountryNamePolicy:
    return CountryNamePolicy()


def test_constructor(policy: CountryNamePolicy) -> None:
    _ = policy


def test_passthrough(policy: CountryNamePolicy, tpcountry1: TPCountry) -> None:
    assert policy(tpcountry1) == "Holland"


def test_no_country(policy: CountryNamePolicy) -> None:
    _ = policy(None)
