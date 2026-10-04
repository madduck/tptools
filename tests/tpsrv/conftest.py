import asyncio
from collections.abc import AsyncIterator, Callable, Coroutine
from contextlib import AbstractAsyncContextManager, asynccontextmanager, suppress
from typing import Any

import click
import pytest
from click.testing import CliRunner, Result
from click_async_plugins import ITC
from fastapi import FastAPI

from tptools.tpsrv.util import CliContext

type PluginTask = Coroutine[None, None, None]
type PluginCM = AbstractAsyncContextManager[PluginTask | None]
type PluginFactory = Callable[[], PluginCM]


@pytest.fixture
def clictx() -> CliContext:
    return CliContext(api=FastAPI(), itc=ITC())


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


InvokePlugin = Callable[[click.Command, list[str]], Result]
MakeFactory = Callable[[click.Command, list[str]], PluginFactory]


@pytest.fixture
def invoke_plugin(runner: CliRunner, clictx: CliContext) -> InvokePlugin:
    """Invoke a plugin command like the command line would, in clictx

    Use this to look at exit codes and output, e.g. for --help or bad options.
    """

    def invoke(cmd: click.Command, args: list[str]) -> Result:
        return runner.invoke(cmd, args, obj=clictx)

    return invoke


@pytest.fixture
def make_factory(clictx: CliContext) -> MakeFactory:
    """Parse a plugin command line and return the plugin factory it produces

    This is what tpsrv's result callback gets handed for every plugin on the
    command line. Errors in the arguments are raised as click exceptions.

    Plugins look up their CliContext via click.get_current_context() when they
    are started, and in tpsrv that happens while the group's click context is
    still active, so the returned factory re-enters the context when called.
    """

    def make(cmd: click.Command, args: list[str]) -> PluginFactory:
        ctx = cmd.make_context(cmd.name or "plugin", list(args), obj=clictx)
        with ctx:
            factory = cmd.invoke(ctx)
        assert callable(factory), f"no plugin factory returned: {factory!r}"

        @asynccontextmanager
        async def in_context() -> AsyncIterator[PluginTask | None]:
            with ctx:
                async with factory() as task:
                    yield task

        return in_context

    return make


@asynccontextmanager
async def running(plugin: PluginCM) -> AsyncIterator[asyncio.Task[None]]:
    """Set up a plugin, run its task in the background, and tear it all down"""
    async with plugin as coro:
        assert coro is not None, "plugin did not provide a task"
        task = asyncio.create_task(coro)
        try:
            yield task
        finally:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task


async def wait_for(
    condition: Callable[[], Any], *, timeout: float = 5, period: float = 0.01
) -> None:
    """Poll until condition() is truthy, or fail after timeout seconds"""
    async with asyncio.timeout(timeout):
        while not condition():
            await asyncio.sleep(period)
