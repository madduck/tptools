import asyncio
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from functools import partial
from typing import cast

import click
from click_async_plugins import PluginLifespan, plugin, react_to_data_update
from httpx import URL

from tptools import Tournament

from .util import (
    CliContext,
    PostData,
    pass_clictx,
    post_data,
    validate_urls,
)

logger = logging.getLogger(__name__)


async def post_to_urls(
    tournament: Tournament, urls: list[URL], cookie: int, *, retries: int = 1
) -> None:
    logger.info(f"Tournament changed, posting to {len(urls)} URLs")

    def log_done_task(task: asyncio.Task[None]) -> None:
        logger.debug(f"Task done: {task}")

    data = PostData(cookie=cookie, data=tournament)

    async with asyncio.TaskGroup() as tg:
        for url in urls:
            task = tg.create_task(
                post_data(url, data, retries=retries),
                name=f"Posting Tournament to {url}",
            )
            logger.debug(f"Task for posting to {url}: {task}")
            task.add_done_callback(log_done_task)

    logger.info(f"Done posting to {len(urls)} URLs")


@asynccontextmanager
async def post_tournament(
    clictx: CliContext, urls: list[URL], retries: int
) -> PluginLifespan:
    callback = partial(post_to_urls, urls=urls, retries=retries, cookie=hash(clictx))
    updates_gen = cast(
        AsyncGenerator[Tournament],
        clictx.itc.updates("tournament", yield_immediately=True),
    )
    yield react_to_data_update(updates_gen, callback=callback)


@plugin
@click.option(
    "--url",
    "-u",
    "urls",
    metavar="URL",
    multiple=True,
    required=True,
    callback=validate_urls,
    help=(
        "POST data to this URL when the input changes (can be specified more than once)"
    ),
)
@click.option(
    "--retries",
    "-r",
    type=click.IntRange(min=1),
    default=1,
    show_default=True,
    help="Number of times to retry POSTing to URLs",
)
@pass_clictx
async def post(clictx: CliContext, urls: list[URL], retries: int) -> PluginLifespan:
    """Post raw (TP) JSON data to URLs on change"""

    async with post_tournament(clictx, urls, retries) as task:
        yield task
