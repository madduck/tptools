import datetime
import logging
from collections import defaultdict
from typing import (
    TYPE_CHECKING,
    Any,
    Iterable,
    TypedDict,
    cast,
)

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SerializationInfo,
    TypeAdapter,
    model_serializer,
)

from tptools.export import (
    Court,
    Draw,
    Entry,
    Match,
    MatchStatusSelectionParams,
    Tournament,
)
from tptools.matchstatus import MatchStatus
from tptools.mixins import ReprMixin, StrMixin
from tptools.models import Court as TPCourt
from tptools.namepolicy import (
    CourtNamePolicy,
    ParamsModel,
)

logger = logging.getLogger(__name__)


class PerMatchOverridableConfig(TypedDict, total=False):
    useHandInHandOutScoring: bool
    numberOfPointsToWinGame: int
    numberOfGamesToWinMatch: int
    tieBreakFormat: str
    timerPauseBetweenGames: int
    skipMatchSettings: bool

    __pydantic_config__ = ConfigDict(extra="forbid")  # type: ignore[misc]


PerMatchConfigValidator = TypeAdapter(PerMatchOverridableConfig)


class Config(PerMatchOverridableConfig, total=False):
    shareAction: str
    PostResult: str
    LiveScoreUrl: str
    captionForPostMatchResultToSite: str
    autoSuggestToPostResult: bool
    postDataPreference: str
    hideCompletedMatchesFromFeed: bool
    locationLast: str
    turnOnLiveScoringForMatchesFromFeed: bool
    postEveryChangeToSupportLiveScore: bool
    Placeholder_Match: str


ConfigValidator = TypeAdapter(Config)


class SqModel(ReprMixin, StrMixin, BaseModel):
    pass


class SquoreMatchStruct(PerMatchOverridableConfig, total=False):
    id: str
    matchnr: int
    draw: Draw
    date: datetime.date | None
    time: datetime.time | None
    court: Court | None
    A: Entry | str
    B: Entry | str
    status: MatchStatus


class SquoreMatch(Match):
    config: PerMatchOverridableConfig = cast(
        PerMatchOverridableConfig, Field(default_factory=dict[str, Any])
    )

    def _get_config_count(self) -> int:
        return len(self.config)

    __repr_fields__ = ["tpmatch", ("nconfig", _get_config_count, False)]  # type: ignore[list-item]

    @model_serializer(mode="plain")
    def _model_serializer(self, info: SerializationInfo) -> SquoreMatchStruct:  # type: ignore[override]
        m = super()._model_serializer(info)

        context = info.context or {}

        ret: SquoreMatchStruct = {
            "id": m["id"],
            "matchnr": m["matchnr"],
            "date": m["date"],
            "time": m["time"],
            "status": m["status"],
            **self.config,  # type: ignore[typeddict-item]
        }

        tournament: Tournament | None
        if (tournament := context.get("tournament")) is not None:
            ret["draw"] = tournament.resolve_draw_by_id(m["draw"])
            ret["court"] = (
                tournament.resolve_court_by_id(c)
                if (c := m["court"]) is not None
                else None
            )
            ret["A"] = (
                tournament.resolve_entry_by_id(a) if isinstance(a := m["A"], int) else a
            )
            ret["B"] = (
                tournament.resolve_entry_by_id(b) if isinstance(b := m["B"], int) else b
            )

        return ret

    if TYPE_CHECKING:
        # Ensure type checkers see the correct return type
        def model_dump(  # type: ignore[override]
            self,
            **_: Any,
        ) -> SquoreMatchStruct: ...


class MatchesSection(SqModel):
    name: str
    # Sorting in Squore is inconsistent. A hack is to prefix the section names
    # with a non-breaking space.
    nameprefix: str = "\xa0"
    expanded: bool = False
    expandprefix: str = "+"
    matches: list[SquoreMatch] = Field(default_factory=list)

    def _get_matches_len(self) -> int:
        return len(self.matches)

    __str_template__ = (
        "{self.get_name_expanding() if self.expanded else self.get_name()}"
    )
    __repr_fields__ = ("name", ("nmatches", _get_matches_len, False), "expanded")

    def get_name(self) -> str:
        return f"{self.nameprefix}{self.name}"

    def get_name_expanding(self) -> str:
        return f"{self.expandprefix}{self.get_name()}"


