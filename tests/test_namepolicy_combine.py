import dataclasses

import pytest

from tptools.namepolicy import PairCombinePolicy


@pytest.fixture
def policy() -> PairCombinePolicy:
    return PairCombinePolicy()


NAME1 = "one"
NAME2 = "two"


def test_combine(policy: PairCombinePolicy) -> None:
    assert policy(NAME1, NAME2) == f"{NAME1}&{NAME2}"


@pytest.mark.parametrize("teamjoinstr", ["", "+"])
def test_joinstr(teamjoinstr: str, policy: PairCombinePolicy) -> None:
    policy = dataclasses.replace(policy, teamjoinstr=teamjoinstr)
    assert policy(NAME1, NAME2) == f"{NAME1}{teamjoinstr}{NAME2}"


def test_joinstr_none() -> None:
    with pytest.raises(ValueError, match="None is not a valid joinstr"):
        _ = PairCombinePolicy(teamjoinstr=None)  # type: ignore[arg-type]


def test_one_only(policy: PairCombinePolicy) -> None:
    assert policy(NAME1, None) == f"{NAME1}"


def test_first_is_none(policy: PairCombinePolicy) -> None:
    with pytest.raises(ValueError, match="First in pair cannot be None"):
        _ = policy(None, NAME2)  # type: ignore


def test_first_is_none_allowed(policy: PairCombinePolicy) -> None:
    assert policy(None, NAME2, first_can_be_none=True) == NAME2


def test_identical(policy: PairCombinePolicy) -> None:
    assert policy(NAME1, NAME1) == NAME1


def test_identical_merge_disabled(policy: PairCombinePolicy) -> None:
    policy = dataclasses.replace(policy, merge_identical=False)
    assert policy(NAME1, NAME1) == f"{NAME1}&{NAME1}"
