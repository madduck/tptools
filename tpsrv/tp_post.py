# needed < 3.14 so that annotations aren't evaluated
from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from functools import partial
from typing import cast

import click
from click_async_plugins import PluginLifespan, plugin, react_to_data_update
from httpx import URL

from tptools.tpdata import TPData

from .util import (
    CliContext,
    pass_clictx,
    post_data,
    validate_urls,
)

logger = logging.getLogger(__name__)


async def _post_to_urls(tpdata: TPData, urls: list[URL], *, retries: int = 1) -> None:
    logger.info(f"TPData changed, posting to {len(urls)} URLs")

    def log_done_task(task: asyncio.Task[None]) -> None:
        logger.debug(f"Task done: {task}")

    async with asyncio.TaskGroup() as tg:
        for url in urls:
            task = tg.create_task(
                post_data(url, tpdata, retries=retries),
                name=f"Posting TPData to {url}",
            )
            logger.debug(f"Task for posting to {url}: {task}")
            task.add_done_callback(log_done_task)

    logger.info(f"Done posting to {len(urls)} URLs")


@asynccontextmanager
async def post_tpdata(
    clictx: CliContext, urls: list[URL], retries: int
) -> PluginLifespan:
    callback = partial(_post_to_urls, urls=urls, retries=retries)
    updates_gen = cast(AsyncGenerator[TPData], clictx.itc.updates("tpdata"))
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
async def tp_post(clictx: CliContext, urls: list[URL], retries: int) -> PluginLifespan:
    """Post raw (TP) JSON data to URLs on change"""

    async with post_tpdata(clictx, urls, retries) as task:
        yield task