class CourtSelectionParams(ParamsModel):
    court: int | None = None
    only_this_court: bool = False


class MatchesFeed(SqModel):
    tournament: Tournament
    config: Config = cast(Config, Field(default_factory=dict[str, Any]))
    default_name: str = "Tournament with Squore"

    def _get_config_len(self) -> int:
        return len(self.config)

    __repr_fields__ = (
        "tournament",
        ("nconfig", _get_config_len, False),
    )
    __str_template__ = "{self.tournament}"

    @property
    def name(self) -> str:
        return self.tournament.name or self.default_name

    @staticmethod
    def _get_matches_by_court(
        matches: Iterable[SquoreMatch],
    ) -> dict[TPCourt | None, list[SquoreMatch]]:
        matches_by_court: dict[TPCourt | None, list[SquoreMatch]] = defaultdict(
            list[SquoreMatch]
        )
        # sort matches without a time last with this tuple trick:
        for match in sorted(
            matches, key=lambda m: (m.tpmatch.time is not None, m.tpmatch.time)
        ):
            tpmatch = match.tpmatch
            if (c := tpmatch.court) is None:
                logger.debug(f"Found {tpmatch!r} without an assigned court")
                c = None

            else:
                logger.debug(f"Found {tpmatch!r} on {tpmatch.court}")

            matches_by_court[c].append(SquoreMatch(tpmatch=tpmatch))

        return matches_by_court

    @staticmethod
    def _make_sections_for_courts(
        matches_by_court: dict[TPCourt | None, list[SquoreMatch]],
        courtnamepolicy: CourtNamePolicy,
        courtselectionparams: CourtSelectionParams,
    ) -> list[MatchesSection]:
        sections = []
        for matchcourt, sqmatches in matches_by_court.items():
            if matchcourt is None:
                thiscourt = courtselectionparams.court == 0
            else:
                thiscourt = matchcourt.id == courtselectionparams.court

            if courtselectionparams.only_this_court and not thiscourt:
                continue

            courtname = courtnamepolicy(matchcourt)
            sections.append(
                MatchesSection(name=courtname, expanded=thiscourt, matches=sqmatches)
            )

        return sections

    @model_serializer(mode="plain")
    def _model_serializer(self, info: SerializationInfo) -> dict[str, Any]:
        context = info.context or {}
        context.setdefault("tournament", self.tournament)

        matchstatusselectionparams = cast(
            MatchStatusSelectionParams,
            context.get("matchstatusselectionparams", MatchStatusSelectionParams()),
        )
        matches = self.tournament.get_matches(
            **dict(matchstatusselectionparams),
            cls=SquoreMatch,
        )
        matches_by_court = self._get_matches_by_court(matches.values())

        courtnamepolicy = cast(
            CourtNamePolicy, context.get("courtnamepolicy", CourtNamePolicy())
        )
        courtselectionparams = cast(
            CourtSelectionParams,
            context.get("courtselectionparams", CourtSelectionParams()),
        )

        sections = self._make_sections_for_courts(
            matches_by_court,
            courtnamepolicy=courtnamepolicy,
            courtselectionparams=courtselectionparams,
        )
        name = self.name
        for matchcourt in matches_by_court.keys():
            if matchcourt is not None and matchcourt.id == courtselectionparams.court:
                name = f"{name} ({courtnamepolicy(matchcourt)})"
                break

        ret = {
            "name": name,
            "config": self.config,
            "nummatches": sum(len(s.matches) for s in sections),
        }

        if not sections:
            return ret | {"matches": []}

        else:
            return ret | {str(s): s.matches for s in sections}
