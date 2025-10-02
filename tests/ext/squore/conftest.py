from collections.abc import Callable
from typing import Any

import pytest

from tptools.ext.squore import (
    MatchesFeed,
    MatchesSection,
    SquoreCourt,
    SquoreDraw,
    SquoreEntry,
)
from tptools.ext.squore.feed import SquoreTournament
from tptools.ext.squore.match import SquoreMatch
from tptools.sqlmodels import TPCourt, TPDraw, TPEntry
from tptools.tpmatch import TPMatch


@pytest.fixture
def sqcourt(tpcourt1: TPCourt) -> SquoreCourt:
    return SquoreCourt.from_tp_model(tpcourt1)


@pytest.fixture
def sqdraw(tpdraw1: TPDraw) -> SquoreDraw:
    return SquoreDraw.from_tp_model(tpdraw1)


@pytest.fixture
def sqentry(tpentry1: TPEntry) -> SquoreEntry:
    return SquoreEntry.from_tp_model(tpentry1)


@pytest.fixture
def sqentrydbl(tpentry12: TPEntry) -> SquoreEntry:
    return SquoreEntry.from_tp_model(tpentry12)


@pytest.fixture
def sqmatch1(tpmatch1: TPMatch) -> SquoreMatch:
    return SquoreMatch.from_tpmatch(tpmatch1)


@pytest.fixture
def sqmatch2(tpmatch2: TPMatch) -> SquoreMatch:
    return SquoreMatch.from_tpmatch(tpmatch2)


@pytest.fixture
def sqmatch_pending(tpmatch_pending: TPMatch) -> SquoreMatch:
    return SquoreMatch.from_tpmatch(tpmatch_pending)


@pytest.fixture
def sqtournament(
    sqentry: SquoreEntry,
    sqentrydbl: SquoreEntry,
    sqcourt: SquoreCourt,
    sqdraw: SquoreDraw,
    sqmatch1: SquoreMatch,
    sqmatch2: SquoreMatch,
) -> SquoreTournament:
    st = SquoreTournament(name="Squore tournament")
    st.add_court(sqcourt)
    st.add_draw(sqdraw)
    st.add_entry(sqentry)
    st.add_entry(sqentrydbl)
    st.add_match(sqmatch1)
    st.add_match(sqmatch2)
    return st


type MatchesSectionFactoryType = Callable[..., MatchesSection]


@pytest.fixture
def MatchesSectionFactory() -> MatchesSectionFactoryType:
    def msmaker(**kwargs: Any) -> MatchesSection:
        defaults: dict[str, Any] = {"name": "name"}
        return MatchesSection(**defaults | kwargs)

    return msmaker


type MatchesFeedFactoryType = Callable[..., MatchesFeed]


@pytest.fixture
def MatchesFeedFactory(sqtournament: SquoreTournament) -> MatchesFeedFactoryType:
    def mfmaker(**kwargs: Any) -> MatchesFeed:
        defaults: dict[str, Any] = {
            "name": "tournament name",
            "tournament": sqtournament,
            "default_name": "default name",
        }
        return MatchesFeed(**defaults | kwargs)

    return mfmaker
