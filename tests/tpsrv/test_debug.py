import asyncio
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from typing import Any

import pytest
from click_async_plugins.debug import KeyAndFunc
from pytest import CaptureFixture
from pytest_mock import MockerFixture

from tptools.tpsrv.debug import (
    debug,
    debug_key_press_handler,
    simulate_reload_tournament,
)
from tptools.tpsrv.util import CliContext

from .conftest import InvokePlugin, MakeFactory, wait_for

CTRL_R = 0x12


class FakeMonitor:
    """Replacement for click_async_plugins.debug.monitor_stdin_for_debug_commands"""

    def __init__(self) -> None:
        self.calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []
        self.entered = 0
        self.exited = 0
        self.task_ran = asyncio.Event()

    @asynccontextmanager
    async def __call__(self, *args: Any, **kwargs: Any) -> AsyncIterator[Any]:
        self.calls.append((args, kwargs))
        self.entered += 1

        async def task() -> None:
            self.task_ran.set()

        try:
            yield task()
        finally:
            self.exited += 1


@pytest.fixture
def monitor(mocker: MockerFixture) -> FakeMonitor:
    fake = FakeMonitor()
    mocker.patch("tptools.tpsrv.debug.monitor_stdin_for_debug_commands", fake)
    return fake


# simulate_reload_tournament


@pytest.mark.asyncio
async def test_reload_wakes_up_tournament_listeners_without_watcher(
    clictx: CliContext,
) -> None:
    assert clictx.watcher is None
    received: list[Any] = []

    async def listen() -> None:
        async for update in clictx.itc.updates("tournament", yield_immediately=False):
            received.append(update)
            return

    task = asyncio.create_task(listen())
    await wait_for(lambda: clictx.itc.has_subscribers("tournament"))

    simulate_reload_tournament(clictx)

    await asyncio.wait_for(task, 2)
    assert received == [None], "woken up, but no new data was provided"


def test_reload_fires_itc_event_for_tournament_key(
    clictx: CliContext, mocker: MockerFixture
) -> None:
    fire = mocker.patch.object(clictx.itc, "fire")
    simulate_reload_tournament(clictx)
    fire.assert_called_once_with("tournament")


def test_reload_prefers_the_watcher(clictx: CliContext, mocker: MockerFixture) -> None:
    watcher = mocker.Mock()
    clictx.watcher = watcher
    fire = mocker.patch.object(clictx.itc, "fire")

    simulate_reload_tournament(clictx)

    watcher.fire.assert_called_once_with()
    fire.assert_not_called()


def test_reload_has_a_docstring_for_the_help_screen() -> None:
    # the library's '?' help prints each handler's docstring
    assert simulate_reload_tournament.__doc__


# debug_key_press_handler


@pytest.mark.asyncio
async def test_key_handler_wraps_monitor(
    clictx: CliContext, monitor: FakeMonitor
) -> None:
    async with debug_key_press_handler(clictx) as task:
        assert monitor.entered == 1 and monitor.exited == 0
        assert task is not None
        await task
        assert monitor.task_ran.is_set()

    assert monitor.exited == 1


@pytest.mark.asyncio
async def test_key_handler_passes_context_and_keymap(
    clictx: CliContext, monitor: FakeMonitor
) -> None:
    async with debug_key_press_handler(clictx) as task:
        assert task is not None
        await task

    ((args, kwargs),) = monitor.calls
    assert args == (clictx,)
    assert set(kwargs) == {"key_to_cmd", "puts"}

    key_to_cmd = kwargs["key_to_cmd"]
    assert list(key_to_cmd) == [CTRL_R]
    assert key_to_cmd[CTRL_R] == KeyAndFunc("^R", simulate_reload_tournament)


@pytest.mark.asyncio
async def test_key_handler_puts_writes_lines_to_stderr(
    clictx: CliContext, monitor: FakeMonitor, capfd: CaptureFixture[str]
) -> None:
    async with debug_key_press_handler(clictx) as task:
        assert task is not None
        await task

    puts: Callable[[str], int] = monitor.calls[0][1]["puts"]
    assert puts("hello") == len(b"hello\n")

    captured = capfd.readouterr()
    assert captured.err == "hello\n"
    assert captured.out == ""


@pytest.mark.asyncio
async def test_ctrl_r_triggers_a_reload(
    clictx: CliContext, monitor: FakeMonitor, mocker: MockerFixture
) -> None:
    fire = mocker.patch.object(clictx.itc, "fire")
    async with debug_key_press_handler(clictx) as task:
        assert task is not None
        await task
        monitor.calls[0][1]["key_to_cmd"][CTRL_R].func(clictx)

    fire.assert_called_once_with("tournament")


# the command


def test_debug_help(invoke_plugin: InvokePlugin) -> None:
    result = invoke_plugin(debug, ["--help"])
    assert result.exit_code == 0
    assert "Allow for debug-level interaction with the CLI" in result.output


def test_debug_takes_no_arguments(invoke_plugin: InvokePlugin) -> None:
    result = invoke_plugin(debug, ["unexpected"])
    assert result.exit_code == 2
    assert "Got unexpected extra argument" in result.output


@pytest.mark.asyncio
async def test_debug_command(
    make_factory: MakeFactory, clictx: CliContext, monitor: FakeMonitor
) -> None:
    async with make_factory(debug, [])() as task:
        assert task is not None
        assert monitor.entered == 1
        await task
        assert monitor.task_ran.is_set()

    assert monitor.exited == 1
    assert monitor.calls[0][0] == (clictx,)
