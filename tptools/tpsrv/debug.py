import logging
import sys
from contextlib import asynccontextmanager
from functools import partial

from click_async_plugins import PluginLifespan, plugin
from click_async_plugins.debug import KeyAndFunc, monitor_stdin_for_debug_commands

from tptools.util import nonblocking_write

from .util import CliContext, pass_clictx

logger = logging.getLogger(__name__)


def simulate_reload_tournament(clictx: CliContext) -> None:
    """Simulate event that the tournament was modified or reloaded"""
    if clictx.watcher is not None:
        clictx.watcher.fire()
    else:
        clictx.itc.fire("tournament")


def dump_court_devices(clictx: CliContext) -> str | None:
    """Dump information gathered so far"""
    tournament = clictx.itc.get("tournament")
    courtdevs = [
        (c, c.scoredev) for c in tournament.courts.values() if c.scoredev is not None
    ]
    if not courtdevs:
        return "(No devices known to be associated with courts yet)"

    ret = "Known devices on courts:\n"
    ret += "\n".join(f"  {p[1]} on {p[0].name}" for p in courtdevs)
    return ret


@asynccontextmanager
async def debug_key_press_handler(clictx: CliContext) -> PluginLifespan:
    key_to_cmd = {
        0x12: KeyAndFunc("^R", simulate_reload_tournament),
        0x0C: KeyAndFunc("^L", dump_court_devices),
    }
    puts = partial(nonblocking_write, file=sys.stderr, eol="\n")
    async with monitor_stdin_for_debug_commands(
        clictx, key_to_cmd=key_to_cmd, puts=puts
    ) as task:
        yield task


@plugin
@pass_clictx
async def debug(clictx: CliContext) -> PluginLifespan:
    """Allow for debug-level interaction with the CLI"""

    async with debug_key_press_handler(clictx) as task:
        yield task
