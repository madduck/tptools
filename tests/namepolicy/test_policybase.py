from dataclasses import dataclass

import pytest

from tptools.namepolicy.policybase import PolicyBase


def test_policybase_is_abstract() -> None:
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        _ = PolicyBase()  # type: ignore[abstract]


@dataclass(frozen=True)
class SomePolicy(PolicyBase):
    one: int = 1
    two: str = "two"

    def __call__(self) -> str:
        return "string"


def test_policybase_params() -> None:
    params = SomePolicy().params()
    assert params["one"] == 1
    assert params["two"] == "two"
