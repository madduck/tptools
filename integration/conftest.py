import pathlib
import sys
from collections.abc import Generator
from typing import Any

import pytest
from sqlalchemy.engine import URL
from sqlmodel import Session, create_engine, select

from tptools.match import Match
from tptools.matchmaker import MatchMaker
from tptools.models import Entry, PlayerMatch
from tptools.playermatchstatus import PlayerMatchStatus
from tptools.util import make_mdb_odbc_connstring

DB_PATH_BASE = pathlib.Path(__file__).parent / "anon_tournament"
if sys.platform == "win32" and (tp_path := DB_PATH_BASE.with_suffix(".TP")).exists():  # noqa: F841
    # could use pytest_addoption to export the database name to test against,
    # but why bother? Noone in their right mind develops on Windows, at least
    # I do not, and so if pytest runs on Windows *and* the TP file is present,
    # run all tests against that. Seems good enough.
    connection_url = URL.create(
        "access+pyodbc",
        query={
            "odbc_connect": make_mdb_odbc_connstring(
                tp_path, uid="Admin", pwd="d4R2GY76w2qzZ"
            )
        },
    )  # TODO: hide the password
else:
    db_path = DB_PATH_BASE.with_suffix(".sqlite")
    connection_url = URL.create("sqlite", database=str(db_path))


def pytest_report_header(config: pytest.Config) -> str | list[str]:
    return f"Connection string for integration tests: {connection_url}"


@pytest.fixture(scope="session")
def db_session() -> Generator[Session, Any]:
    engine = create_engine(connection_url)
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

    def teardown() -> None:
        session.rollback()
        session.close()

    atexit.register(teardown)


@pytest.fixture
def all_entries(db_session: Session) -> Generator[list[Entry], Any]:
    yield list(db_session.exec(select(Entry)))


@pytest.fixture
def all_playermatches(db_session: Session) -> Generator[list[PlayerMatch], Any]:
    yield list(db_session.exec(select(PlayerMatch)))


@pytest.fixture
def all_matches(all_playermatches: list[PlayerMatch]) -> set[Match]:
    mm = MatchMaker()
    for pm in all_playermatches:
        if pm.status in (PlayerMatchStatus.BYE, PlayerMatchStatus.PLAYER):
            continue
        mm.add_playermatch(pm)

    assert len(mm.unmatched) == 0
    return mm.matches
