# needed < 3.14 so that annotations aren't evaluated
from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import cast

from click_async_plugins import PluginLifespan, react_to_data_update

from tptools.export import Tournament
from tptools.tpdata import TPData

from .util import CliContext

logger = logging.getLogger(__name__)


@asynccontextmanager
async def tp_proc(clictx: CliContext) -> PluginLifespan:
    async def callback(tpdata: TPData) -> None:
        logger.info("TPData updated, generating new Tournament…")
        clictx.itc.set("tournament", Tournament(tpdata=tpdata))

    updates_gen = cast(AsyncGenerator[TPData], clictx.itc.updates("tpdata"))
    yield react_to_data_update(updates_gen, callback=callback)
