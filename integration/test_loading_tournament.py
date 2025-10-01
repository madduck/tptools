import pytest
from sqlmodel import Session

from tptools import Court, Draw, Entry, Match, Tournament, load_tournament


@pytest.fixture
def tournament() -> Tournament:
    return Tournament(name="Test")


def test_loading_tournament(
    tournament: Tournament,
    all_matches: list[Match],
    all_entries: list[Entry],
    all_draws: list[Draw],
    all_courts: list[Court],
) -> None:
    tournament.add_matches(all_matches)
    assert tournament.nmatches == 68
    tournament.add_entries(all_entries)
    assert tournament.nentries == 36
    tournament.add_draws(all_draws)
    assert tournament.ndraws == 9
    tournament.add_courts(all_courts)
    assert tournament.ncourts == 10


@pytest.mark.asyncio
async def test_loading_tournament_tpload(db_session: Session) -> None:
    tournament = await load_tournament(db_session)
    assert tournament.nmatches == 68
    assert tournament.nentries == 36
