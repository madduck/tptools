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

from tptools.tpsrv.cli import (
    make_app,
)
from tptools.tpsrv.debug import debug_key_press_handler
from tptools.tpsrv.post import post_tournament
from tptools.tpsrv.sq_stdout import print_sqdata
from tptools.tpsrv.squoresrv import setup_for_squore
from tptools.tpsrv.stdout import print_tournament
from tptools.tpsrv.tp import make_engine, tp_source
from tptools.tpsrv.tp_recv import setup_to_receive_tournament_post
from tptools.tpsrv.util import CliContext
from tptools.util import silence_logger

logging.getLogger().setLevel(logging.DEBUG)

if not sys.warnoptions:
    warnings.simplefilter("default")
    logging.captureWarnings(True)

for name, level in (
    ("watchfiles.main", logging.WARNING),
    ("uvicorn.error", logging.WARNING),
    ("tptools.tpmatch", logging.INFO),
):
    silence_logger(name, level=level)

logger = logging.getLogger(__name__)

TP_FILE: pathlib.Path | None
if (envfile := os.getenv("TPFILE", os.getenv("TP_FILE"))) is None:
    TP_FILE = pathlib.Path(__file__).parent / "integration" / "anon_tournament.sqlite"
elif envfile.lower() in ("", "false", "0", "no"):
    TP_FILE = None
else:
    TP_FILE = pathlib.Path(envfile)

POSTURLS = [
    URL(os.getenv("POSTURL_TPTOOLS") or "http://localhost:8000/tptools/v1/tournament"),
    URL(os.getenv("POSTURL_TCBOARD") or "http://localhost:8001/tptools/v1/tournament"),
]


def _maybe_do_stdout(factories: list[PluginFactory]) -> None:
    if os.getenv("DOSTDOUT"):
        tpstdout_lifespan = partial(print_tournament, indent=1)
        factories.append(tpstdout_lifespan)
    else:
        logger.info(
            "Not printing tournament to stdout, set DOSTDOUT=1 if you want that"
        )


def _maybe_do_post(factories: list[PluginFactory]) -> None:
    if os.getenv("NOPOST"):
        logger.info("Not posting tournament to URLs as per $NOPOST")

    elif POSTURLS:
        urls = [url for url in POSTURLS if url and url.scheme.startswith("http")]
        logger.info(f"Posting to URLs: {','.join(str(u) for u in urls)}")
        tppost_lifespan = partial(
            post_tournament,
            urls=[url for url in POSTURLS if url and url.scheme.startswith("http")],
            retries=0,
        )
        factories.append(tppost_lifespan)
    else:
        logger.info("Not posting tournament anywhere, no URLs configured")


def _maybe_do_sqstdout(factories: list[PluginFactory]) -> None:
    if not os.getenv("NOSQSTDOUT"):
        sqstdout_lifespan = partial(print_sqdata, indent=1)
        factories.append(sqstdout_lifespan)
    else:
        logger.info("Not printing TPData to stdout as per $NOSQSTDOUT")


def _maybe_do_recv(factories: list[PluginFactory]) -> None:
    if not os.getenv("NORECV"):
        factories.append(setup_to_receive_tournament_post)
    else:
        logger.info("Not setting up to receive tournament via POST as per $NORECV")


@asynccontextmanager
async def app_lifespan(api: FastAPI) -> AsyncGenerator[None]:
    clictx = CliContext(api=api, itc=ITC())

    factories: list[PluginFactory] = [
        debug_key_press_handler,
        setup_for_squore,
    ]
    _maybe_do_stdout(factories)
    _maybe_do_post(factories)
    _maybe_do_sqstdout(factories)
    _maybe_do_recv(factories)

    try:
        async with AsyncExitStack() as stack:
            if TP_FILE is not None:
                engine = make_engine(
                    TP_FILE, os.getenv("TPUSER", "Admin"), os.getenv("TPPASS", "")
                )
                session = stack.enter_context(Session(engine))
                tp_lifespan = partial(tp_source, tp_file=TP_FILE, session=session)
                factories.append(tp_lifespan)

            tasks = await setup_plugins(factories, stack=stack, clictx=clictx)

            try:
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
                logger.info("Exiting…")

    except* RuntimeError:
        logger.exception("A runtime error occurred")

    except* Exception as exc:
        import ipdb

        ipdb.set_trace()  # noqa: E402 E702 I001 # fmt: skip
        _ = exc


app = make_app(lifespan=app_lifespan)
