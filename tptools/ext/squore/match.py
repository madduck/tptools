import logging
from datetime import datetime
from typing import (
    Any,
    Literal,
    Self,
    cast,
)

from pydantic import (
    Field,
    SerializerFunctionWrapHandler,
    TypeAdapter,
    model_serializer,
)

from ...match import Match
from ...tpmatch import TPMatch
from ...util import ScoresType
from .config import PerMatchOverridableConfig
from .court import SquoreCourt
from .draw import SquoreDraw, SquoreDrawStruct
from .entry import SquoreEntry, SquorePlayerStruct

logger = logging.getLogger(__name__)


class SquoreMatchStruct(PerMatchOverridableConfig, total=False):
    id: str
    matchnr: int
    draw: SquoreDrawStruct
    date: str | None
    time: str | None
    court: int | None
    A: SquorePlayerStruct | str
    B: SquorePlayerStruct | str
    starttime: datetime | None
    endtime: datetime | None
    winner: Literal["A"] | Literal["B"] | None
    scores: ScoresType
    status: str
    config: PerMatchOverridableConfig


SquoreMatchStructValidator = TypeAdapter(SquoreMatchStruct)


class SquoreMatch(Match[SquoreEntry, SquoreDraw, SquoreCourt]):
    config: PerMatchOverridableConfig = cast(
        PerMatchOverridableConfig, Field(default_factory=dict[str, Any])
    )

    def _get_config_count(self) -> int:
        return len(self.config)

    __repr_fields__ = Match.__repr_fields__ + [("nconfig", _get_config_count, False)]

    @classmethod
    def from_tpmatch(cls, tpmatch: TPMatch) -> Self:  # type: ignore[override]
        return super().from_tpmatch(
            tpmatch,
            EntryClass=SquoreEntry,
            DrawClass=SquoreDraw,
            CourtClass=SquoreCourt,
        )

    @model_serializer(mode="wrap")
    def split_date_from_time(
        self, handler: SerializerFunctionWrapHandler
    ) -> SquoreMatchStruct:
        ret: SquoreMatchStruct = handler(self)
        dt = self.time
        ret["date"] = dt.date().strftime("%F") if dt is not None else None
        ret["time"] = dt.time().strftime("%H:%M") if dt is not None else None
        return SquoreMatchStructValidator.validate_python(ret)
