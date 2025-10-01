from datetime import datetime
from enum import StrEnum, auto
from functools import partial
from typing import Any, ClassVar

from pydantic import SerializerFunctionWrapHandler, model_serializer
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlmodel import Field, Relationship, SQLModel

from .drawtype import DrawType
from .mixins import ComparableMixin, ReprMixin, StrMixin
from .util import EnumAsInteger, normalise_time, reduce_common_prefix, zero_to_none


class TPModel(ReprMixin, StrMixin, ComparableMixin, SQLModel):
    def __setattr__(self, attr: str, value: Any) -> None:
        if hasattr(self, f"{attr}id_") and hasattr(value, "id"):
            object.__setattr__(self, f"{attr}id_", value.id)
        super().__setattr__(attr, value)

    @model_serializer(mode="wrap")
    def replace_id_fields_with_model_instances(
        self, handler: SerializerFunctionWrapHandler
    ) -> dict[str, Any]:
        ret: dict[str, Any] = handler(self)
        for key in [k for k in ret.keys() if k.endswith("id_")]:
            if hasattr(self, mkey := key[:-3]):
                del ret[key]
                ret[mkey] = getattr(self, mkey)
        return ret


class TPSetting(TPModel, table=True):
    # ClassVar as per https://github.com/fastapi/sqlmodel/issues/98#issuecomment-3247459451
    __tablename__: ClassVar[Any] = "Settings"

    id: int = Field(primary_key=True)
    name: str
    value: str | None

    __repr_fields__ = ("id", "name", "value")
    __str_template__ = "{self.name}={repr(self.value)}"
    __eq_fields__ = ("name", "value")


class TPEvent(TPModel, table=True):
    # ClassVar as per https://github.com/fastapi/sqlmodel/issues/98#issuecomment-3247459451
    __tablename__: ClassVar[Any] = "Event"

    id: int = Field(primary_key=True)
    name: str
    abbreviation: str | None = None
    gender: int
    stages: list["TPStage"] = Relationship(back_populates="event")
    entries: list["TPEntry"] = Relationship(back_populates="event")

    def _repr_name(self) -> str:
        return self.abbreviation if self.abbreviation is not None else self.name

    __str_template__ = "{self.name}"
    __repr_fields__ = ("id", ("name", _repr_name), "gender")
    __eq_fields__ = ("gender", "name", "abbreviation")


class TPStage(TPModel, table=True):
    # ClassVar as per https://github.com/fastapi/sqlmodel/issues/98#issuecomment-3247459451
    __tablename__: ClassVar[Any] = "Stage"

    id: int = Field(primary_key=True)
    name: str
    eventid_: int | None = Field(
        default=None, sa_column=Column("event", ForeignKey("Event.id"))
    )
    event: TPEvent = Relationship(back_populates="stages")
    draws: list["TPDraw"] = Relationship(back_populates="stage")

    __str_template__ = "{self.name}, {self.event}"
    __repr_fields__ = ("id", "name", "event.name")
    __eq_fields__ = ("event", "name")


class TPDraw(TPModel, table=True):
    # ClassVar as per https://github.com/fastapi/sqlmodel/issues/98#issuecomment-3247459451
    __tablename__: ClassVar[Any] = "Draw"

    id: int = Field(primary_key=True)
    name: str
    type: DrawType = Field(sa_column=Column("drawtype", EnumAsInteger(DrawType)))
    size: int = Field(sa_column=Column("drawsize"))
    stageid_: int | None = Field(
        default=None, sa_column=Column("stage", ForeignKey("Stage.id"))
    )
    stage: TPStage = Relationship(back_populates="draws")
    playermatches: list["TPPlayerMatch"] = Relationship(back_populates="draw")

    def _type_repr(self) -> str:
        return self.type.name

    __str_template__ = "{self.name}, {self.stage}"
    __repr_fields__ = ("id", "name", "stage.name", ("type", _type_repr, False), "size")
    __eq_fields__ = ("stage", "name", "type", "size")


class TPClub(TPModel, table=True):
    # ClassVar as per https://github.com/fastapi/sqlmodel/issues/98#issuecomment-3247459451
    __tablename__: ClassVar[Any] = "Club"

    id: int = Field(primary_key=True)
    name: str
    players: list["TPPlayer"] = Relationship(back_populates="club")

    __str_template__ = "{self.name}"
    __repr_fields__ = ("id", "name")
    __eq_fields__ = ("name",)
    __none_sorts_last__ = True


class TPCountry(TPModel, table=True):
    # ClassVar as per https://github.com/fastapi/sqlmodel/issues/98#issuecomment-3247459451
    __tablename__: ClassVar[Any] = "Country"

    id: int = Field(primary_key=True)
    name: str
    code: str | None = None
    players: list["TPPlayer"] = Relationship(back_populates="country")

    __str_template__ = "{self.name}"
    __repr_fields__ = ("id", "name", "code?")
    __eq_fields__ = ("name", "code")
    __none_sorts_last__ = True


