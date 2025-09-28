import pytest
from sqlmodel import Session

from tptools.match import Match
from tptools.sqlmodels import TPCourt, TPDraw, TPEntry
from tptools.tpdata import TPData, load_tournament


@pytest.fixture
def tpdata() -> TPData:
    return TPData(name="Test")


def test_loading_tournament(
    tpdata: TPData,
    all_matches: list[Match],
    all_entries: list[TPEntry],
    all_draws: list[TPDraw],
    all_courts: list[TPCourt],
) -> None:
    tpdata.add_matches(all_matches)
    assert tpdata.nmatches == 68
    tpdata.add_entries(all_entries)
    assert tpdata.nentries == 36
    tpdata.add_draws(all_draws)
    assert tpdata.ndraws == 9
    tpdata.add_courts(all_courts)
    assert tpdata.ncourts == 10


@pytest.mark.asyncio
async def test_loading_tournament_tpload(db_session: Session) -> None:
    tpdata = await load_tournament(db_session)
    assert tpdata.nmatches == 68
    assert tpdata.nentries == 36
