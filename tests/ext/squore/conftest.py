from typing import Any, Callable

import pytest

from tptools.export import Court, Draw, Entry, Tournament
from tptools.ext.squore import (
    MatchesFeed,
    MatchesSection,
    SquoreMatch,
)
from tptools.match import Match as TPMatch
from tptools.sqlmodels import TPCourt, TPDraw, TPEntry

from ...export.conftest import exptournament1

_ = exptournament1


@pytest.fixture
def sqplayer1(entry1: TPEntry) -> Entry:
    return Entry(tpentry=entry1)


@pytest.fixture
def sqplayer2(entry2: TPEntry) -> Entry:
    return Entry(tpentry=entry2)


@pytest.fixture
def sqplayer12(entry12: TPEntry) -> Entry:
    return Entry(tpentry=entry12)


@pytest.fixture
def sqcourt1(court1: TPCourt) -> Court:
    return Court(tpcourt=court1)


@pytest.fixture
def sqdraw1(draw1: TPDraw) -> Draw:
    return Draw(tpdraw=draw1)


@pytest.fixture
def sqmatch1(match1: TPMatch) -> SquoreMatch:
    return SquoreMatch(tpmatch=match1)


@pytest.fixture
def sqmatch2(match2: TPMatch) -> SquoreMatch:
    return SquoreMatch(tpmatch=match2, config={"numberOfGamesToWinMatch": 11})


type MatchesSectionFactoryType = Callable[..., MatchesSection]


@pytest.fixture
def MatchesSectionFactory() -> MatchesSectionFactoryType:
    def msmaker(**kwargs: Any) -> MatchesSection:
        defaults: dict[str, Any] = {"name": "name"}
        return MatchesSection(**defaults | kwargs)

    return msmaker


type MatchesFeedFactoryType = Callable[..., MatchesFeed]


@pytest.fixture
def MatchesFeedFactory(exptournament1: Tournament) -> MatchesFeedFactoryType:
    def mfmaker(**kwargs: Any) -> MatchesFeed:
        defaults: dict[str, Any] = {
            "tournament": exptournament1,
            "default_name": "default name",
        }
        return MatchesFeed(**defaults | kwargs)

    return mfmaker
