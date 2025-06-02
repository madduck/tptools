from typing import Any

from pydantic import SerializerFunctionWrapHandler, model_serializer
from sqlalchemy import Column, ForeignKey
from sqlmodel import Field, Relationship

from .basemodel import Model


class Event(Model, table=True):
    id: int = Field(primary_key=True)
    name: str
    abbreviation: str | None = None
    gender: int
    stages: list["Stage"] = Relationship(back_populates="event")

    def _repr_name(self) -> str:
        return self.abbreviation if self.abbreviation is not None else self.name

    __str_template__ = "{self.name}"
    __repr_fields__ = ("id", ("name", _repr_name), "gender")
    __eq_fields__ = ("gender", "name", "abbreviation")


class Stage(Model, table=True):
    id: int = Field(primary_key=True)
    name: str
    eventid_: int | None = Field(
        default=None, sa_column=Column("event", ForeignKey("event.id"))
    )
    event: Event = Relationship(back_populates="stages")

    @model_serializer(mode="wrap")
    def recurse(self, nxt: SerializerFunctionWrapHandler) -> dict[str, Any]:
        ret: dict[str, Any] = nxt(self)
        del ret["eventid_"]
        ret["event"] = self.event
        return ret

    __str_template__ = "{self.name}, {self.event}"
    __repr_fields__ = ("id", "name", "event.name")
    __eq_fields__ = ("event", "name")
