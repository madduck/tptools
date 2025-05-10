import pathlib
from collections.abc import Generator
from typing import Any

import pytest
from sqlmodel import Session, create_engine, select

from tptools.models import PlayerMatch


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


@pytest.fixture(scope="module")
def all_playermatches(sqlite_ro_session: Session) -> ScalarResult[PlayerMatch]:
    return sqlite_ro_session.exec(select(PlayerMatch))
