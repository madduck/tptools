import logging
import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from functools import partial
from typing import cast

import click
from click_async_plugins import PluginLifespan, plugin, react_to_data_update

from tptools import MatchStatusSelectionParams
from tptools.ext.squore import Config, MatchesFeed, SquoreTournament
from tptools.namepolicy import PlayerNamePolicy
from tptools.util import nonblocking_write

from .util import CliContext, pass_clictx

logger = logging.getLogger(__name__)


async def matches_feed_json(
    tournament: SquoreTournament,
    *,
    indent: int | None = None,
) -> None:
    logger.info("Squore tournament changed, printing Squore data to stdout")
    data = MatchesFeed(tournament=tournament, config=Config()).model_dump_json(
        indent=indent,
        context={
            "matchstatusselectionparams": MatchStatusSelectionParams(
                include_not_ready=True
            ),
            "playernamepolicy": PlayerNamePolicy(),
        },
    )
    nonblocking_write(data + "\n", file=sys.stdout)


@asynccontextmanager
async def print_sqdata(clictx: CliContext, indent: int | None) -> PluginLifespan:
    callback = partial(matches_feed_json, indent=indent)
    updates_gen = cast(
        AsyncGenerator[SquoreTournament], clictx.itc.updates("sqtournament")
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
async def sq_stdout(clictx: CliContext, indent: int | None) -> PluginLifespan:
    """Output data as sent to Squore to stdout whenever the tournament changes"""

    async with print_sqdata(clictx, indent) as task:
        yield task
