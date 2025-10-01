import pathlib
import sys
from collections.abc import Generator
from typing import Any

import pytest
from sqlalchemy.engine import URL
from sqlmodel import Session, create_engine, select

from tptools import Court, Draw, Entry, Match
from tptools.sqlmodels import TPCourt, TPDraw, TPEntry, TPPlayerMatch
from tptools.tpmatch import TPMatch, TPMatchMaker
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
def all_tpentries(db_session: Session) -> Generator[list[TPEntry], Any]:
    yield list(db_session.exec(select(TPEntry)))


@pytest.fixture
def all_entries(all_tpentries: list[TPEntry]) -> list[Entry]:
    return [Entry.from_tp_model(e) for e in all_tpentries]


@pytest.fixture
def all_tpdraws(db_session: Session) -> Generator[list[TPDraw], Any]:
    yield list(db_session.exec(select(TPDraw)))


@pytest.fixture
def all_draws(all_tpdraws: list[TPDraw]) -> list[Draw]:
    return [Draw.from_tp_model(d) for d in all_tpdraws]


@pytest.fixture
def all_tpcourts(db_session: Session) -> Generator[list[TPCourt], Any]:
    yield list(db_session.exec(select(TPCourt)))


@pytest.fixture
def all_courts(all_tpcourts: list[TPCourt]) -> list[Court]:
    return [Court.from_tp_model(c) for c in all_tpcourts]


@pytest.fixture
def all_tpplayermatches(db_session: Session) -> Generator[list[TPPlayerMatch], Any]:
    yield list(db_session.exec(select(TPPlayerMatch)))


@pytest.fixture
def all_tpmatches(all_tpplayermatches: list[TPPlayerMatch]) -> set[TPMatch]:
    mm = TPMatchMaker()
    for pm in all_tpplayermatches:
        if pm.status in (TPPlayerMatch.Status.BYE, TPPlayerMatch.Status.PLAYER):
            continue
        mm.add_playermatch(pm)

    assert len(mm.unmatched) == 0
    return mm.matches


@pytest.fixture
def all_matches(all_tpmatches: list[TPMatch]) -> list[Match]:
    return [Match.from_tpmatch(m) for m in all_tpmatches]
