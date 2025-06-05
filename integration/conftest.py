import pathlib
from collections.abc import Generator
from typing import Any

import pytest
from sqlalchemy import ScalarResult
from sqlmodel import Session, create_engine, select

from tptools.match import Match
from tptools.matchmaker import MatchMaker
from tptools.models import Entry, PlayerMatch
from tptools.playermatchstatus import PlayerMatchStatus


@pytest.fixture(scope="session")
def sqlite_ro_session(
    sqlite_db_path: pathlib.Path = pathlib.Path(__file__).parent
    / "anon_tournament.sqlite",
) -> Generator[Session, Any]:
    engine = create_engine(f"sqlite:///{sqlite_db_path}")
    session = Session(engine)
    session.begin()
    yield session
    # we don't rollback & close during testing, as error output of failed tests might
    # include repr() of model instances, causing lazy queries that would otherwise fail
    # as detached from the session. I tried eager loading, both using lazy="selectin" in
    # the model relationships, as well as using options on select, but could not get the
    # wanted result.
    #
    # session.rollback()
    # session.close()
    import atexit

    def teardown():
        session.rollback()
        session.close()

    atexit.register(teardown)


@pytest.fixture
def all_entries(sqlite_ro_session: Session) -> Generator[list[Entry], Any]:
    yield list(sqlite_ro_session.exec(select(Entry)))


@pytest.fixture
def all_playermatches(sqlite_ro_session: Session) -> Generator[list[PlayerMatch], Any]:
    yield list(sqlite_ro_session.exec(select(PlayerMatch)))


@pytest.fixture
def all_matches(all_playermatches: list[PlayerMatch]) -> set[Match]:
    mm = MatchMaker()
    for pm in all_playermatches:
        if pm.status in (PlayerMatchStatus.BYE, PlayerMatchStatus.PLAYER):
            continue
        mm.add_playermatch(pm)

    assert len(mm.unmatched) == 0
    return mm.matches
