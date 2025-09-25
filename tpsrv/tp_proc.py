# needed < 3.14 so that annotations aren't evaluated
from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import cast

from click_async_plugins import PluginLifespan

from tptools.export import Tournament
from tptools.tpdata import TPData

from .util import TpsrvContext, react_to_data_update

logger = logging.getLogger(__name__)


@asynccontextmanager
async def tp_proc(tpsrv: TpsrvContext) -> PluginLifespan:
    async def callback(tpdata: TPData) -> None:
        logger.info("TPData updated, generating new Tournament…")
        tpsrv.itc.set("tournament", Tournament(tpdata=tpdata))

    updates_gen = cast(AsyncGenerator[TPData], tpsrv.itc.updates("tpdata"))
    yield react_to_data_update(updates_gen, callback=callback)
