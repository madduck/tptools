from typing import Any, Callable

import pytest

from tptools.export import Court, Draw, Entry, Tournament
from tptools.ext.squore import (
    MatchesFeed,
    MatchesSection,
    SquoreMatch,
)
from tptools.sqlmodels import TPCourt, TPDraw, TPEntry
from tptools.tpmatch import TPMatch

from ...export.conftest import exptournament1

_ = exptournament1


@pytest.fixture
def sqplayer1(tpentry1: TPEntry) -> Entry:
    return Entry(tpentry=tpentry1)


@pytest.fixture
def sqplayer2(tpentry2: TPEntry) -> Entry:
    return Entry(tpentry=tpentry2)


@pytest.fixture
def sqplayer12(tpentry12: TPEntry) -> Entry:
    return Entry(tpentry=tpentry12)


@pytest.fixture
def sqcourt1(tpcourt1: TPCourt) -> Court:
    return Court(tpcourt=tpcourt1)


@pytest.fixture
def sqdraw1(tpdraw1: TPDraw) -> Draw:
    return Draw(tpdraw=tpdraw1)


@pytest.fixture
def sqmatch1(tpmatch1: TPMatch) -> SquoreMatch:
    return SquoreMatch(tpmatch=tpmatch1)


@pytest.fixture
def sqmatch2(tpmatch2: TPMatch) -> SquoreMatch:
    return SquoreMatch(tpmatch=tpmatch2, config={"numberOfGamesToWinMatch": 11})


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
