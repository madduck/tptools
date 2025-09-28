import pytest

from tptools.export import Court, Draw, Entry, Match, Tournament
from tptools.match import Match as TPMatch
from tptools.sqlmodels import TPCourt, TPDraw, TPEntry
from tptools.tpdata import TPData


@pytest.fixture
def expentry1(tpentry1: TPEntry) -> Entry:
    return Entry(tpentry=tpentry1)


expentry1copy = expentry1


@pytest.fixture
def expentry2(tpentry2: TPEntry) -> Entry:
    return Entry(tpentry=tpentry2)


@pytest.fixture
def expentry12(tpentry12: TPEntry) -> Entry:
    return Entry(tpentry=tpentry12)


@pytest.fixture
def expcourt1(tpcourt1: TPCourt) -> Court:
    return Court(tpcourt=tpcourt1)


@pytest.fixture
def expcourt2(tpcourt2: TPCourt) -> Court:
    return Court(tpcourt=tpcourt2)


expcourt1copy = expcourt1


@pytest.fixture
def expdraw1(tpdraw1: TPDraw) -> Draw:
    return Draw(tpdraw=tpdraw1)


@pytest.fixture
def expmatch1(match1: TPMatch) -> Match:
    return Match(tpmatch=match1)


@pytest.fixture
def expmatch2(match2: TPMatch) -> Match:
    return Match(tpmatch=match2)


@pytest.fixture
def exptournament1(tpdata1: TPData) -> Tournament:
    return Tournament(tpdata=tpdata1)
