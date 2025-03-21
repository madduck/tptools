import click
import sys
from aiohttp import web
import asyncio
import pathlib
from contextlib import suppress

from tptools.reader.tp import (
    make_connstring_from_path,
    async_tp_watcher,
    AsyncTPReader,
    load_tournament_from_tpfile,
)
from tptools.tournament import Tournament
from tptools.entry import Entry
from tptools.logger import get_logger, adjust_log_level
from tptools.jsonfeed import JSONFeedMaker

logger = get_logger(__name__)


TP_DEFAULT_USER = "Admin"
APPKEY_TOURNAMENT = web.AppKey("tournament", Tournament)
APPKEY_CONFIG = web.AppKey("config", dict)


routes = web.RouteTableDef()


@routes.get("/matches")
async def matches(request):
    include_params = {}
    for p in ("include_played", "include_not_ready"):
        if request.query.get(p) in ("1", "true", "yes"):
            logger.debug(f"Setting '{p}=True'")
            include_params[p] = True

    matches = request.app[APPKEY_TOURNAMENT].get_matches(**include_params)

    if court := request.query.get("court"):
        logger.info(f"Matches request received for '{court}'")

    matches_by_court = {}
    matches_without_court = []
    only_this_court = request.query.get("only_this_court") in (
        "1",
        "true",
        "yes",
    )
    for match in sorted(matches, key=lambda m: m.time):

        if not match.court and not only_this_court:
            logger.debug(f"Found a match {match.id} without an assigned court")
            matches_without_court.append(match)

        else:
            sect = " " + match.court

            if court == match.court:
                sect = "+" + sect
                logger.debug(f"Found match {match.id} on OUR court {match.court}")

            elif only_this_court:
                logger.debug(f"Skipping match on court {match.court}")
                continue

            else:
                logger.debug(f"Found match {match.id} on court {match.court}")

            matches_by_court.setdefault(sect, []).append(match)

    if matches_without_court:
        matches_by_court[" No court"] = matches_without_court

    config = {
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
    entries = sorted(request.app[APPKEY_TOURNAMENT].get_entries())
    names = [Entry.make_team_name(e.players) for e in entries]
    return web.Response(text="\n".join(names))


async def watch_tp_file(app):
    config = app[APPKEY_CONFIG]
    connstr = config["connstr"]

    async def callback(logger):
        tournament = await load_tournament_from_tpfile(connstr, logger=logger)
        app[APPKEY_TOURNAMENT] = tournament

    try:
        async with asyncio.TaskGroup() as tg:
            task = tg.create_task(
                async_tp_watcher(
                    path=config["tpfile"],
                    logger=logger,
                    callback=callback,
                    pollsecs=config["pollsecs"],
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
    "--host",
    "-h",
    default="0.0.0.0",
    help="Host to listen on (bind to)",
)
@click.option(
    "--port",
    "-p",
    type=click.INT,
    default=8000,
    help="Port to listen on",
)
@click.option(
    "--tpfile",
    "-i",
    type=click.Path(path_type=pathlib.Path),
    required=True,
    help="TP file to watch and read",
)
@click.option(
    "--tpuser",
    "-U",
    required=True,
    default=TP_DEFAULT_USER,
    show_default=True,
    help="User name to use for TP file",
)
@click.option(
    "--tppasswd",
    "-P",
    required=True,
    help="Password to use for TP file",
)
@click.option(
    "--pollsecs",
    "-p",
    type=click.INT,
    help="Frequency in seconds to poll TP file in the absence of inotify",
    default=30,
)
@click.option("--verbose", "-v", count=True, help="Increase verbosity of log output")
@click.option(
    "--quiet",
    "-q",
    is_flag=True,
    help="Output as little information as possible",
)
@click.pass_context
def main(ctx, verbose, quiet, host, port, tpfile, tpuser, tppasswd, pollsecs):
    adjust_log_level(logger, verbose, quiet=quiet)

    tpfile = tpfile.absolute()

    app = web.Application()
    app[APPKEY_CONFIG] = {
        "tpfile": tpfile,
        "connstr": make_connstring_from_path(tpfile, tpuser, tppasswd),
        "pollsecs": pollsecs,
    }
    app.add_routes(routes)
    app.cleanup_ctx.append(watch_tp_file)
    web.run_app(app, host=host, port=port)


if __name__ == "__main__":
    sys.exit(main())
