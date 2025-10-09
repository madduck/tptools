import asyncio
import importlib
import importlib.resources
import logging
import pathlib
from contextlib import AsyncExitStack
from typing import Never

import click
import click_extra as clickx
import uvicorn
from click_async_plugins import (
    ITC,
    PluginFactory,
    create_plugin_task,
    plugin_group,
    setup_plugins,
)
from click_extra.config import Formats
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, PlainTextResponse
from starlette.types import StatefulLifespan, StatelessLifespan

from tptools.util import silence_logger

from .util import CliContext, pass_clictx

PLUGINS = [
    "debug",
    "tp",
    "tp_recv",
    "stdout",
    "post",
    "squoresrv",
    "sq_stdout",
]


try:
    from uvloop import new_event_loop

except ImportError:
    from asyncio import new_event_loop  # type: ignore[assignment,unused-ignore]

logger = clickx.new_extra_logger(
    format="{asctime} {name} {levelname} {message} ({filename}:{lineno})",
    datefmt="%F %T",
    level=logging.WARNING,
)


def make_app(
    lifespan: StatelessLifespan[FastAPI] | StatefulLifespan[FastAPI] | None = None,
    *,
    app_class: type[FastAPI] = FastAPI,
) -> FastAPI:
    app = app_class(lifespan=lifespan)
    app.state.changeevent = asyncio.Event()

    def favicon() -> FileResponse:
        with importlib.resources.path(
            "tptools", "tpsrv", "assets", "favicon.ico"
        ) as favicon:
            return FileResponse(
                favicon,
                media_type="image/png",
            )

    app.get("/favicon.ico")(favicon)

    def robotstxt() -> str:
        return "User-agent: *\nDisallow: /\n"

    app.get("/robots.txt", response_class=PlainTextResponse)(robotstxt)

    def pong(request: Request) -> str:
        client = request.headers.get(
            "X-Forwarded-For", request.client.host if request.client else None
        )
        return f"Hello {client}, tpsrv is running!\n"

    app.get("/", response_class=PlainTextResponse)(pong)

    return app


@plugin_group
@clickx.config_option(  # type: ignore[misc]
    strict=True,
    show_default=True,
    formats=Formats.TOML,
    # TODO:https://github.com/kdeldycke/click-extra/issues/1356 for str() call
    default=str(pathlib.Path(click.get_app_dir("tptools", roaming=True)) / "cfg.toml"),
)
@clickx.verbose_option(default_logger=logger)  # type: ignore[misc]
@click.option("--very-debug", is_flag=True, help="Do not silence any debug logging")
@click.option(
    "--host",
    "-h",
    metavar="IP",
    default="0.0.0.0",
    show_default=True,
    help="Host to listen on (bind to)",
)
@click.option(
    "--port",
    "-p",
    metavar="PORT",
    type=click.IntRange(min=1024, max=65535),
    default=8000,
    show_default=True,
    help="Port to listen on",
)
@click.pass_context
def tpsrv(
    ctx: click.Context,
    very_debug: bool,
    host: str,
    port: int,
) -> None:
    """Serve match and player data via HTTP"""

    if not very_debug:
        for name, level in (
            ("asyncio", logging.WARNING),
            ("watchdog", logging.WARNING),
            ("click_async_plugins.itc", logging.INFO),
            ("click_extra", logging.INFO),
            ("tptools.tpmatch", logging.INFO),
            ("httpx", logging.WARNING),
            ("httpcore.connection", logging.INFO),
            ("httpcore.http11", logging.INFO),
        ):
            silence_logger(name, level=level)

    # the options will be used in the result_callback function down below
    _ = host, port
    ctx.obj = CliContext(api=make_app(), itc=ITC())


for plugin in PLUGINS:
    try:
        mod = importlib.import_module(f".{plugin}", __package__)

    except (ImportError, NotImplementedError) as exc:
        logger.warning(f"Plugin '{plugin}' cannot be loaded: {exc}")

    else:
        subcmd = getattr(mod, plugin)
        tpsrv.add_command(subcmd)
        logger.debug(f"Added plugin to tpsrv: {plugin}")


@tpsrv.result_callback()
@pass_clictx
def runit(
    clictx: CliContext,
    plugin_factories: list[PluginFactory],
    very_debug: bool,
    host: str,
    port: int,
) -> Never:
    _ = very_debug

    loop = new_event_loop()
    asyncio.set_event_loop(loop)

    config = uvicorn.Config(clictx.api, host=host, port=port)
    server = uvicorn.Server(config)

    # We do not use FastAPI's/Starlette's lifespan because of
    # https://github.com/fastapi/fastapi/discussions/13878
    # but handle the lifespan ourselves outside of the server process:
    async def lifespan(plugin_factories: list[PluginFactory]) -> None:
        async with AsyncExitStack() as stack:
            tasks = await setup_plugins(plugin_factories, stack=stack)

            try:
                async with asyncio.TaskGroup() as tg:
                    for task in tasks:
                        create_plugin_task(task, create_task_fn=tg.create_task)

                    try:
                        await server.serve()

                    except KeyboardInterrupt:
                        pass

                    raise asyncio.CancelledError

            except asyncio.CancelledError:
                logger.info("Exiting…")

    try:
        loop.run_until_complete(lifespan(plugin_factories))

    except* click.ClickException as exc:
        for e in exc.exceptions:
            raise e from exc

    except* Exception:
        import ipdb

        logger.exception("Something went really wrong")

        ipdb.set_trace()  # noqa: E402 E702 I001 # fmt: skip

        click.get_current_context().exit(1)

    click.get_current_context().exit(0)
