from typing import Any

from pydantic import SerializerFunctionWrapHandler, model_serializer
from sqlalchemy import Column, ForeignKey, Integer, String
from sqlmodel import Field, Relationship

from .basemodel import Model
from .drawtype import DrawType
from .util import EnumAsInteger


class Event(Model, table=True):
    id: int = Field(primary_key=True)
    name: str
    abbreviation: str | None = None
    gender: int
    stages: list["Stage"] = Relationship(back_populates="event")
    entries: list["Entry"] = Relationship(back_populates="event")

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
    draws: list["Draw"] = Relationship(back_populates="stage")

    @model_serializer(mode="wrap")
    def recurse(self, nxt: SerializerFunctionWrapHandler) -> dict[str, Any]:
        ret: dict[str, Any] = nxt(self)
        del ret["eventid_"]
        ret["event"] = self.event
        return ret

    __str_template__ = "{self.name}, {self.event}"
    __repr_fields__ = ("id", "name", "event.name")
    __eq_fields__ = ("event", "name")


class Draw(Model, table=True):
    id: int = Field(primary_key=True)
    name: str
    type: DrawType = Field(sa_column=Column("drawtype", EnumAsInteger(DrawType)))
    size: int = Field(sa_column=Column("drawsize"))
    stageid_: int | None = Field(
        default=None, sa_column=Column("stage", ForeignKey("stage.id"))
    )
    stage: Stage = Relationship(back_populates="draws")

    @model_serializer(mode="wrap")
    def recurse(self, nxt: SerializerFunctionWrapHandler) -> dict[str, Any]:
        ret: dict[str, Any] = nxt(self)
        del ret["stageid_"]
        ret["stage"] = self.stage
        return ret

    def _type_repr(self) -> str:
        return self.type.name

    __str_template__ = "{self.name}, {self.stage}"
    __repr_fields__ = ("id", "name", "stage.name", ("type", _type_repr, False), "size")
    __eq_fields__ = ("stage", "name", "type", "size")


class Club(Model, table=True):
    id: int = Field(primary_key=True)
    name: str
    players: list["Player"] = Relationship(back_populates="club")

    __str_template__ = "{self.name}"
    __repr_fields__ = ("id", "name")
    __eq_fields__ = ("name",)
    __none_sorts_last__ = True


class Country(Model, table=True):
    id: int = Field(primary_key=True)
    name: str
    code: str | None = None
    players: list["Player"] = Relationship(back_populates="country")

    __str_template__ = "{self.name}"
    __repr_fields__ = ("id", "name", "code?")
    __eq_fields__ = ("name", "code")
    __none_sorts_last__ = True


class Player(Model, table=True):
    id: int = Field(primary_key=True)
    lastname: str = Field(sa_column=Column("name", String))
    firstname: str

    @property
    def name(self) -> str:
        return f"{self.firstname} {self.lastname}".strip()

    clubid_: int | None = Field(
        default=None, sa_column=Column("club", Integer, ForeignKey("club.id"))
    )
    club: Club = Relationship(back_populates="players")
    countryid_: int | None = Field(
        default=None, sa_column=Column("country", Integer, ForeignKey("country.id"))
    )
    country: Country = Relationship(back_populates="players")
    entries: list["Entry"] = Relationship(
        sa_relationship_kwargs={
            "primaryjoin": (
                "or_(Player.id==Entry.player1id_,Player.id==Entry.player2id_)"
            ),
            "viewonly": True,
        }
    )

    @model_serializer(mode="wrap")
    def recurse(self, nxt: SerializerFunctionWrapHandler) -> dict[str, Any]:
        ret: dict[str, Any] = nxt(self)
        del ret["clubid_"]
        ret["club"] = self.club
        del ret["countryid_"]
        ret["country"] = self.country
        return ret

    __str_template__ = (
        "{self.name} "
        "({self.club if self.club else 'no club'}"
        "{', ' + str(self.country) if self.country else ''})"
    )
    __repr_fields__ = ("id", "lastname", "firstname", "country?.name", "club?.name")
    __eq_fields__ = ("lastname", "firstname", "club", "country")
    __none_sorts_last__ = True


class Entry(Model, table=True):
    id: int = Field(primary_key=True)
    eventid_: int = Field(sa_column=Column("event", ForeignKey("event.id")))
    event: Event = Relationship(back_populates="entries")
    player1id_: int | None = Field(
        default=None, sa_column=Column("player1", ForeignKey("player.id"))
    )
    player1: Player = Relationship(
        sa_relationship_kwargs={
            "foreign_keys": "Entry.player1id_",
            "primaryjoin": "Entry.player1id_ == Player.id",
        }
    )
    player2id_: int | None = Field(
        default=None, sa_column=Column("player2", ForeignKey("player.id"))
    )
    player2: Player | None = Relationship(
        sa_relationship_kwargs={
            "foreign_keys": "Entry.player2id_",
            "primaryjoin": "Entry.player2id_ == Player.id",
        }
    )

    @model_serializer(mode="wrap")
    def recurse(self, nxt: SerializerFunctionWrapHandler) -> dict[str, Any]:
        ret: dict[str, Any] = nxt(self)
        for f in ("player1", "player2", "event"):
            del ret[f"{f}id_"]
            ret[f] = getattr(self, f)
        return ret

    @property
    def players(self) -> tuple[Player, Player | None]:
        return self.player1, self.player2

    @property
    def name(self) -> str:
        return "&".join(p.name for p in self.players if p)

    def __init__(
        self,
        player1: Player,
        player2: Player | None = None,
        **kwargs: Any,
    ) -> None:
        if player1 == player2:
            raise ValueError(f"player2 cannot be the same as player1: {player1}")
        kwargs |= {"player1": player1, "player2": player2}
        super().__init__(**kwargs)

    __str_template__ = "{self.name}"
    __repr_fields__ = [
        "id",
        "event.name",
        "player1.name",
        "player2?.name",
    ]
    __eq_fields__ = ["event", "player1", "player2"]
