import asyncio
import logging
import pathlib
import shutil
import sqlite3
from collections.abc import Generator
from typing import Any

import click
import pytest
from click.testing import CliRunner
from pytest import LogCaptureFixture, MonkeyPatch
from pytest_mock import MockerFixture
from sqlalchemy import Engine
from sqlalchemy.exc import (
    DatabaseError,
    DBAPIError,
    NoSuchModuleError,
    OperationalError,
    ProgrammingError,
)
from sqlmodel import Session, create_engine

from tptools import Tournament
from tptools.draw import InvalidDrawType
from tptools.tpsrv.tp import (
    TP_DEFAULT_USER,
    make_access_url,
    make_engine,
    make_sqlite_url,
    tp,
    tp_source,
    try_make_engine_for_url,
)
from tptools.tpsrv.util import CliContext

from .conftest import InvokePlugin, MakeFactory, running, wait_for

SQLITE_EXPORT = (
    pathlib.Path(__file__).parents[2] / "integration" / "anon_tournament.sqlite"
)
# see integration/test_loading_tournament.py
NENTRIES, NDRAWS, NCOURTS, NMATCHES = 36, 9, 10, 68


@pytest.fixture
def tpfile(tmp_path: pathlib.Path) -> pathlib.Path:
    """A private copy of the anonymised SQLite export of a tournament"""
    dest = tmp_path / "tournament.sqlite"
    shutil.copy(SQLITE_EXPORT, dest)
    return dest


@pytest.fixture
def textfile(tmp_path: pathlib.Path) -> pathlib.Path:
    path = tmp_path / "notes.txt"
    path.write_text("This is not a database, and certainly not a TP file.\n" * 20)
    return path


@pytest.fixture
def emptydb(tmp_path: pathlib.Path) -> pathlib.Path:
    """A valid SQLite database, but not one that TP exported"""
    path = tmp_path / "empty.sqlite"
    sqlite3.connect(path).close()
    return path


@pytest.fixture(autouse=True)
def dispose_engines(mocker: MockerFixture) -> Generator[None]:
    """Close the pooled SQLite connections of every engine made during a test"""
    engines: list[Engine] = []

    def tracking(*args: Any, **kwargs: Any) -> Engine:
        engines.append(engine := create_engine(*args, **kwargs))
        return engine

    mocker.patch("tptools.tpsrv.tp.create_engine", tracking)
    yield
    for engine in engines:
        engine.dispose()


@pytest.fixture
def new_engine(tpfile: pathlib.Path) -> Generator[Engine]:
    engine = create_engine(make_sqlite_url(tpfile))
    yield engine
    engine.dispose()


def loaded(clictx: CliContext) -> bool:
    return isinstance(clictx.itc.get("tournament"), Tournament)


# URL builders


def test_make_sqlite_url(tpfile: pathlib.Path) -> None:
    url = make_sqlite_url(tpfile)
    assert url.drivername == "sqlite"
    assert url.database == str(tpfile)


