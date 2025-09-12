import logging
from typing import (
    TYPE_CHECKING,
    Any,
    TypedDict,
    cast,
)

from pydantic import (
    BaseModel,
    ConfigDict,
    SerializationInfo,
    model_serializer,
)

from tptools.mixins import ReprMixin, StrMixin
from tptools.mixins.comparable import ComparableMixin
from tptools.models import Entry as TPEntry
from tptools.namepolicy import (
    ClubNamePolicy,
    CountryNamePolicy,
    PairCombinePolicy,
    PlayerNamePolicy,
)

logger = logging.getLogger(__name__)


class EntryStruct(TypedDict, total=True):
    name: str
    club: str | None
    country: str | None


class Entry(ReprMixin, StrMixin, ComparableMixin, BaseModel):
    tpentry: TPEntry

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @property
    def id(self) -> int:
        return self.tpentry.id

    @property
    def name(self) -> str:
        return self.tpentry.name

    @model_serializer(mode="plain")
    def _model_serializer(
        self,
        info: SerializationInfo,
    ) -> EntryStruct:
        entry = self.tpentry

        context = info.context or {}
        paircombinepolicy = context.get("paircombinepolicy") or PairCombinePolicy()
        playernamepolicy = context.get("playernamepolicy") or PlayerNamePolicy(
            include_club=False, include_country=False
        )
        clubnamepolicy = context.get("clubnamepolicy") or ClubNamePolicy()
        countrynamepolicy = context.get("countrynamepolicy") or CountryNamePolicy()

        name = cast(str, playernamepolicy(entry.player1))
        club = clubnamepolicy(entry.player1.club)
        country = countrynamepolicy(entry.player1.country)

        if entry.player2:
            paircombinepolicy = paircombinepolicy or PairCombinePolicy()
            name = paircombinepolicy(name, playernamepolicy(entry.player2))
            club = paircombinepolicy(
                club, clubnamepolicy(entry.player2.club), first_can_be_none=True
            )
            country = paircombinepolicy(
                country,
                countrynamepolicy(entry.player2.country),
                first_can_be_none=True,
            )

        return {"name": name, "club": club, "country": country}

    if TYPE_CHECKING:
        # Ensure type checkers see the correct return type
        def model_dump(  # type: ignore[override]
            self,
            **_: Any,
        ) -> EntryStruct: ...

    __repr_fields__ = ("tpentry",)
    __str_template__ = "{self.tpentry}"
    __eq_fields__ = ("tpentry",)
