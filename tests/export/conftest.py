import pytest

from tptools.export import Court, Draw, Entry, Match, Tournament
from tptools.match import Match as TPMatch
from tptools.sqlmodels import Court as TPCourt
from tptools.sqlmodels import Entry as TPEntry
from tptools.sqlmodels import TPDraw
from tptools.tpdata import TPData


@pytest.fixture
def expentry1(entry1: TPEntry) -> Entry:
    return Entry(tpentry=entry1)


expentry1copy = expentry1


@pytest.fixture
def expentry2(entry2: TPEntry) -> Entry:
    return Entry(tpentry=entry2)


@pytest.fixture
def expentry12(entry12: TPEntry) -> Entry:
    return Entry(tpentry=entry12)


@pytest.fixture
def expcourt1(court1: TPCourt) -> Court:
    return Court(tpcourt=court1)


@pytest.fixture
def expcourt2(court2: TPCourt) -> Court:
    return Court(tpcourt=court2)


expcourt1copy = expcourt1


@pytest.fixture
def expdraw1(draw1: TPDraw) -> Draw:
    return Draw(tpdraw=draw1)


@pytest.fixture
def expmatch1(match1: TPMatch) -> Match:
    return Match(tpmatch=match1)


@pytest.fixture
def expmatch2(match2: TPMatch) -> Match:
    return Match(tpmatch=match2)


@pytest.fixture
def exptournament1(tpdata1: TPData) -> Tournament:
    return Tournament(tpdata=tpdata1)
