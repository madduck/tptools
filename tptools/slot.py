# needed < 3.14 so that annotations aren't evaluated
from __future__ import annotations

import enum
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

from pydantic_core import CoreSchema, core_schema

if TYPE_CHECKING:
    pass

from pydantic import BaseModel, Field, GetCoreSchemaHandler, model_serializer

from .mixins import ComparableMixin, ReprMixin, StrMixin
from .sqlmodels import Entry


class SlotContent(ABC, ReprMixin, StrMixin):
    @abstractmethod
    def __init__(self) -> None:
        super().__init__()

    __repr_fields__ = ()

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        _ = source_type, handler
        return core_schema.no_info_plain_validator_function(
            # lambda instance: str(instance)
            lambda self: self
        )


@dataclass
class Playceholder(SlotContent):
    matchnr: int
    winner: bool

    def _desc(self) -> str:
        return ("Winner" if self.winner else "Loser") + f" of match #{self.matchnr}"

    __str_template__ = "{self._desc()}"
    __repr_fields__ = ("matchnr", "winner")  # type: ignore[assignment]


class Bye(SlotContent):
    def __init__(self) -> None:
        super().__init__()

    __str_template__ = "Bye"


class Unknown(SlotContent):
    def __init__(self) -> None:
        super().__init__()

    __str_template__ = "Unknown"


class SlotType(enum.Enum):
    UNKNOWN = Unknown
    BYE = Bye
    PLAYCEHOLDER = Playceholder
    ENTRY = Entry

    @classmethod
    def from_class(cls, typecls: type[SlotContent | Entry]) -> SlotType:
        try:
            return cls(typecls)
        except ValueError as err:
            raise ValueError(f"Class {typecls.__name__} is not valid for Slot") from err

    @classmethod
    def from_instance(cls, instance: SlotContent | Entry) -> SlotType:
        return cls.from_class(instance.__class__)

    @property
    def value(self) -> str:
        return str(super().value.__name__)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.value})"


class Slot(ComparableMixin, ReprMixin, StrMixin, BaseModel):
    # The reason why we're using a separate class to wrap SlotContent
    # is because Entry is both an SQLModel and a SlotContent, and
    # if SlotContent was also a BaseModel, there wouldn't be a
    # consistent MRO on the base classes.
    content: Entry | SlotContent = Field(default_factory=Unknown)

    @property
    def type(self) -> SlotType:
        return SlotType.from_instance(self.content)

    @property
    def name(self) -> str:
        return str(self.content)

    @property
    def is_ready(self) -> bool:
        return self.type in (SlotType.ENTRY, SlotType.BYE)

    @property
    def id(self) -> int | None:
        return getattr(self.content, "id", None)

    __str_template__ = "{self.name}"
    __repr_fields__ = ("content",)

    @model_serializer(mode="plain")
    def _model_serializer(self) -> Entry | str:
        if self.type == SlotType.ENTRY:
            return cast(Entry, self.content)
        else:
            return self.name

    if TYPE_CHECKING:
        # Ensure type checkers see the correct return type
        def model_dump(self, **_: Any) -> Entry | str: ...  # type: ignore[override]
