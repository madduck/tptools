import dataclasses

import pytest

from tptools.namepolicy import CourtNamePolicy
from tptools.sqlmodels import TPCourt


@pytest.fixture
def policy() -> CourtNamePolicy:
    return CourtNamePolicy()


def test_constructor(policy: CourtNamePolicy) -> None:
    _ = policy


def test_passthrough(policy: CourtNamePolicy, tpcourt1: TPCourt) -> None:
    assert policy(tpcourt1) == "C01"


def test_no_court(policy: CourtNamePolicy) -> None:
    assert policy(None) == "No court"


def test_court_with_location(policy: CourtNamePolicy, tpcourt1: TPCourt) -> None:
    policy = dataclasses.replace(policy, include_location=True)
    assert policy(tpcourt1) == "C01 (Sports4You)"
