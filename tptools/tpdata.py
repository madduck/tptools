from collections.abc import Iterable

from pydantic import BaseModel, model_serializer
from sqlmodel import Session, select

from .match import Match
from .matchmaker import MatchMaker
from .matchstatus import MatchStatus
from .mixins import ComparableMixin, ReprMixin, StrMixin
from .sqlmodels import TPCourt, TPDraw, TPEntry, TPPlayerMatch, TPSetting


class TPData(ReprMixin, StrMixin, ComparableMixin, BaseModel):
    name: str | None = None
    entries: set[TPEntry] = set()
    draws: set[TPDraw] = set()
    courts: set[TPCourt] = set()
    matches: set[Match] = set()

    def add_entry(self, entry: TPEntry) -> None:
        if entry in self.entries:
            raise ValueError(f"{entry!r} already added")
        self.entries.add(entry)

    def add_entries(self, entries: Iterable[TPEntry]) -> None:
        self.entries |= set(entries)

    def add_match(self, match: Match) -> None:
        if match in self.matches:
            raise ValueError(f"{match!r} already added")
        self.matches.add(match)

    def add_matches(self, matches: Iterable[Match]) -> None:
        self.matches |= set(matches)

    def add_draw(self, draw: TPDraw) -> None:
        if draw in self.draws:
            raise ValueError(f"{draw!r} already added")
        self.draws.add(draw)

    def add_draws(self, draws: Iterable[TPDraw]) -> None:
        self.draws |= set(draws)

    def add_court(self, court: TPCourt) -> None:
        if court in self.courts:
            raise ValueError(f"{court!r} already added")
        self.courts.add(court)

    def add_courts(self, courts: Iterable[TPCourt]) -> None:
        self.courts |= set(courts)

    @property
    def ndraws(self) -> int:
        return len(self.draws)

    @property
    def ncourts(self) -> int:
        return len(self.courts)

    @property
    def nmatches(self) -> int:
        return len(self.matches)

    def get_matches(
        self, include_played: bool = False, include_not_ready: bool = True
    ) -> set[Match]:
        if include_played and include_not_ready:
            return self.matches

        accepted_statuses = set(MatchStatus)
        if not include_played:
            accepted_statuses.remove(MatchStatus.PLAYED)
            accepted_statuses.remove(MatchStatus.NOTPLAYED)
        if not include_not_ready:
            accepted_statuses.remove(MatchStatus.PENDING)

        return {m for m in self.matches if m.status in accepted_statuses}  # pyright: ignore[reportUnhashable]

    def get_matches_by_draw(self, draw: TPDraw) -> set[Match]:
        return {m for m in self.matches if m.draw == draw}  # pyright: ignore[reportUnhashable]

    def get_draws(self) -> set[TPDraw]:
        return self.draws

    def get_courts(self) -> set[TPCourt]:
        return self.courts

    @property
    def nentries(self) -> int:
        return len(self.entries)

    def get_entries(self) -> set[TPEntry]:
        return self.entries

    __eq_fields__ = (
        "name",
        "entries",
        "draws",
        "courts",
        "matches",
    )
    __str_template__ = (
        "{self.name} ({self.nentries} entries, {self.ndraws} draws, "
        "{self.ncourts} courts, {self.nmatches} matches)"
    )
    __repr_fields__ = ("name?", "nentries", "ndraws", "ncourts", "nmatches")

    @model_serializer
    def serialise_with_lists(self) -> dict[str, list[TPEntry] | list[Match]]:
        return {
            "entries": list(self.entries),
            "matches": list(self.matches),
        }


async def load_tournament(db_session: Session) -> TPData:
    tset = db_session.exec(
        select(TPSetting).where(TPSetting.name == "Tournament")
    ).one_or_none()
    entries = db_session.exec(select(TPEntry))
    draws = db_session.exec(select(TPDraw))
    courts = db_session.exec(select(TPCourt))
    mm = MatchMaker()
    for pm in db_session.exec(select(TPPlayerMatch)):
        mm.add_playermatch(pm)

    mm.resolve_unmatched()
    mm.resolve_match_entries()

    return TPData(
        name=tset.value if tset is not None else None,
        entries=set(entries),
        draws=set(draws),
        courts=set(courts),
        matches=set(mm.matches),
    )
