import logging
import pathlib
from contextlib import asynccontextmanager, closing
from types import MappingProxyType
from typing import Never

import click
from click_async_plugins import PluginLifespan, plugin
from sqlalchemy import URL, Engine
from sqlalchemy.exc import (
    DatabaseError,
    DBAPIError,
    NoSuchModuleError,
    ProgrammingError,
)
from sqlmodel import Session, create_engine, select

from tptools import load_tournament
from tptools.draw import InvalidDrawType
from tptools.filewatcher import FileWatcher, StateType
from tptools.sqlmodels import TPSetting
from tptools.util import make_mdb_odbc_connstring

from .util import CliContext, pass_clictx

TP_DEFAULT_USER = "Admin"

logger = logging.getLogger(__name__)


def make_access_url(tp_file: pathlib.Path, *, user: str, password: str) -> URL:
    return URL.create(
        "access+pyodbc",
        query={
            "odbc_connect": make_mdb_odbc_connstring(tp_file, uid=user, pwd=password)
        },
    )


def make_sqlite_url(tp_file: pathlib.Path) -> URL:
    return URL.create("sqlite", database=str(tp_file.absolute()))


def try_make_engine_for_url(url: URL, *, verify: bool = True) -> Engine | Never:
    engine = create_engine(url)
    if verify:
        with closing(engine.connect()) as conn:
            logger.debug(f"SQL connection for testing {url}: {conn}")
            # duck-type test the database. This is necessary because
            # e.g. SQLite lets you open any file whatsoever without
            # an error, even if the file is not a database. So to
            # verify that the file is actually a valid TP SQLite export.
            # see if we can query one of the known models:
            _ = conn.execute(select(TPSetting))
    return engine


@asynccontextmanager
async def tp_source(
    clictx: CliContext,
    tp_file: pathlib.Path,
    session: Session,
    *,
    no_fire_on_startup: bool = False,
) -> PluginLifespan:
    if clictx.itc.knows_about("tpdata"):
        raise click.ClickException("Another TP source is already registered")

    async def callback() -> StateType:
        logger.info("Loading tournament…")
        try:
            session.expire_all()
            tournament = await load_tournament(session)
            clictx.itc.set("tournament", tournament)
            return MappingProxyType({})

        except InvalidDrawType as err:
            raise click.ClickException(err.args[0]) from err

    watcher = FileWatcher(tp_file, fire_once_asap=not no_fire_on_startup)
    watcher.register_callback(callback)
    async with watcher():
        logger.info(f"Starting FileWatcher reactor for {tp_file}")
        yield watcher.reactor_task()


@plugin
@click.argument(
    "TP_FILE",
    type=click.Path(path_type=pathlib.Path),
    nargs=1,
)
@click.option(
    "--user",
    "-u",
    metavar="UID",
    default=TP_DEFAULT_USER,
    show_default=True,
    help="User name to access TP file",
)
@click.password_option(
    "--password",
    "-p",
    prompt_required=False,
    confirmation_prompt=False,
    prompt="Enter the password to access the TP file",
    metavar="PASSWORD",
    help="Password to access TP file",
)
@click.option(
    "--no-fire-on-startup",
    is_flag=True,
    help="Do not load data ASAP on startup, only on change",
)
# TODO: how to use pollfreq? See https://github.com/gorakhargosh/watchdog/issues/1116
# @click.option(
#     "--pollfreq",
#     "-f",
#     metavar="SECONDS",
#     type=click.IntRange(min=1),
#     help=("Frequency in seconds to poll TP file in the absence of inotify"),
#     default=30,
#     show_default=True,
# )
@pass_clictx
async def tp(
    clictx: CliContext,
    tp_file: pathlib.Path,
    user: str,
    password: str,
    no_fire_on_startup: bool,
    # pollfreq: int,
) -> PluginLifespan:
    """Obtain match and player data from a TP file (or SQLite)"""

    if not tp_file.exists():
        raise click.ClickException(f"File {tp_file} does not exist")

    engine: Engine | None = None
    for url in [
        make_access_url(tp_file, user=user, password=password),
        make_sqlite_url(tp_file),
    ]:
        try:
            engine = try_make_engine_for_url(url)

        except NoSuchModuleError:
            logger.debug(f"No SQLAlchemy module to handle {url}")

        except ProgrammingError as exc:
            if "Not a valid password" in exc.args[0]:
                raise click.ClickException(
                    f"Password needed to access {tp_file}"
                ) from exc

        except (DatabaseError, DBAPIError) as exc:
            logger.debug(f"Cannot open {url}: {exc.args[0]}")

    if engine is None:
        raise click.ClickException(f"File {tp_file} cannot be read")

    with Session(engine) as session:
        async with tp_source(
            clictx, tp_file, session, no_fire_on_startup=no_fire_on_startup
        ) as task:
            yield task
