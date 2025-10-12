import logging
from collections import defaultdict
from typing import (
    Any,
    Iterable,
    cast,
)

from pydantic import (
    Field,
    SerializationInfo,
    model_serializer,
)

from ...court import CourtSelectionParams
from ...namepolicy import CourtNamePolicy
from ...tournament import MatchSelectionParams, NumMatchesParams, Tournament
from .basemodel import SqModel
from .config import Config
from .court import SquoreCourt
from .draw import SquoreDraw
from .entry import SquoreEntry
from .match import SquoreMatch
from .section import MatchesSection

logger = logging.getLogger(__name__)


class SquoreTournament(
    Tournament[SquoreEntry, SquoreDraw, SquoreCourt, SquoreMatch]  # type: ignore[type-var]
    # TODO: Mypy error:
    # > Type argument "SquoreMatch" of "Tournament"
    # > must be a subtype of "Match[Entry, Draw, Court]"
    # See https://discord.com/channels/267624335836053506/891788761371906108/1423261501367517275
    # and https://discord.com/channels/267624335836053506/891788761371906108/1423261782981738598
): ...


class MatchesFeed(SqModel):
    tournament: SquoreTournament
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
    ) -> dict[SquoreCourt | None, list[SquoreMatch]]:
        matches_by_court: dict[SquoreCourt | None, list[SquoreMatch]] = defaultdict(
            list[SquoreMatch]
        )
        # sort matches without a time last with this tuple trick:
        for match in sorted(matches, key=lambda m: (m.time is not None, m.time)):
            if match.court is None:
                logger.debug(f"Found {match!r} without an assigned court")
                c = None

            else:
                logger.debug(f"Found {match!r} on {match.court}")
                c = SquoreCourt(**dict(match.court))

            matches_by_court[c].append(match)

        return matches_by_court

    @staticmethod
    def _make_sections_for_courts(
        matches_by_court: dict[SquoreCourt | None, list[SquoreMatch]],
        courtnamepolicy: CourtNamePolicy,
        courtselectionparams: CourtSelectionParams,
        nummatchesparams: NumMatchesParams,
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
                MatchesSection(
                    name=str(courtname),
                    expanded=thiscourt,
                    matches=sqmatches
                    if nummatchesparams.max_matches_per_court is None
                    else sqmatches[: nummatchesparams.max_matches_per_court],
                )
            )

        return sections

    @model_serializer(mode="plain")
    def _model_serializer(self, info: SerializationInfo) -> dict[str, Any]:
        matchselectionparams = self.get_params_from_info(
            info, "matchselectionparams", MatchSelectionParams()
        )
        nummatchesparams = self.get_params_from_info(
            info, "nummatchesparams", NumMatchesParams()
        )
        matches = self.tournament.get_matches(
            **dict(matchselectionparams),
        )
        matches_by_court = self._get_matches_by_court(matches)

        courtnamepolicy = self.get_policy_from_info(
            info, "courtnamepolicy", CourtNamePolicy()
        )
        courtselectionparams = self.get_params_from_info(
            info, "courtselectionparams", CourtSelectionParams()
        )
        sections = self._make_sections_for_courts(
            matches_by_court,
            courtnamepolicy=courtnamepolicy,
            courtselectionparams=courtselectionparams,
            nummatchesparams=nummatchesparams,
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
            ret |= {"matches": []}

        else:
            ret |= {str(s): s.matches for s in sections}

        return ret
