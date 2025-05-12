import dataclasses

import pytest

from tptools.models import Court
from tptools.namepolicy import CourtNamePolicy


@pytest.fixture
def policy() -> CourtNamePolicy:
    return CourtNamePolicy()


def test_constructor(policy: CourtNamePolicy) -> None:
    _ = policy


def test_passthrough(policy: CourtNamePolicy, court1: Court) -> None:
    assert policy(court1) == "C01"


def test_no_court(policy: CourtNamePolicy) -> None:
    assert policy(None) == "No court"


def test_court_with_location(policy: CourtNamePolicy, court1: Court) -> None:
    policy = dataclasses.replace(policy, include_location=True)
    assert policy(court1) == "C01 (Sports4You)"
