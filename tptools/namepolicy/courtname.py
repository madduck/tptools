# needed < 3.14 so that annotations aren't evaluated
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..paramsmodel import ParamsModel
from .policybase import PolicyBase

if TYPE_CHECKING:
    from ..court import Court


class CourtNamePolicyParams(ParamsModel):
    include_location: bool = False
    no_court_string: str = "No court"


# TODO: remove redundancy between these two classes
# It currently seems impossible to do so:
# - https://github.com/pydantic/pydantic/discussions/12204
# - https://discuss.python.org/t/dataclasses-asdicttype-type/103448/2


@dataclass(frozen=True)
class CourtNamePolicy(PolicyBase):
    include_location: bool = False
    no_court_string: str = "No court"

    def __call__(self, court: Court | None) -> str:
        if court is None:
            return self.no_court_string

        ret = court.name
        if self.include_location and court.location:
            ret += f" ({court.location})"
        return ret
