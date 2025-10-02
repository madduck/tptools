from tptools.sqlmodels import TPDraw, TPEvent, TPStage

from .basemodel import BaseModel
from .drawtype import DrawType


class Event(BaseModel[TPEvent]):
    id: int
    name: str
    abbreviation: str | None = None
    gender: int

    def _repr_name(self) -> str:
        return self.abbreviation if self.abbreviation is not None else self.name

    __str_template__ = "{self.name}"
    __repr_fields__ = ("id", ("name", _repr_name), "gender")
    __eq_fields__ = ("gender", "name", "abbreviation")


class Stage(BaseModel[TPStage]):
    id: int
    name: str
    event: Event

    __str_template__ = "{self.name}, {self.event}"
    __repr_fields__ = ("id", "name", "event.name")
    __eq_fields__ = ("event", "name")


class Draw(BaseModel[TPDraw]):
    id: int
    name: str
    type: DrawType
    size: int
    stage: Stage

    def _type_repr(self) -> str:
        return self.type.name

    __str_template__ = "{self.name}, {self.stage}"
    __repr_fields__ = (
        "id",
        "name",
        "stage.name",
        ("type", _type_repr, False),
        "size",
    )
    __eq_fields__ = ("stage", "name", "type", "size")


class InvalidDrawType(ValueError):
    def __init__(self, drawtypeid: int) -> None:
        super().__init__(f"Unable to handle draw type with ID {drawtypeid}")
