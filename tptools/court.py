from .basemodel import BaseModel
from .paramsmodel import ParamsModel
from .sqlmodels import TPCourt, TPLocation


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

    def _add_location_if_exists(self) -> str:
        return f" ({self.location})" if self.location else ""

    __str_template__ = "{self.name}{self._add_location_if_exists()}"
    __repr_fields__ = ("id", "name", "sortorder?", "location?.name")
    __eq_fields__ = ("sortorder", "name", "location")


class CourtSelectionParams(ParamsModel):
    court: int | None = None
    only_this_court: bool = False
