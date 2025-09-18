from typing import Any

from pydantic import SerializerFunctionWrapHandler, model_serializer
from sqlmodel import Field

from .basemodel import Model


class Event(Model, table=True):
    id: int = Field(primary_key=True)
    name: str
    abbreviation: str | None = None
    gender: int

    def _repr_name(self) -> str:
        return self.abbreviation if self.abbreviation is not None else self.name

    @model_serializer(mode="wrap")
    def recurse(self, nxt: SerializerFunctionWrapHandler) -> dict[str, Any]:
        ret: dict[str, Any] = nxt(self)
        return ret

    __str_template__ = "{self.name}"
    __repr_fields__ = ("id", ("name", _repr_name), "gender")
    __eq_fields__ = ("gender", "name", "abbreviation")