def test_make_sqlite_url_is_absolute(
    tpfile: pathlib.Path, monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.chdir(tpfile.parent)
    url = make_sqlite_url(pathlib.Path(tpfile.name))
    assert url.database == str(tpfile)


def test_make_access_url(tmp_path: pathlib.Path) -> None:
    tp_file = tmp_path / "t.TP"
    url = make_access_url(tp_file, user="Admin", password="s3cret")

    assert url.drivername == "access+pyodbc"
    connstr = url.query["odbc_connect"]
    assert isinstance(connstr, str)
    assert "Microsoft Access Driver" in connstr
    assert f"DBQ={tp_file}" in connstr
    assert "Pwd=s3cret" in connstr
    assert "Uid" not in connstr, "Admin is the default user, and not passed"


def test_make_access_url_with_other_user(tmp_path: pathlib.Path) -> None:
    url = make_access_url(tmp_path / "t.TP", user="alice", password="pw")
    assert "Uid=alice" in str(url.query["odbc_connect"])


# engines


def test_try_make_engine_for_valid_export(tpfile: pathlib.Path) -> None:
    engine = try_make_engine_for_url(make_sqlite_url(tpfile))
    assert isinstance(engine, Engine)
    assert engine.url.database == str(tpfile)


def test_try_make_engine_closes_its_verification_connection(
    tpfile: pathlib.Path, mocker: MockerFixture
) -> None:
    conn = mocker.MagicMock()
    engine = mocker.Mock()
    engine.connect.return_value = conn
    mocker.patch("tptools.tpsrv.tp.create_engine", return_value=engine)

    assert try_make_engine_for_url(make_sqlite_url(tpfile)) is engine

    conn.execute.assert_called_once()
    conn.close.assert_called_once_with()


def test_try_make_engine_rejects_files_that_are_not_databases(
    textfile: pathlib.Path,
) -> None:
    with pytest.raises(DatabaseError, match="not a database"):
        try_make_engine_for_url(make_sqlite_url(textfile))


def test_try_make_engine_rejects_databases_that_are_not_tp_exports(
    emptydb: pathlib.Path,
) -> None:
    with pytest.raises(OperationalError, match="no such table"):
        try_make_engine_for_url(make_sqlite_url(emptydb))


def test_try_make_engine_without_verification(textfile: pathlib.Path) -> None:
    engine = try_make_engine_for_url(make_sqlite_url(textfile), verify=False)
    assert isinstance(engine, Engine)


def test_make_engine_for_valid_export(tpfile: pathlib.Path) -> None:
    engine = make_engine(tpfile, TP_DEFAULT_USER, "")
    assert isinstance(engine, Engine)
    with Session(engine) as session:
        assert session.connection() is not None


@pytest.mark.parametrize("path", ["textfile", "emptydb"])
def test_make_engine_gives_none_for_unusable_files(
    path: str, request: pytest.FixtureRequest
) -> None:
    assert make_engine(request.getfixturevalue(path), TP_DEFAULT_USER, "") is None


@pytest.fixture
def try_make(mocker: MockerFixture) -> Any:
    return mocker.patch("tptools.tpsrv.tp.try_make_engine_for_url")


def test_make_engine_prefers_access_and_passes_credentials(
    try_make: Any, tmp_path: pathlib.Path, mocker: MockerFixture
) -> None:
    sentinel = mocker.sentinel.engine
    try_make.return_value = sentinel
    tp_file = tmp_path / "t.TP"

    assert make_engine(tp_file, "alice", "pw") is sentinel

    try_make.assert_called_once()
    (url,) = try_make.call_args.args
    assert url.drivername == "access+pyodbc"
    assert "Uid=alice" in url.query["odbc_connect"]
    assert "Pwd=pw" in url.query["odbc_connect"]


def test_make_engine_falls_back_to_sqlite_without_access_driver(
    try_make: Any,
    tmp_path: pathlib.Path,
    mocker: MockerFixture,
    caplog: LogCaptureFixture,
) -> None:
    sentinel = mocker.sentinel.engine
    try_make.side_effect = [NoSuchModuleError("access.pyodbc"), sentinel]

    with caplog.at_level(logging.DEBUG):
        assert make_engine(tmp_path / "t.TP", "Admin", "") is sentinel

    drivers = [c.args[0].drivername for c in try_make.call_args_list]
    assert drivers == ["access+pyodbc", "sqlite"]
    assert "No SQLAlchemy module to handle" in caplog.text


@pytest.mark.parametrize(
    "exc",
    [
        DatabaseError("stmt", {}, Exception("file is not a database")),
        DBAPIError("stmt", {}, Exception("driver trouble")),
        ProgrammingError("stmt", {}, Exception("some other programming error")),
    ],
    ids=["DatabaseError", "DBAPIError", "ProgrammingError"],
)
def test_make_engine_tries_next_url_after_database_errors(
    try_make: Any, tmp_path: pathlib.Path, mocker: MockerFixture, exc: Exception
) -> None:
    sentinel = mocker.sentinel.engine
    try_make.side_effect = [exc, sentinel]

    assert make_engine(tmp_path / "t.TP", "Admin", "") is sentinel
    assert try_make.call_count == 2


def test_make_engine_logs_why_a_url_could_not_be_opened(
    try_make: Any, tmp_path: pathlib.Path, caplog: LogCaptureFixture
) -> None:
    try_make.side_effect = [
        DatabaseError("stmt", {}, Exception("file is not a database")),
        DatabaseError("stmt", {}, Exception("still not a database")),
    ]
    with caplog.at_level(logging.DEBUG):
        assert make_engine(tmp_path / "t.TP", "Admin", "") is None
    assert caplog.text.count("Cannot open") == 2


def test_make_engine_password_needed(try_make: Any, tmp_path: pathlib.Path) -> None:
    try_make.side_effect = ProgrammingError(
        "stmt", {}, Exception("[ODBC] Not a valid password.")
    )

    with pytest.raises(RuntimeError, match="Password needed to access .*t.TP"):
        make_engine(tmp_path / "t.TP", "Admin", "")

    assert try_make.call_count == 1, "no point in trying the other formats"


def test_make_engine_nothing_works(try_make: Any, tmp_path: pathlib.Path) -> None:
    try_make.side_effect = NoSuchModuleError("access"), NoSuchModuleError("sqlite")
    assert make_engine(tmp_path / "t.TP", "Admin", "") is None


# tp_source


@pytest.fixture
def session(new_engine: Engine) -> Generator[Session]:
    with Session(new_engine) as session:
        yield session


@pytest.mark.asyncio
async def test_tp_source_loads_tournament_on_startup(
    clictx: CliContext, tpfile: pathlib.Path, session: Session
) -> None:
    async with running(tp_source(clictx, tpfile, session)):
        await wait_for(lambda: loaded(clictx))

    tournament = clictx.itc.get("tournament")
    assert tournament.nentries == NENTRIES
    assert tournament.ndraws == NDRAWS
    assert tournament.ncourts == NCOURTS
    assert tournament.nmatches == NMATCHES


@pytest.mark.asyncio
async def test_tp_source_exposes_the_watcher(
    clictx: CliContext, tpfile: pathlib.Path, session: Session
) -> None:
    before = clictx.watcher
    assert before is None

    async with running(tp_source(clictx, tpfile, session)):
        watcher = clictx.watcher
        assert watcher is not None
        assert len(watcher.callbacks) == 1


@pytest.mark.asyncio
async def test_tp_source_notifies_subscribers(
    clictx: CliContext, tpfile: pathlib.Path, session: Session
) -> None:
    received: list[Any] = []

    async def listen() -> None:
        async for t in clictx.itc.updates("tournament", yield_immediately=False):
            received.append(t)

    listener = asyncio.create_task(listen())
    try:
        await wait_for(lambda: clictx.itc.has_subscribers("tournament"))
        async with running(tp_source(clictx, tpfile, session)):
            await wait_for(lambda: len(received) == 1)
    finally:
        listener.cancel()

    assert isinstance(received[0], Tournament)


@pytest.mark.asyncio
async def test_tp_source_no_fire_on_startup(
    clictx: CliContext, tpfile: pathlib.Path, session: Session
) -> None:
    async with running(tp_source(clictx, tpfile, session, no_fire_on_startup=True)):
        await asyncio.sleep(0.3)
        assert not loaded(clictx), "nothing changed, so nothing should be loaded"

        # which is also how the debug plugin's ^R forces a reload
        assert clictx.watcher is not None
        clictx.watcher.fire()
        await wait_for(lambda: loaded(clictx))


@pytest.mark.asyncio
async def test_tp_source_reloads_on_every_change(
    clictx: CliContext, tpfile: pathlib.Path, session: Session, mocker: MockerFixture
) -> None:
    expire_all = mocker.spy(session, "expire_all")
    loader = mocker.patch(
        "tptools.tpsrv.tp.load_tournament",
        side_effect=[Tournament(name="first"), Tournament(name="second")],
    )

    async with running(tp_source(clictx, tpfile, session)):
        await wait_for(lambda: loader.await_count == 1)
        assert clictx.itc.get("tournament").name == "first"

        assert clictx.watcher is not None
        clictx.watcher.fire()
        await wait_for(lambda: loader.await_count == 2)
        assert clictx.itc.get("tournament").name == "second"

    # stale objects must not be served from the session cache
    assert expire_all.call_count == 2
    loader.assert_awaited_with(session)


@pytest.mark.asyncio
async def test_tp_source_refuses_second_source(
    clictx: CliContext, tpfile: pathlib.Path, session: Session
) -> None:
    clictx.itc.set("tpdata", object())

    with pytest.raises(click.ClickException, match="Another TP source is already"):
        async with tp_source(clictx, tpfile, session):
            pytest.fail("must not get this far")  # pragma: nocover

    assert clictx.watcher is None


@pytest.mark.asyncio
async def test_tp_source_unsupported_draw_type_is_a_clickexception(
    clictx: CliContext, tpfile: pathlib.Path, session: Session, mocker: MockerFixture
) -> None:
    mocker.patch("tptools.tpsrv.tp.load_tournament", side_effect=InvalidDrawType(99))

    async with tp_source(clictx, tpfile, session) as task:
        assert task is not None
        with pytest.raises(
            click.ClickException, match="Unable to handle draw type with ID 99"
        ):
            await asyncio.wait_for(task, 5)

    assert not loaded(clictx)


@pytest.mark.asyncio
async def test_tp_source_stops_the_observer_on_exit(
    clictx: CliContext, tpfile: pathlib.Path, session: Session
) -> None:
    async with running(tp_source(clictx, tpfile, session)):
        assert clictx.watcher is not None
        observer = clictx.watcher._observer  # noqa: SLF001
        assert observer.is_alive()

    assert not observer.is_alive()


# the command


def test_tp_help(invoke_plugin: InvokePlugin) -> None:
    result = invoke_plugin(tp, ["--help"])
    assert result.exit_code == 0
    assert "Obtain match and player data from a TP file" in result.output
    for item in ("TP_FILE", "--user", "--password", "--no-fire-on-startup"):
        assert item in result.output
    assert f"[default: {TP_DEFAULT_USER}]" in result.output


def test_tp_requires_a_file(invoke_plugin: InvokePlugin) -> None:
    result = invoke_plugin(tp, [])
    assert result.exit_code == 2
    assert "Missing argument 'TP_FILE'" in result.output


def test_tp_takes_only_one_file(
    invoke_plugin: InvokePlugin, tpfile: pathlib.Path
) -> None:
    result = invoke_plugin(tp, [str(tpfile), str(tpfile)])
    assert result.exit_code == 2
    assert "unexpected extra argument" in result.output


@pytest.mark.asyncio
async def test_tp_nonexistent_file(
    make_factory: MakeFactory, tmp_path: pathlib.Path
) -> None:
    missing = tmp_path / "missing.TP"
    with pytest.raises(click.ClickException, match=f"File {missing} does not exist"):
        async with make_factory(tp, [str(missing)])():
            pytest.fail("must not get this far")  # pragma: nocover


@pytest.mark.asyncio
@pytest.mark.parametrize("path", ["textfile", "emptydb"])
async def test_tp_unreadable_file(
    make_factory: MakeFactory, path: str, request: pytest.FixtureRequest
) -> None:
    file = request.getfixturevalue(path)
    with pytest.raises(click.ClickException, match=f"File {file} cannot be read"):
        async with make_factory(tp, [str(file)])():
            pytest.fail("must not get this far")  # pragma: nocover


@pytest.mark.asyncio
async def test_tp_password_needed(
    make_factory: MakeFactory, tpfile: pathlib.Path, mocker: MockerFixture
) -> None:
    mocker.patch(
        "tptools.tpsrv.tp.make_engine",
        side_effect=RuntimeError("Password needed to access foo.TP"),
    )
    with pytest.raises(click.ClickException) as exc:
        async with make_factory(tp, [str(tpfile)])():
            pytest.fail("must not get this far")  # pragma: nocover

    assert exc.value.message == "Password needed to access foo.TP"
    assert isinstance(exc.value.__cause__, RuntimeError)


@pytest.mark.asyncio
async def test_tp_command_loads_the_file(
    make_factory: MakeFactory, clictx: CliContext, tpfile: pathlib.Path
) -> None:
    async with running(make_factory(tp, [str(tpfile)])()):
        await wait_for(lambda: loaded(clictx))

    assert clictx.itc.get("tournament").nmatches == NMATCHES
    assert clictx.watcher is not None


@pytest.mark.asyncio
async def test_tp_command_closes_session_on_exit(
    make_factory: MakeFactory, tpfile: pathlib.Path, mocker: MockerFixture
) -> None:
    sessions: list[Any] = []
    real_session = Session

    def tracking(*args: Any, **kwargs: Any) -> Session:
        sessions.append(mocker.spy(s := real_session(*args, **kwargs), "close"))
        return s

    mocker.patch("tptools.tpsrv.tp.Session", tracking)

    async with running(make_factory(tp, [str(tpfile)])()):
        assert sessions[0].call_count == 0

    assert sessions[0].call_count == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "args, user, fire",
    [
        ([], "Admin", True),
        (["-u", "alice"], "alice", True),
        (["--user", "bob", "--no-fire-on-startup"], "bob", False),
    ],
)
async def test_tp_command_options(
    make_factory: MakeFactory,
    clictx: CliContext,
    tpfile: pathlib.Path,
    new_engine: Engine,
    mocker: MockerFixture,
    args: list[str],
    user: str,
    fire: bool,
) -> None:
    make = mocker.patch("tptools.tpsrv.tp.make_engine", return_value=new_engine)
    source = mocker.patch("tptools.tpsrv.tp.tp_source", wraps=tp_source)

    async with running(make_factory(tp, [str(tpfile), "-p", "pw", *args])()):
        await asyncio.sleep(0.1)

    make.assert_called_once_with(tpfile, user, "pw")
    assert source.call_args.kwargs == {"no_fire_on_startup": not fire}


