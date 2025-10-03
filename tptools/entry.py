import logging

from .basemodel import BaseModel
from .draw import Event
from .sqlmodels import TPClub, TPCountry, TPEntry, TPPlayer

logger = logging.getLogger(__name__)


class Club(BaseModel[TPClub]):
    id: int
    name: str

    __repr_fields__ = ("name",)
    __str_template__ = "{self.name}"
    __eq_fields__ = ("name",)


class Country(BaseModel[TPCountry]):
    id: int
    name: str
    code: str | None

    __repr_fields__ = ("name", "code")
    __str_template__ = "{self.name}"
    __eq_fields__ = ("name", "code")


class Player(BaseModel[TPPlayer]):
    id: int
    lastname: str
    firstname: str
    club: Club | None
    country: Country | None

    @property
    def name(self) -> str:
        return f"{self.firstname} {self.lastname}"

    __repr_fields__ = ("name", "club", "country")
    __str_template__ = "{self.name} ({self.club}, {self.country})"
    __eq_fields__ = ("name", "club", "country")


class Entry(BaseModel[TPEntry]):
    id: int
    event: Event
    player1: Player
    player2: Player | None

    __repr_fields__ = ("event.name", "player1.name", "player2?.name")
    __str_template__ = "{self.player1}{'&'+str(self.player2) if self.player2 else ''}"
    __eq_fields__ = ("event", "player1", "player2")
