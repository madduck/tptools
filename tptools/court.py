from .basemodel import BaseModel
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
    location: Location | None

    __str_template__ = "{self.name} ({self.location})"
    __repr_fields__ = ("id", "name", "sortorder?", "location?.name")
    __eq_fields__ = ("sortorder", "name", "location")
