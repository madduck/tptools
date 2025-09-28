import pytest

from tptools.namepolicy import ClubNamePolicy
from tptools.sqlmodels import TPClub


@pytest.fixture
def policy() -> ClubNamePolicy:
    return ClubNamePolicy()


def test_constructor(policy: ClubNamePolicy) -> None:
    _ = policy


def test_passthrough(policy: ClubNamePolicy, tpclub1: TPClub) -> None:
    assert policy(tpclub1) == "RSC"


def test_no_club(policy: ClubNamePolicy) -> None:
    _ = policy(None)
