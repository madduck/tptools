import datetime
import logging
from typing import Literal, Self, cast

from pydantic import BaseModel

from .court import Court
from .draw import Draw
from .entry import Entry
from .mixins import ComparableMixin, ReprMixin, StrMixin
from .slot import Slot, SlotType
from .sqlmodels import TPEntry
from .tpmatch import TPMatch, TPMatchStatus
from .util import ScoresType, scores_to_string

logger = logging.getLogger(__name__)


class Match[EntryT: Entry = Entry, DrawT: Draw = Draw, CourtT: Court = Court](
    ComparableMixin, ReprMixin, StrMixin, BaseModel
):
    id: str
    matchnr: int
    draw: DrawT
    time: datetime.datetime | None
    court: CourtT | None
    A: EntryT | str
    B: EntryT | str
    status: TPMatchStatus
    winner: Literal["A"] | Literal["B"] | None = None
    scores: ScoresType = []

    __repr_fields__ = [
        "id",
        "matchnr",
        "draw",
        ("time", TPMatch._time_repr, False),
        "court",
        "A",
        "B",
        ("status", TPMatch._status_repr, False),
        "winner",
        ("scores", lambda s: scores_to_string(s.scores, nullstr="-"), False),
    ]
    __str_template__ = (
        "{self.id} {self.status}"
        "{(' on '+str(self.court)) if self.court else ''}"
        "{(self.time.strftime(' @ %H:%M')) if self.time else ''}"
    )
    __eq_fields__ = (
        "id",
        "matchnr",
        "draw",
        "time",
        "court",
        "A",
        "B",
        "status",
    )

    @classmethod
    def from_tpmatch(
        cls,
        tpmatch: TPMatch,
        *,
        EntryClass: type[EntryT] = Entry,  # type: ignore[assignment]
        DrawClass: type[DrawT] = Draw,  # type: ignore[assignment]
        CourtClass: type[CourtT] = Court,  # type: ignore[assignment]
    ) -> Self:
        def slot_to_player(slot: Slot) -> EntryT | str:
            if slot.type == SlotType.ENTRY:
                return EntryClass.from_tp_model(cast(TPEntry, slot.content))

            return slot.name

        players = {
            "A": slot_to_player(tpmatch.slot1),
            "B": slot_to_player(tpmatch.slot2),
        }

        winner: Literal["A"] | Literal["B"] | None = None
        if tpmatch.winner is not None:
            winner = "A" if tpmatch.pm1.winner == 1 else "B"

        return cls(
            id=tpmatch.id,
            matchnr=tpmatch.matchnr,
            draw=DrawClass.from_tp_model(tpmatch.draw),
            time=tpmatch.time,
            court=CourtClass.from_tp_model(tpmatch.court) if tpmatch.court else None,
            status=tpmatch.status,
            winner=winner,
            scores=tpmatch.scores,
            **players,
        )