class TPPlayer(TPModel, table=True):
    # ClassVar as per https://github.com/fastapi/sqlmodel/issues/98#issuecomment-3247459451
    __tablename__: ClassVar[Any] = "Player"

    id: int = Field(primary_key=True)
    lastname: str = Field(sa_column=Column("name", String))
    firstname: str

    @property
    def name(self) -> str:
        return f"{self.firstname} {self.lastname}".strip()

    clubid_: int | None = Field(
        default=None, sa_column=Column("club", Integer, ForeignKey("Club.id"))
    )
    club: TPClub = Relationship(back_populates="players")
    countryid_: int | None = Field(
        default=None, sa_column=Column("country", Integer, ForeignKey("Country.id"))
    )
    country: TPCountry = Relationship(back_populates="players")
    entries: list["TPEntry"] = Relationship(
        sa_relationship_kwargs={
            "primaryjoin": (
                "or_(TPPlayer.id==TPEntry.player1id_,TPPlayer.id==TPEntry.player2id_)"
            ),
            "viewonly": True,
        }
    )

    __str_template__ = (
        "{self.name} "
        "({self.club if self.club else 'no club'}"
        "{', ' + str(self.country) if self.country else ''})"
    )
    __repr_fields__ = ("id", "lastname", "firstname", "country?.name", "club?.name")
    __eq_fields__ = ("lastname", "firstname", "club", "country")
    __none_sorts_last__ = True


class TPEntry(TPModel, table=True):
    # ClassVar as per https://github.com/fastapi/sqlmodel/issues/98#issuecomment-3247459451
    __tablename__: ClassVar[Any] = "Entry"

    id: int = Field(primary_key=True)
    eventid_: int = Field(sa_column=Column("event", ForeignKey("Event.id")))
    event: TPEvent = Relationship(back_populates="entries")
    player1id_: int | None = Field(
        default=None, sa_column=Column("player1", ForeignKey("Player.id"))
    )
    player1: TPPlayer = Relationship(
        sa_relationship_kwargs={
            "foreign_keys": "TPEntry.player1id_",
            "primaryjoin": "TPEntry.player1id_ == TPPlayer.id",
        }
    )
    player2id_: int | None = Field(
        default=None, sa_column=Column("player2", ForeignKey("Player.id"))
    )
    player2: TPPlayer | None = Relationship(
        sa_relationship_kwargs={
            "foreign_keys": "TPEntry.player2id_",
            "primaryjoin": "TPEntry.player2id_ == TPPlayer.id",
        }
    )
    playermatches: list["TPPlayerMatch"] = Relationship(back_populates="entry")

    @property
    def players(self) -> tuple[TPPlayer, TPPlayer | None]:
        return self.player1, self.player2

    @property
    def name(self) -> str:
        return "&".join(p.name for p in self.players if p)

    def __init__(
        self,
        *,
        event: TPEvent,
        player1: TPPlayer,
        player2: TPPlayer | None = None,
        **kwargs: Any,
    ) -> None:
        if player1 == player2:
            raise ValueError(f"player2 cannot be the same as player1: {player1}")
        kwargs |= {"event": event, "player1": player1, "player2": player2}
        super().__init__(**kwargs)

    __str_template__ = "{self.name}"
    __repr_fields__ = [
        "id",
        "event.name",
        "player1.name",
        "player2?.name",
    ]
    __eq_fields__ = ["event", "player1", "player2"]


class TPLocation(TPModel, table=True):
    # ClassVar as per https://github.com/fastapi/sqlmodel/issues/98#issuecomment-3247459451
    __tablename__: ClassVar[Any] = "Location"

    id: int = Field(primary_key=True)
    name: str
    courts: list["TPCourt"] = Relationship(back_populates="location")

    __str_template__ = "{self.name}"
    __repr_fields__ = ("id", "name", "numcourts")
    __eq_fields__ = ("name",)

    @property
    def numcourts(self) -> int:
        return len(self.courts)


class TPCourt(TPModel, table=True):
    # ClassVar as per https://github.com/fastapi/sqlmodel/issues/98#issuecomment-3247459451
    __tablename__: ClassVar[Any] = "Court"

    id: int = Field(primary_key=True)
    name: str
    locationid_: int | None = Field(
        default=None, sa_column=Column("location", ForeignKey("Location.id"))
    )
    location: TPLocation = Relationship(back_populates="courts")
    sortorder: int | None = None
    playermatches: list["TPPlayerMatch"] = Relationship(back_populates="court")

    __str_template__ = "{self.location}, {self.name}"
    __repr_fields__ = ("id", "name", "location?.name", "sortorder?")
    __eq_fields__ = ("location", "sortorder", "name")


