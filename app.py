import asyncio
import logging
import os
import pathlib
import sys
import warnings
from collections.abc import AsyncGenerator
from contextlib import AsyncExitStack, asynccontextmanager
from functools import partial

from click_async_plugins import (
    ITC,
    PluginFactory,
    create_plugin_task,
    setup_plugins,
)
from fastapi import FastAPI
from httpx import URL
from sqlmodel import Session

from tpsrv.cli import (
    make_app,
)
from tpsrv.debug import debug_key_press_handler
from tpsrv.post import post_tournament
from tpsrv.sq_stdout import print_sqdata
from tpsrv.squoresrv import setup_for_squore
from tpsrv.stdout import print_tournament
from tpsrv.tp import make_sqlite_url, tp_source, try_make_engine_for_url
from tpsrv.tp_proc import tp_proc
from tpsrv.util import CliContext
from tptools.util import silence_logger

logging.getLogger().setLevel(logging.DEBUG)

if not sys.warnoptions:
    warnings.simplefilter("default")
    logging.captureWarnings(True)

for name, level in (
    ("watchfiles.main", logging.WARNING),
    ("uvicorn.error", logging.WARNING),
    ("tptools.matchmaker", logging.INFO),
    ("tptools.match", logging.INFO),
):
    silence_logger(name, level=level)

logger = logging.getLogger(__name__)

TP_FILE = pathlib.Path(__file__).parent / "integration" / "anon_tournament.sqlite"
POSTURL = URL("http://localhost:8001")


@asynccontextmanager
async def app_lifespan(api: FastAPI) -> AsyncGenerator[None]:
    clictx = CliContext(api=api, itc=ITC())

    engine = try_make_engine_for_url(make_sqlite_url(TP_FILE))

    with Session(engine) as session:
        tp_lifespan = partial(tp_source, tp_file=TP_FILE, session=session)

        factories: list[PluginFactory] = [
            debug_key_press_handler,
            tp_lifespan,
            tp_proc,
            setup_for_squore,
        ]

        if not os.getenv("NOTPSTDOUT"):
            tpstdout_lifespan = partial(print_tournament, indent=1)
            factories.append(tpstdout_lifespan)
        else:
            logger.info("Not printing TPData to stdout as per $NOTPSTDOUT")
        if not os.getenv("NOTPPOST"):
            tppost_lifespan = partial(post_tournament, urls=[POSTURL], retries=0)
            factories.append(tppost_lifespan)
        else:
            logger.info("Not posting TPData to URLs as per $NOTPPOST")
        if not os.getenv("NOSQSTDOUT"):
            sqstdout_lifespan = partial(print_sqdata, indent=1)
            factories.append(sqstdout_lifespan)
        else:
            logger.info("Not printing TPData to stdout as per $NOSQSTDOUT")

        try:
            async with AsyncExitStack() as stack:
                tasks = await setup_plugins(factories, stack=stack, clictx=clictx)

                async with asyncio.TaskGroup() as tg:
                    plugin_task = partial(
                        create_plugin_task, create_task_fn=tg.create_task
                    )
                    for task in tasks:
                        plugin_task(task)
                    logger.debug("Tasks:")
                    for t in tg._tasks:
                        logger.debug(f"  {t}")
                    yield
                    raise asyncio.CancelledError

        except asyncio.CancelledError:
            pass


app = make_app(lifespan=app_lifespan)
