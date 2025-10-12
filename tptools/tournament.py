import logging
from collections import defaultdict
from collections.abc import Iterable, Sequence
from typing import Any, Self, cast

from pydantic import (
    SerializationInfo,
    model_serializer,
)
from sqlmodel import Session, select

from .basemodel import BaseModel
from .court import Court
from .draw import Draw, InvalidDrawType
from .entry import Entry
from .match import Match
from .paramsmodel import ParamsModel
from .sqlmodels import TPCourt, TPDraw, TPEntry, TPPlayerMatch, TPSetting
from .tpmatch import TPMatchMaker
from .tpmatch import TPMatchStatus as MatchStatus

logger = logging.getLogger(__name__)


class MatchSelectionParams(ParamsModel):
    include_played: bool = False
    include_not_ready: bool = False


class Tournament[
    EntryT: Entry = Entry,
    DrawT: Draw = Draw,
    CourtT: Court = Court,
    MatchT: Match = Match,
    TPModelT: None = None,
](BaseModel[TPModelT]):
    name: str | None = None
    entries: dict[int, EntryT] = {}
    draws: dict[int, DrawT] = {}
    courts: dict[int, CourtT] = {}
    matches: dict[str, MatchT] = {}

    __eq_fields__ = ("name", "entries", "draws", "courts", "matches")
    __cmp_fields__ = ("name", "nentries", "ndraws", "ncourts", "nmatches")
    __str_template__ = (
        "{self.name} ({self.nentries} entries, {self.ndraws} draws, "
        "{self.ncourts} courts, {self.nmatches} matches)"
    )
    __repr_fields__ = ("name?", "nentries", "ndraws", "ncourts", "nmatches")

    def add_entry(self, entry: EntryT) -> None:
        if entry.id in self.entries:
            raise ValueError(f"{entry!r} already added")
        self.entries[entry.id] = entry

    def add_entries(self, entries: Iterable[EntryT]) -> None:
        self.entries |= {e.id: e for e in entries}

    @property
    def nentries(self) -> int:
        return len(self.entries)

    def get_entries(self) -> Sequence[EntryT]:
        return list(self.entries.values())

    def resolve_entry_by_id(self, id: int) -> EntryT:
        return self.entries[id]

    def add_match(self, match: MatchT) -> None:
        if match.id in self.matches:
            raise ValueError(f"{match!r} already added")
        self.matches[match.id] = match

    def add_matches(self, matches: Iterable[MatchT]) -> None:
        self.matches |= {m.id: m for m in matches}

    @property
    def nmatches(self) -> int:
        return len(self.matches)

    @staticmethod
    def _params_to_status_set(params: MatchSelectionParams) -> set[MatchStatus]:
        accepted_statuses = set(MatchStatus)
        if not params.include_played:
            accepted_statuses.remove(MatchStatus.PLAYED)
            accepted_statuses.remove(MatchStatus.NOTPLAYED)
        if not params.include_not_ready:
            accepted_statuses.remove(MatchStatus.PENDING)

        return accepted_statuses

    def select_matches(
        self,
        include_played: bool = False,
        include_not_ready: bool = True,
        # TODO: remove redundancy with MatchStatusSelectionParams above
    ) -> dict[str, MatchT]:
        accepted_statuses = Tournament._params_to_status_set(
            MatchSelectionParams(
                include_not_ready=include_not_ready, include_played=include_played
            )
        )
        return {m.id: m for m in self.matches.values() if m.status in accepted_statuses}

    def get_matches(
        self,
        include_played: bool = False,
        include_not_ready: bool = True,
        # TODO: remove redundancy with MatchStatusSelectionParams above
    ) -> Sequence[MatchT]:
        if include_played and include_not_ready:
            return list(self.matches.values())

        return list(
            self.select_matches(
                include_not_ready=include_not_ready, include_played=include_played
            ).values()
        )

    def resolve_match_by_id(self, id: str) -> MatchT:
        return self.matches[id]

    def get_matches_for_draw(self, draw: DrawT) -> Sequence[MatchT]:
        return [m for m in self.matches.values() if m.draw == draw]

    def get_matches_for_court(self, court: CourtT | None) -> Sequence[MatchT]:
        return [m for m in self.matches.values() if m.court == court]

    def get_matches_by_court(self) -> dict[CourtT | None, list[MatchT]]:
        ret: dict[CourtT | None, list[MatchT]] = defaultdict(list)
        for match in self.matches.values():
            ret[cast(CourtT, match.court)].append(match)
        return ret

    def add_draw(self, draw: DrawT) -> None:
        if draw.id in self.draws:
            raise ValueError(f"{draw!r} already added")
        self.draws[draw.id] = draw

    def add_draws(self, draws: Iterable[DrawT]) -> None:
        self.draws |= {d.id: d for d in draws}

    @property
    def ndraws(self) -> int:
        return len(self.draws)

    def get_draws(self) -> Sequence[DrawT]:
        return list(self.draws.values())

    def resolve_draw_by_id(self, id: int) -> DrawT:
        return self.draws[id]

    def add_court(self, court: CourtT) -> None:
        if court.id in self.courts:
            raise ValueError(f"{court!r} already added")
        self.courts[court.id] = court

    def add_courts(self, courts: Iterable[CourtT]) -> None:
        self.courts |= {c.id: c for c in courts}

    @property
    def ncourts(self) -> int:
        return len(self.courts)

    def get_courts(self) -> Sequence[CourtT]:
        return list(self.courts.values())

    def resolve_court_by_id(self, id: int) -> CourtT:
        return self.courts[id]

    @model_serializer(mode="plain")
    def _model_serializer(
        self,
        info: SerializationInfo,
    ) -> dict[str, Any]:
        matchselectionparams = BaseModel.get_params_from_info(
            info, "matchselectionparams", MatchSelectionParams()
        )
        return {
            "name": self.name,
            "class": self.__class__.__qualname__,
            "draws": self.draws,
            "courts": self.courts,
            "entries": self.entries,
            "matches": self.select_matches(**dict(matchselectionparams)),
        }

    @classmethod
    def from_tournament(cls, tournament: "Tournament") -> Self:
        return cls.model_validate(tournament.model_dump())


