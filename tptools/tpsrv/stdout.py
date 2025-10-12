import logging
import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from functools import partial
from typing import cast

import click
from click_async_plugins import PluginLifespan, plugin, react_to_data_update

from tptools import MatchSelectionParams, Tournament
from tptools.util import nonblocking_write

from .util import CliContext, pass_clictx

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
            "matchselectionparams": MatchSelectionParams(include_not_ready=True),
        },
    )
    nonblocking_write(data + "\n", file=sys.stdout)


@asynccontextmanager
async def print_tournament(clictx: CliContext, indent: int | None) -> PluginLifespan:
    callback = partial(tournament_model_dump_json, indent=indent)
    updates_gen = cast(
        AsyncGenerator[Tournament],
        clictx.itc.updates("tournament", yield_immediately=False),
    )
    yield react_to_data_update(updates_gen, callback=callback)


@plugin
@click.option(
    "--indent",
    "-i",
    type=click.IntRange(min=1),
    help="Indent JSON output this many characters",
)
@pass_clictx
async def stdout(clictx: CliContext, indent: int | None) -> PluginLifespan:
    """Output tournament data as JSON to stdout whenever it changes"""

    async with print_tournament(clictx, indent) as task:
        yield task
