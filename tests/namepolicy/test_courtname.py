import pytest

from tptools.court import Court
from tptools.namepolicy import CourtNamePolicy


@pytest.fixture
def policy() -> CourtNamePolicy:
    return CourtNamePolicy()


def test_constructor(policy: CourtNamePolicy) -> None:
    _ = policy


def test_passthrough(policy: CourtNamePolicy, court1: Court) -> None:
    assert policy(court1) == "C01"


def test_no_court(policy: CourtNamePolicy) -> None:
    assert policy(None) is None


def test_no_court_string() -> None:
    policy = CourtNamePolicy(no_court_string="No court")
    assert policy(None) == "No court"


def test_court_with_location(policy: CourtNamePolicy, court1: Court) -> None:
    policy = policy.with_(include_location=True)
    assert policy(court1) == "C01 (Sports4You)"