async def load_tournament(
    # EntryT: Entry = Entry,
    # DrawT: Draw = Draw,
    # CourtT: Court = Court,
    # MatchT: Match = Match,
    db_session: Session,
    *,
    EntryClass: type[Entry] = Entry,
    DrawClass: type[Draw] = Draw,
    CourtClass: type[Court] = Court,
    MatchClass: type[Match] = Match,
) -> Tournament:
    tset = db_session.exec(
        select(TPSetting).where(TPSetting.name == "Tournament")
    ).one_or_none()
    entries = [EntryClass.from_tp_model(e) for e in db_session.exec(select(TPEntry))]

    try:
        draws = [DrawClass.from_tp_model(d) for d in db_session.exec(select(TPDraw))]

    except ValueError as err:  # pragma: nocover
        # TODO: figure out how to test for this branch
        if "is not a valid DrawType" in err.args[0]:
            split = err.args[0].split(" ", 1)
            raise InvalidDrawType(int(split[0])) from err

        raise

    courts = [CourtClass.from_tp_model(c) for c in db_session.exec(select(TPCourt))]
    mm = TPMatchMaker()
    for pm in db_session.exec(select(TPPlayerMatch)):
        mm.add_playermatch(pm)

    mm.resolve_unmatched()
    mm.resolve_match_entries()

    matches = [MatchClass.from_tpmatch(m) for m in mm.matches]

    tournament = Tournament(
        name=tset.value if tset is not None else None,
    )
    tournament.add_draws(draws)
    tournament.add_entries(entries)
    tournament.add_courts(courts)
    tournament.add_matches(matches)

    return tournament