@pytest.mark.asyncio
async def test_tp_command_prompts_for_password_if_asked_to(
    runner: CliRunner,
    make_factory: MakeFactory,
    tpfile: pathlib.Path,
    new_engine: Engine,
    mocker: MockerFixture,
) -> None:
    make = mocker.patch("tptools.tpsrv.tp.make_engine", return_value=new_engine)

    with runner.isolation(input="typed-in\n") as (stdout, _, _):
        factory = make_factory(tp, [str(tpfile), "--password"])

    output = stdout.getvalue().decode()
    assert "Enter the password to access the TP file" in output
    assert "typed-in" not in output, "input is not echoed"

    async with running(factory()):
        pass
    make.assert_called_once_with(tpfile, "Admin", "typed-in")


@pytest.mark.asyncio
async def test_tp_command_does_not_prompt_for_password_by_default(
    runner: CliRunner,
    make_factory: MakeFactory,
    tpfile: pathlib.Path,
    new_engine: Engine,
    mocker: MockerFixture,
) -> None:
    make = mocker.patch("tptools.tpsrv.tp.make_engine", return_value=new_engine)

    # with no input available, prompting would abort
    with runner.isolation(input="") as (stdout, _, _):
        factory = make_factory(tp, [str(tpfile)])

    assert b"password" not in stdout.getvalue().lower()
    async with running(factory()):
        pass
    assert make.call_args.args[:2] == (tpfile, "Admin")
