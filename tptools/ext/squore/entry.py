from typing import TYPE_CHECKING, Any, ClassVar, NotRequired, TypedDict

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
    club: NotRequired[str | None]
    country: NotRequired[str | None]


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
        paircombinepolicy = self.get_policy_from_info(
            info, self.PAIRCOMBINEPOLICY, PairCombinePolicy()
        )

        return self.make_player_export_struct(
            clubnamepolicy=clubnamepolicy,
            countrynamepolicy=countrynamepolicy,
            playernamepolicy=playernamepolicy,
            paircombinepolicy=paircombinepolicy,
        )

    if TYPE_CHECKING:
        # Ensure type checkers see the correct return type
        def model_dump(self, **_: Any) -> SquorePlayerStruct: ...  # type: ignore[override]
