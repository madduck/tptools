import datetime
import logging
from typing import (
    TYPE_CHECKING,
    Any,
    TypedDict,
)

from pydantic import (
    BaseModel,
    SerializationInfo,
    model_serializer,
)

from tptools.match import Match as TPMatch
from tptools.matchstatus import MatchStatus
from tptools.mixins import ReprMixin, StrMixin

logger = logging.getLogger(__name__)


class MatchStruct(TypedDict, total=True):
    id: str
    matchnr: int
    draw: int
    date: datetime.date | None
    time: datetime.time | None
    court: int | None
    A: int | str
    B: int | str
    status: MatchStatus


class Match(ReprMixin, StrMixin, BaseModel):
    tpmatch: TPMatch

    __repr_fields__ = ["tpmatch"]
    __str_template__ = "{self.tpmatch}"

    @property
    def id(self) -> str:
        return self.tpmatch.id

    @property
    def matchnr(self) -> int:
        return self.tpmatch.matchnr

    @property
    def draw(self) -> int:
        return self.tpmatch.draw.id

    @property
    def date(self) -> datetime.date | None:
        return self.tpmatch.time.date() if self.tpmatch.time else None

    @property
    def time(self) -> datetime.time | None:
        return self.tpmatch.time.time() if self.tpmatch.time else None

    @property
    def court(self) -> int | None:
        return self.tpmatch.court.id if self.tpmatch.court else None

    @property
    def A(self) -> int | str:
        return self.tpmatch.slot1.id or str(self.tpmatch.slot1)

    @property
    def B(self) -> int | str:
        return self.tpmatch.slot2.id or str(self.tpmatch.slot2)

    @property
    def status(self) -> MatchStatus:
        return self.tpmatch.status

    @model_serializer(mode="plain")
    def _model_serializer(self, info: SerializationInfo) -> MatchStruct:
        _ = info
        return {
            "id": self.id,
            "matchnr": self.matchnr,
            "draw": self.draw,
            "date": self.date,
            "time": self.time,
            "court": self.court,
            "A": self.A,
            "B": self.B,
            "status": self.status,
        }

    if TYPE_CHECKING:
        # Ensure type checkers see the correct return type
        def model_dump(  # type: ignore[override]
            self,
            **_: Any,
        ) -> MatchStruct: ...
