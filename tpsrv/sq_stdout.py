# needed < 3.14 so that annotations aren't evaluated
from __future__ import annotations

import logging
import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from functools import partial
from typing import cast

import click
from click_async_plugins import PluginLifespan, plugin, react_to_data_update

from tptools.export import Tournament
from tptools.export.tournament import MatchStatusSelectionParams
from tptools.ext.squore import Config, MatchesFeed
from tptools.util import nonblocking_write

from .util import CliContext, pass_clictx

logger = logging.getLogger(__name__)


async def matches_feed_json(
    tournament: Tournament,
    *,
    indent: int | None = None,
) -> None:
    logger.info("Tournament changed, printing Squore data to stdout")

    data = MatchesFeed(tournament=tournament, config=Config()).model_dump_json(
        indent=indent,
        context={
            "matchstatusselectionparams": MatchStatusSelectionParams(
                include_not_ready=True
            ),
        },
    )
    nonblocking_write(data, file=sys.stdout)


@asynccontextmanager
async def print_sqdata(clictx: CliContext, indent: int | None) -> PluginLifespan:
    callback = partial(matches_feed_json, indent=indent)
    updates_gen = cast(AsyncGenerator[Tournament], clictx.itc.updates("tournament"))
    yield react_to_data_update(updates_gen, callback=callback)


@plugin
@click.option(
    "--indent",
    "-i",
    type=click.IntRange(min=1),
    help="Indent JSON output this many characters",
)
@pass_clictx
async def sq_stdout(clictx: CliContext, indent: int | None) -> PluginLifespan:
    """Output data as sent to Squore to stdout whenever the tournament changes"""

    async with print_sqdata(clictx, indent) as task:
        yield task
