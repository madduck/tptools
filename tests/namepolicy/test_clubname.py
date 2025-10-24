import pytest

from tptools.entry import Club
from tptools.namepolicy import ClubNamePolicy
from tptools.namepolicy.policybase import RegexpSubstTuple


@pytest.fixture
def policy() -> ClubNamePolicy:
    return ClubNamePolicy()


def test_constructor(policy: ClubNamePolicy) -> None:
    _ = policy


def test_passthrough(policy: ClubNamePolicy, club1: Club) -> None:
    assert policy(club1) == "RSC"


def test_no_club(policy: ClubNamePolicy) -> None:
    _ = policy(None)


def test_regexp_empties_means_none(policy: ClubNamePolicy, club1: Club) -> None:
    regexp = RegexpSubstTuple(club1.name, "")
    policy = policy.with_(regexps=[regexp])
    assert policy(club1) is None
