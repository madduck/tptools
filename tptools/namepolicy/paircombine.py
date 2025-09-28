from dataclasses import KW_ONLY, dataclass
from typing import Literal, overload

from ..paramsmodel import ParamsModel
from .policybase import PolicyBase


class PairCombinePolicyParams(ParamsModel):
    teamjoinstr: str = "&"
    merge_identical: bool = True


# TODO: remove redundancy between these two classes.
# It currently seems impossible to do so:
# - https://github.com/pydantic/pydantic/discussions/12204
# - https://discuss.python.org/t/dataclasses-asdicttype-type/103448/2


@dataclass(frozen=True)
class PairCombinePolicy(PolicyBase):
    _: KW_ONLY
    teamjoinstr: str = "&"
    merge_identical: bool = True

    def __post_init__(self) -> None:
        if self.teamjoinstr is None:
            raise ValueError("None is not a valid joinstr")

    @overload
    def __call__(
        self, a: str, b: str | None, *, first_can_be_none: Literal[False] = False
    ) -> str: ...

    @overload
    def __call__(
        self, a: str | None, b: str | None, *, first_can_be_none: Literal[True]
    ) -> str | None: ...

    def __call__(self, a, b, *, first_can_be_none=False):  # type: ignore[no-untyped-def]
        if a is None and not first_can_be_none:
            raise ValueError("First in pair cannot be None")

        if self.merge_identical and a == b:
            return a

        return self.teamjoinstr.join(filter(None, (a, b))) or None
