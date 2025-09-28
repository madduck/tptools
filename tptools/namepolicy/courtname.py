from dataclasses import dataclass

from ..paramsmodel import ParamsModel
from ..sqlmodels import TPCourt
from .policybase import PolicyBase


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

    def __call__(self, court: TPCourt | None) -> str:
        if court is None:
            return self.no_court_string

        ret = court.name
        if self.include_location and court.location:
            ret += f" ({court.location})"
        return ret
