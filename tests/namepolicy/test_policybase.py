from dataclasses import dataclass

import pytest

from tptools.namepolicy.policybase import NamePolicy, PolicyBase, RegexpSubstTuple


def test_policybase_is_abstract() -> None:
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        _ = PolicyBase()  # type: ignore[abstract]


@dataclass(frozen=True)
class SomePolicy(NamePolicy):
    one: int = 1
    two: str = "two"

    def __call__(self) -> str:
        return "string"


def test_policybase_params() -> None:
    params = SomePolicy().params()
    assert params["one"] == 1
    assert params["two"] == "two"


def test_regexp_application() -> None:
    rgxp = RegexpSubstTuple(r".", r"x\g<0>")
    assert SomePolicy([rgxp])._apply_regexps("instr") == "xixnxsxtxr"


def test_regexp_application_passthrough() -> None:
    assert SomePolicy()._apply_regexps("instr") == "instr"


def test_regexp_application_multiple() -> None:
    rgxp1 = RegexpSubstTuple(r".", r"x\g<0>")
    rgxp2 = RegexpSubstTuple("^", "start-of-line")

    assert (
        SomePolicy([rgxp1, rgxp2])._apply_regexps("instr") == "start-of-linexixnxsxtxr"
    )
