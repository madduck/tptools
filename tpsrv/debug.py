# needed < 3.14 so that annotations aren't evaluated
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from click_async_plugins import CliContext, PluginLifespan, plugin
from click_async_plugins.debug import KeyAndFunc, monitor_stdin_for_debug_commands

from .util import pass_clictx

logger = logging.getLogger(__name__)


def simulate_reload_tpdata(clictx: CliContext) -> None:
    """Simulate event that TPData was reloaded"""
    clictx.itc.fire("tpdata")


@asynccontextmanager
async def debug_key_press_handler(clictx: CliContext) -> PluginLifespan:
    key_to_cmd = {
        0x12: KeyAndFunc("^R", simulate_reload_tpdata),
    }
    async with monitor_stdin_for_debug_commands(clictx, key_to_cmd=key_to_cmd) as task:
        yield task


@plugin
@pass_clictx
async def debug(clictx: CliContext) -> PluginLifespan:
    """Output tournament data as JSON to stdout whenever it changes"""

    async with debug_key_press_handler(clictx) as task:
        yield task
