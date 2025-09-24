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

from tptools.mixins import ReprMixin, StrMixin
from tptools.namepolicy import ParamsModel
from tptools.tpdata import TPData

from .court import Court
from .draw import Draw
from .entry import Entry
from .match import Match

logger = logging.getLogger(__name__)


class MatchStatusSelectionParams(ParamsModel):
    include_played: bool = False
    include_not_ready: bool = False


class TournamentStruct(TypedDict, total=True):
    name: str | None
    draws: dict[int, Draw]
    courts: dict[int, Court]
    entries: dict[int, Entry]
    matches: dict[str, Match]


class Tournament(ReprMixin, StrMixin, BaseModel):
    tpdata: TPData

    @model_serializer(mode="plain")
    def _model_serializer(
        self,
        info: SerializationInfo,
    ) -> TournamentStruct:
        context = info.context or {}
        matchstatusselectionparams = (
            context.get("matchstatusselectionparams") or MatchStatusSelectionParams()
        )
        CourtClass = context.get("EntryClass") or Court
        DrawClass = context.get("EntryClass") or Draw
        MatchClass = context.get("MatchClass") or Match
        EntryClass = context.get("EntryClass") or Entry

        return {
            "name": self.tpdata.name,
            "draws": self.get_draws(cls=DrawClass),
            "courts": self.get_courts(cls=CourtClass),
            "entries": self.get_entries(cls=EntryClass),
            "matches": self.get_matches(
                **dict(matchstatusselectionparams), cls=MatchClass
            ),
        }

    @property
    def name(self) -> str | None:
        return self.tpdata.name

    def get_matches[T: Match](
        self,
        # TODO:eliminate redundancy with MatchStatusSelectionParams above
        include_played: bool = False,
        include_not_ready: bool = True,
        *,
        cls: type[T] = Match,  # type: ignore[assignment]
    ) -> dict[str, T]:
        return {
            m.id: cls(tpmatch=m)
            for m in self.tpdata.get_matches(
                include_played=include_played, include_not_ready=include_not_ready
            )
        }

    def get_entries[T: Entry](self, *, cls: type[T] = Entry) -> dict[int, T]:  # type: ignore[assignment]
        if getattr(self, "_cached_entries", None) is None:
            self._cached_entries = {
                e.id: cls(tpentry=e) for e in self.tpdata.get_entries()
            }
        return self._cached_entries

    def resolve_entry_by_id[T: Entry](self, id: int, *, cls: type[T] = Entry) -> T:  # type: ignore[assignment]
        return self.get_entries(cls=cls)[id]

    def get_courts[T: Court](self, *, cls: type[T] = Court) -> dict[int, T]:  # type: ignore[assignment]
        if getattr(self, "_cached_courts", None) is None:
            self._cached_courts = {
                c.id: cls(tpcourt=c) for c in self.tpdata.get_courts()
            }
        return self._cached_courts

    def resolve_court_by_id[T: Court](self, id: int, *, cls: type[T] = Court) -> T:  # type: ignore[assignment]
        return self.get_courts(cls=cls)[id]

    def get_draws[T: Draw](self, *, cls: type[T] = Draw) -> dict[int, T]:  # type: ignore[assignment]
        if getattr(self, "_cached_draws", None) is None:
            self._cached_draws = {d.id: cls(tpdraw=d) for d in self.tpdata.get_draws()}
        return self._cached_draws

    def resolve_draw_by_id[T: Draw](self, id: int, *, cls: type[T] = Draw) -> T:  # type: ignore[assignment]
        return self.get_draws(cls=cls)[id]

    if TYPE_CHECKING:
        # Ensure type checkers see the correct return type
        def model_dump(  # type: ignore[override]
            self,
            **_: Any,
        ) -> TournamentStruct: ...

    __repr_fields__ = ("tpdata",)
    __str_template__ = "{self.tpdata}"
