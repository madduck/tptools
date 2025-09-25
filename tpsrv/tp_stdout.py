# needed < 3.14 so that annotations aren't evaluated
from __future__ import annotations

import logging
import sys
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from functools import partial
from typing import cast

import click
from click_async_plugins import PluginLifespan, plugin

from tptools.tpdata import TPData
from tptools.util import nonblocking_write

from .util import TpsrvContext, react_to_data_update

logger = logging.getLogger(__name__)


async def tpdata_model_dump_json(
    tpdata: TPData,
    *,
    indent: int | None = None,
    to_json_fn: Callable[[TPData, int | None], str] | None = None,
) -> None:
    logger.info("TPData changed, printing JSON to stdout")

    if to_json_fn is None:
        data = tpdata.model_dump_json(indent=indent)

    else:
        data = to_json_fn(tpdata, indent)

    nonblocking_write(data, file=sys.stdout)


@asynccontextmanager
async def print_tpdata_to_stdout(
    tpsrv: TpsrvContext, indent: int | None
) -> PluginLifespan:
    callback = partial(tpdata_model_dump_json, indent=indent)
    updates_gen = cast(AsyncGenerator[TPData], tpsrv.itc.updates("tpdata"))
    yield react_to_data_update(updates_gen, callback=callback)


@plugin
@click.option(
    "--indent",
    "-i",
    type=click.IntRange(min=1),
    help="Indent JSON output this many characters",
)
async def tp_stdout(tpsrv: TpsrvContext, indent: int | None) -> PluginLifespan:
    """Output raw (TP) data as JSON to stdout whenever it changes"""

    async with print_tpdata_to_stdout(tpsrv, indent) as task:
        yield task
