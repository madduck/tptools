# needed < 3.14 so that annotations aren't evaluated
from __future__ import annotations

import logging
import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from functools import partial
from typing import cast

import click
from click_async_plugins import PluginLifespan, plugin

from tptools.export import Tournament
from tptools.export.tournament import MatchStatusSelectionParams
from tptools.tpsrv.util import react_to_data_update
from tptools.util import nonblocking_write

from .util import TpsrvContext

logger = logging.getLogger(__name__)


async def tournament_model_dump_json(
    tournament: Tournament,
    *,
    indent: int | None = None,
) -> None:
    logger.info("Tournament changed, printing JSON to stdout")

    data = tournament.model_dump_json(
        indent=indent,
        context={
            "matchstatusselectionparams": MatchStatusSelectionParams(
                include_not_ready=True
            ),
        },
    )
    nonblocking_write(data, file=sys.stdout)


@asynccontextmanager
async def print_tournament(tpsrv: TpsrvContext, indent: int | None) -> PluginLifespan:
    callback = partial(tournament_model_dump_json, indent=indent)
    updates_gen = cast(
        AsyncGenerator[Tournament],
        tpsrv.itc.updates("tournament", yield_immediately=False),
    )
    yield react_to_data_update(updates_gen, callback=callback)


@plugin
@click.option(
    "--indent",
    "-i",
    type=click.IntRange(min=1),
    help="Indent JSON output this many characters",
)
async def stdout(tpsrv: TpsrvContext, indent: int | None) -> PluginLifespan:
    """Output tournament data as JSON to stdout whenever it changes"""

    async with print_tournament(tpsrv, indent) as task:
        yield task
