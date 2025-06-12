import pytest
from sqlmodel import Session

from tptools.match import Match
from tptools.models import Entry
from tptools.tpdata import TPData, load_tournament


@pytest.fixture
def tpdata() -> TPData:
    return TPData(name="Test")


def test_loading_tournament(
    tpdata: TPData, all_matches: list[Match], all_entries: list[Entry]
) -> None:
    tpdata.add_matches(all_matches)
    tpdata.add_entries(all_entries)
    assert tpdata.nmatches == 68
    assert tpdata.nentries == 36


@pytest.mark.asyncio
async def test_loading_tournament_tpload(db_session: Session) -> None:
    tpdata = await load_tournament(db_session)
    assert tpdata.nmatches == 68
    assert tpdata.nentries == 36
