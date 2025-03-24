import click
import sys
from aiohttp import web
import asyncio
import pathlib
from contextlib import suppress
import tempfile
import shutil
from collections.abc import Callable

from tptools.reader.tp import (
    make_connstring_from_path,
    async_tp_watcher,
    AsyncTPReader,
    load_tournament_from_tpfile,
    async_load_tournament_from_tpfile,
)
from tptools.tournament import Tournament
from tptools.entry import Entry
from tptools.logger import get_logger, adjust_log_level
from tptools.jsonfeed import JSONFeedMaker
from tptools.util import is_truish, get_config_file_path
from tptools.configfile import ConfigFile

logger = get_logger(__name__)

TP_DEFAULT_USER = "Admin"
APPKEY_TOURNAMENT_CB = web.AppKey("tournament_cb", Callable)
APPKEY_TOURNAMENT = web.AppKey("tournament", Tournament)
APPKEY_CONFIG = web.AppKey("config", dict)


routes = web.RouteTableDef()


@routes.get("/matches")
async def matches(request):
    include_params = {}
    for p in ("include_played", "include_not_ready"):
        if is_truish(request.query.get(p)):
            logger.debug(f"Setting '{p}=True'")
            include_params[p] = True

    matches = request.app[APPKEY_TOURNAMENT_CB](request.app).get_matches(
        **include_params
    )

    if court := request.query.get("court"):
        logger.info(f"Matches request received for '{court}'")

    matches_by_court = {}
    matches_without_court = []
    only_this_court = is_truish(request.query.get("only_this_court"))
    for match in sorted(matches, key=lambda m: m.time):

        if not match.court and not only_this_court:
            logger.debug(f"Found a match {match.id} without an assigned court")
            matches_without_court.append(match)

        else:
            # IMPORTANT: use a non-breaking space or else sorting in Squore is
            # inconsistent
            sect = "\xa0" + match.court

            if court == match.court:
                # Prefixing the court/section name with a '+' will cause Squore
                # to expand the section
                sect = "+" + sect
                logger.debug(f"Found match {match.id} on OUR court {match.court}")

            elif only_this_court:
                logger.debug(f"Skipping match on court {match.court}")
                continue

            else:
                logger.debug(f"Found match {match.id} on court {match.court}")

            matches_by_court.setdefault(sect, []).append(match)

    if matches_without_court:
        # IMPORTANT: use a non-breaking space or else sorting in Squore is
        # inconsistent
        matches_by_court["\xa0No court"] = matches_without_court

    config = {  # TODO: parametrise
        "Placeholder_Match": (
            "${time} Uhr : "
            "${FirstOfList:~${A}~${A.name}~} - "
            "${FirstOfList:~${B}~${B.name}~} "
            "(${field}) : "
            "${result}"
        ),
        # "PostResult": str(request.url.parent / "result"),
        # "LiveScoreUrl": str(request.url.parent / "live"),
    }

    jfm = JSONFeedMaker(matches=matches_by_court, **config)

    return web.json_response(jfm.get_data())


@routes.get("/players")
async def players(request):
    entries = sorted(request.app[APPKEY_TOURNAMENT_CB](request.app).get_entries())
    names = [Entry.make_team_name(e.players) for e in entries]
    return web.Response(text="\n".join(names))


async def watch_tp_file(app, work_on_copy=False):
    config = app[APPKEY_CONFIG]

    async def callback(path, *, logger):
        tpuser = config["tpuser"]
        tppasswd = config["tppasswd"]

        async def load_tournament(connstr):
            tournament = await async_load_tournament_from_tpfile(connstr, logger=logger)
            if tournament:
                app[APPKEY_TOURNAMENT] = tournament
            else:
                logger.warn(
                    f"Loading tournament from {connstr} " f"returned: {tournament}"
                )

        if work_on_copy:
            with tempfile.TemporaryDirectory() as tmpdir:
                tmpfile = pathlib.Path(tmpdir) / path.name
                shutil.copy(path, tmpfile)
                connstr = make_connstring_from_path(tmpfile, tpuser, tppasswd)
                await load_tournament(connstr)

        else:
            connstr = make_connstring_from_path(path, tpuser, tppasswd)
            await load_tournament(connstr)

    try:
        async with asyncio.TaskGroup() as tg:
            task = tg.create_task(
                async_tp_watcher(
                    path=config["tpfile"],
                    logger=logger,
                    callback=callback,
                    pollfreq=config["pollfreq"],
                ),
                name="TPWatcher",
            )
            logger.debug(f"Created TP watcher task: {task}")

            yield

            app.logger.debug(f"Tearing down TP watcher task: {task}")
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task

    except* AsyncTPReader.DriverMissingException:
        if isinstance(task.exception(), AsyncTPReader.DriverMissingException):
            logger.error("Missing Microsoft Access driver. Are you on Windows?")
            sys.exit(1)

        else:
            raise


@click.command
@click.option(
    "--tpfile",
    "-i",
    type=click.Path(path_type=pathlib.Path),
    help="TP file to watch and read",
)
@click.option(
    "--tpuser",
    "-U",
    default=TP_DEFAULT_USER,
    show_default=True,
    help="User name to use for TP file",
)
@click.option(
    "--tppasswd",
    "-P",
    help="Password to use for TP file",
)
@click.option(
    "--pollfreq",
    "-f",
    type=click.INT,
    help="Frequency in seconds to poll TP file in the absence of inotify",
    default=30,
    show_default=True,
)
@click.option(
    "--host",
    "-h",
    default="0.0.0.0",
    show_default=True,
    help="Host to listen on (bind to)",
)
@click.option(
    "--port",
    "-p",
    type=click.INT,
    default=80,
    show_default=True,
    help="Port to listen on",
)
@click.option(
    "--cfgfile",
    "-c",
    type=click.Path(path_type=pathlib.Path),
    default=get_config_file_path(),
    show_default=True,
    help="Config file to read instead of default",
)
@click.option("--verbose", "-v", count=True, help="Increase verbosity of log output")
@click.option(
    "--quiet",
    "-q",
    is_flag=True,
    help="Output as little information as possible",
)
@click.option(
    "--asynchronous",
    "-a",
    is_flag=True,
    help="Query database asynchronously (BUGGY!)",
)
@click.pass_context
def main(
    ctx,
    cfgfile,
    verbose,
    quiet,
    asynchronous,
    host,
    port,
    tpfile,
    tpuser,
    tppasswd,
    pollfreq,
):
    cfg = ConfigFile(cfgfile)

    params = {}
    for param in ("tpfile", "tpuser", "tppasswd", "pollfreq"):
        params[param] = locals()[param] or cfg.get(f"{param}")
    for param in ("host", "port"):
        params[param] = locals()[param] or cfg.get(f"squoresrv.{param}")

    if not params.get("tppasswd"):
        raise click.BadParameter("Missing TP password")

    adjust_log_level(logger, verbose, quiet=quiet)

    params["tpfile"] = params["tpfile"].expanduser().absolute()

    app = web.Application()
    app.add_routes(routes)

    if asynchronous:

        def get_tournament(app):
            return app[APPKEY_TOURNAMENT]

        app[APPKEY_CONFIG] = params
        app.cleanup_ctx.append(watch_tp_file)

    else:

        def get_tournament(app):
            connstr = make_connstring_from_path(
                params["tpfile"], params["tpuser"], params["tppasswd"]
            )
            return load_tournament_from_tpfile(connstr, logger=logger)

    app[APPKEY_TOURNAMENT_CB] = get_tournament
    web.run_app(app, host=params["host"], port=params["port"])


if __name__ == "__main__":
    sys.exit(main())
