import logging
from typing import NotRequired, TypedDict

from pydantic import TypeAdapter

from .basemodel import BaseModel
from .draw import Event
from .namepolicy import (
    ClubNamePolicy,
    CountryNamePolicy,
    PairCombinePolicy,
    PlayerNamePolicy,
)
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
    firstname: str
    lastname: str | None = None
    club: Club | None = None
    country: Country | None = None

    @property
    def name(self) -> str:
        if self.lastname:
            return f"{self.firstname} {self.lastname}"
        else:
            return self.firstname

    __repr_fields__ = ("name", "club", "country")
    __str_template__ = "{self.name} ({self.club}, {self.country})"
    __eq_fields__ = ("name", "club", "country")


class PlayerExportStruct(TypedDict):
    name: str
    club: NotRequired[str | None]
    country: NotRequired[str | None]


PlayerExportStructValidator = TypeAdapter(PlayerExportStruct)


class Entry(BaseModel[TPEntry]):
    id: int
    event: Event
    player1: Player
    player2: Player | None = None

    def make_player_export_struct(
        self,
        clubnamepolicy: ClubNamePolicy | None = None,
        countrynamepolicy: CountryNamePolicy | None = None,
        playernamepolicy: PlayerNamePolicy | None = None,
        paircombinepolicy: PairCombinePolicy | None = None,
    ) -> PlayerExportStruct:
        clubnamepolicy = clubnamepolicy or ClubNamePolicy()
        countrynamepolicy = countrynamepolicy or CountryNamePolicy()
        playernamepolicy = playernamepolicy or PlayerNamePolicy()
        paircombinepolicy = paircombinepolicy or PairCombinePolicy()

        name = playernamepolicy(self.player1)
        club = clubnamepolicy(self.player1.club)
        ctry = countrynamepolicy(self.player1.country)

        if self.player2:
            name = paircombinepolicy(
                name, playernamepolicy(self.player2), first_can_be_none=False
            )
            club = paircombinepolicy(
                club, clubnamepolicy(self.player2.club), first_can_be_none=True
            )
            ctry = paircombinepolicy(
                ctry, countrynamepolicy(self.player2.country), first_can_be_none=True
            )

        if name is None:
            raise ValueError(f"No player name discernable from {self}")

        return PlayerExportStructValidator.validate_python(
            {
                k: v
                for k, v in (("name", name), ("club", club), ("country", ctry))
                if v is not None
                # TODO: omit None from result while
                # https://github.com/obbimi/Squore/issues/98
            }
        )

    __repr_fields__ = ("event.name", "player1.name", "player2?.name")
    __str_template__ = "{self.player1}{'&'+str(self.player2) if self.player2 else ''}"
    __eq_fields__ = ("event", "player1", "player2")
