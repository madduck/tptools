# needed < 3.14 so that annotations aren't evaluated
from __future__ import annotations

import asyncio
import datetime
import logging
import os
import sys
from collections.abc import Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from functools import partial

try:
    import fcntl
    import termios
    import tty

except ImportError as err:
    raise NotImplementedError(
        "Terminal control not supported on this platform"
    ) from err

from click_async_plugins import ITC, PluginLifespan, plugin

from tptools.util import nonblocking_write

from .util import TpsrvContext

logger = logging.getLogger(__name__)


def puts(s: str) -> None:
    nonblocking_write(s, file=sys.stderr, eol="\n")


def simulate_reload_tpdata(itc: ITC) -> None:
    """Simulate event that TPData was reloaded"""
    itc.fire("tpdata")


def echo_newline(_: ITC) -> None:
    """Outputs a new line"""
    puts("")


def terminal_block(_: ITC) -> None:
    """Outputs a couple of newlines and the current time"""
    puts(f"{'\n' * 8}The time is now: {datetime.datetime.now().isoformat(sep=' ')}\n")


def debug_info(itc: ITC) -> None:
    """Prints debugging information on tasks and ITC"""
    puts("*** BEGIN DEBUG INFO: ***")
    puts("Tasks:")
    for i, task in enumerate(asyncio.all_tasks(asyncio.get_event_loop()), 1):
        coro = task.get_coro()
        puts(
            f"  {i:02n}  {task.get_name():24s}  "
            f"state={task._state.lower():8s}  "
            f"coro={None if coro is None else coro.__qualname__}"
        )
    puts("ITC:")
    puts(f"  {itc}")
    puts("*** END DEBUG INFO: ***")


_LOGLEVELS = {
    logging.DEBUG: "DEBUG",
    logging.INFO: "INFO",
    logging.WARN: "WARN",
    logging.ERROR: "ERROR",
    logging.CRITICAL: "CRITICAL",
}


def adjust_loglevel(_: ITC, change: int) -> None:
    """Adjusts the log level"""
    rootlogger = logging.getLogger()
    newlevel = rootlogger.getEffectiveLevel() + change
    if newlevel < logging.DEBUG or newlevel > logging.CRITICAL:
        return

    rootlogger.setLevel(newlevel)
    puts(f"Log level now at {_LOGLEVELS[logger.getEffectiveLevel()]}")


@dataclass
class KeyAndFunc:
    key: str
    func: Callable[[ITC], None]


type KeyCmdMapType = dict[int, KeyAndFunc]


def print_help(_: ITC, key_to_cmd: KeyCmdMapType) -> None:
    puts("Keys I know about for debugging:")
    for keyfunc in key_to_cmd.values():
        puts(f"  {keyfunc.key:5s} {keyfunc.func.__doc__}")
    puts("  ?     Print this message")


async def _monitor_stdin(itc: ITC, key_to_cmd: KeyCmdMapType) -> None:
    fd = sys.stdin.fileno()
    termios_saved = termios.tcgetattr(fd)
    fnctl_flags = fcntl.fcntl(sys.stdin, fcntl.F_GETFL)

    try:
        logger.debug("Configuring stdin for raw input")
        tty.setcbreak(fd)
        fcntl.fcntl(sys.stdin, fcntl.F_SETFL, fnctl_flags | os.O_NONBLOCK)

        while True:
            ch = sys.stdin.read(1)

            if len(ch) == 0:
                await asyncio.sleep(0.1)
                continue

            if (key := ord(ch)) == 0x3F:
                print_help(itc, key_to_cmd)

            elif (keyfunc := key_to_cmd.get(key)) is not None and callable(
                keyfunc.func
            ):
                keyfunc.func(itc)

            else:
                logger.debug(f"Ignoring character 0x{key:02x} on stdin")

    finally:
        logger.debug("Restoring stdin")
        termios.tcsetattr(fd, termios.TCSADRAIN, termios_saved)
        fcntl.fcntl(sys.stdin, fcntl.F_SETFL, fnctl_flags)


@asynccontextmanager
async def monitor_stdin_for_debug_commands(tpsrv: TpsrvContext) -> PluginLifespan:
    increase_loglevel = partial(adjust_loglevel, change=-10)
    increase_loglevel.__doc__ = "Increase the logging level"
    decrease_loglevel = partial(adjust_loglevel, change=10)
    decrease_loglevel.__doc__ = "Decrease the logging level"

    key_to_cmd = {
        0xA: KeyAndFunc(r"\n", echo_newline),
        0x12: KeyAndFunc("^R", simulate_reload_tpdata),
        0x1B: KeyAndFunc("<Esc>", terminal_block),
        0x4: KeyAndFunc("^D", debug_info),
        0x2B: KeyAndFunc("+", increase_loglevel),
        0x2D: KeyAndFunc("-", decrease_loglevel),
    }
    yield _monitor_stdin(tpsrv.itc, key_to_cmd)


@plugin
async def debug(tpsrv: TpsrvContext) -> PluginLifespan:
    """Monitor stdin for keypresses to trigger debugging functions

    Press '?' to get a list of possible keys.
    """

    async with monitor_stdin_for_debug_commands(tpsrv) as task:
        yield task
