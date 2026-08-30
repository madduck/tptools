from typing import TYPE_CHECKING

from .basemodel import BaseModel
from .paramsmodel import ParamsModel
from .sqlmodels import TPCourt, TPLocation

if TYPE_CHECKING:
    from .match import Match


class Location(BaseModel[TPLocation]):
    id: int
    name: str

    __str_template__ = "{self.name}"
    __repr_fields__ = ("id", "name")
    __eq_fields__ = ("name",)


class Court(BaseModel[TPCourt]):
    id: int
    name: str
    sortorder: int | None = None
    location: Location | None = None
    current_match: "Match | None" = None

    def _add_location_if_exists(self) -> str:
        return f" ({self.location})" if self.location else ""

    def _current_match_id(self) -> str | None:
        return self.current_match.id if self.current_match is not None else None

    __str_template__ = "{self.name}{self._add_location_if_exists()}"
    __repr_fields__ = (
        "id",
        "name",
        "sortorder?",
        "location?.name",
        ("match_on?", _current_match_id, True),
    )
    __eq_fields__ = ("sortorder", "name", "location")


class CourtSelectionParams(ParamsModel):
    court: int | None = None
    only_this_court: bool = False
