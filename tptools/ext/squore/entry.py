from typing import TYPE_CHECKING, Any, ClassVar, TypedDict

from pydantic import SerializationInfo, TypeAdapter, model_serializer

from tptools import Entry
from tptools.namepolicy import (
    ClubNamePolicy,
    CountryNamePolicy,
    PairCombinePolicy,
    PlayerNamePolicy,
)


class SquorePlayerStruct(TypedDict):
    name: str
    club: str | None
    country: str | None


SquorePlayerStructValidator = TypeAdapter(SquorePlayerStruct)


class SquoreEntry(Entry):
    CLUBNAMEPOLICY: ClassVar[str] = "clubnamepolicy"
    COUNTRYNAMEPOLICY: ClassVar[str] = "countrynamepolicy"
    PLAYERNAMEPOLICY: ClassVar[str] = "playernamepolicy"
    PAIRCOMBINEPOLICY: ClassVar[str] = "paircombinepolicy"

    @model_serializer(mode="plain")
    def apply_policies(self, info: SerializationInfo) -> SquorePlayerStruct:
        clubnamepolicy = self.get_policy_from_info(
            info, self.CLUBNAMEPOLICY, ClubNamePolicy()
        )
        countrynamepolicy = self.get_policy_from_info(
            info, self.COUNTRYNAMEPOLICY, CountryNamePolicy()
        )
        playernamepolicy = self.get_policy_from_info(
            info, self.PLAYERNAMEPOLICY, PlayerNamePolicy()
        )
        name = playernamepolicy(self.player1)
        club = clubnamepolicy(self.player1.club)
        ctry = countrynamepolicy(self.player1.country)

        if self.player2:
            paircombinepolicy = self.get_policy_from_info(
                info, self.PAIRCOMBINEPOLICY, PairCombinePolicy()
            )
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

        return SquorePlayerStructValidator.validate_python(
            {"name": name, "club": club, "country": ctry}
        )

    if TYPE_CHECKING:
        # Ensure type checkers see the correct return type
        def model_dump(self, **_: Any) -> SquorePlayerStruct: ...  # type: ignore[override]