class TPPlayerMatch(TPModel, table=True):
    # ClassVar as per https://github.com/fastapi/sqlmodel/issues/98#issuecomment-3247459451
    __tablename__: ClassVar[Any] = "PlayerMatch"

    class Status(StrEnum):
        BYE = auto()
        PLAYER = auto()
        PENDING = auto()
        PLAYED = auto()
        NOTPLAYED = auto()

        @property
        def is_player(self) -> bool:
            return self in (self.BYE.value, self.PLAYER.value)

        @property
        def is_match(self) -> bool:
            return not self.is_player

    id: int = Field(primary_key=True)
    drawid_: int = Field(sa_column=Column("draw", ForeignKey("Draw.id")))
    draw: TPDraw = Relationship(back_populates="playermatches")
    matchnr: int
    entryid_: int | None = Field(
        default=None, sa_column=Column("entry", ForeignKey("Entry.id"))
    )
    entry: TPEntry | None = Relationship(back_populates="playermatches")
    time: datetime | None = Field(default=None, sa_column=Column("plandate", DateTime))
    courtid_: int | None = Field(
        default=None, sa_column=Column("court", ForeignKey("Court.id"))
    )
    court: TPCourt | None = Relationship(back_populates="playermatches")
    winner: int | None = None
    planning: int
    van1: int | None = None
    van2: int | None = None
    # wn/wn need to differentiate between 0 and None, unlike e.g. winner and van1/2,
    # where we want the data to be normalised (0 → None). But wn/vn seems like the only
    # way in a group draw to distinguish whether a match is played or notplayed.
    wn: int | None = None
    vn: int | None = None
    reversehomeaway: bool = False

    @property
    def van(self) -> tuple[int, int] | tuple[None, None]:
        van1 = zero_to_none(self.van1)
        van2 = zero_to_none(self.van2)

        match (van1, van2, self.reversehomeaway):
            case (None, None, _):
                return None, None
            case (int(_), int(_), False):
                return van1, van2
            case (int(_), int(_), True):
                return van2, van1

        raise AssertionError("van{1,2} inconsistent")

    @property
    def scheduled(self) -> bool:
        return (
            normalise_time(self.time, nodate_value=datetime(1899, 12, 30)) is not None
        )

    @property
    def status(self) -> Status:
        try:
            if self.van[0] is None:
                if self.entry is None:
                    return self.Status.BYE
                else:
                    return self.Status.PLAYER

            else:
                winner = zero_to_none(self.winner)
                if self.draw.type == DrawType.GROUP:
                    if winner is not None:
                        return self.Status.PLAYED

                    elif self.wn == 0 and self.vn == 0:
                        return self.Status.NOTPLAYED

                    else:
                        return self.Status.PENDING

                elif winner is None:
                    return self.Status.PENDING

                elif self.entry is None:
                    return self.Status.NOTPLAYED

                else:
                    return self.Status.PLAYED

        except AssertionError as err:
            raise RuntimeError(f"{self} has an invalid status: {str(err)}") from err

    def _status_repr(self) -> str:
        return self.status.name.lower()

    def _time_repr(self) -> str:
        return repr(self.time).replace("datetime.", "")

    def _ll_repr(self, attr1: str, attr2: str) -> str | None:
        return reduce_common_prefix(
            str(a) if (a := getattr(self, attr1, None)) is not None else None,
            str(b) if (b := getattr(self, attr2, None)) is not None else None,
        )

    def _van_repr(self) -> str | None:
        return reduce_common_prefix(*map(str, self.van))

    __str_template__ = (
        "{self.id}: [{self.draw.name}:{self.matchnr}] "
        "[{self._van_repr()} → "
        "{self.planning} → "
        "{self._ll_repr('wn', 'vn')}] "
        "'{self.entry}' ({self._status_repr()})"
    )

    __repr_fields__ = (
        "id",
        "draw.name",
        "matchnr",
        "entry?.players",
        ("time", _time_repr, False),
        "court?.name",
        "winner",
        "planning",
        ("van", _van_repr, False),
        ("wnvn", partial(_ll_repr, attr1="wn", attr2="vn"), False),
        ("status", _status_repr, False),
    )

    __eq_fields__ = (
        "draw",
        "matchnr",
        "entry",
        "time",
        "court",
        "winner",
        "planning",
    )
    __cmp_fields__ = (
        "draw",
        "matchnr",
        "time",
        "court",
        "id",
    )
    __none_sorts_last__ = True

    __massage_fields__ = {
        "van1": zero_to_none,
        "van2": zero_to_none,
        "winner": zero_to_none,
        "time": partial(normalise_time, nodate_value=datetime(1899, 12, 30)),
    }
