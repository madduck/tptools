import click
import sys
import aiohttp
from aiohttp import web
import asyncio
import pathlib
import warnings

from tptools.tournament import Tournament
from tptools.entry import Entry
from tptools.logger import get_logger, adjust_log_level
from tptools.jsonfeed import JSONFeedMaker
from tptools.util import is_truish, json_dump_with_default
from tptools.configfile import (
    get_config_file_path,
    ConfigFile,
    merge_cli_opts_into_cfg,
)

logger = get_logger(__name__)

TP_DEFAULT_USER = "Admin"
APPKEY_TOURNAMENT = web.AppKey("tournament", Tournament)


routes = web.RouteTableDef()


def tournament_to_squore(
    tournament,
    *,
    include_played=True,
    include_not_ready=True,
    court=None,
    only_this_court=False,
):
    matches = tournament.get_matches(
        include_played=include_played,
        include_not_ready=include_not_ready,
    )

    matches_by_court = {}
    matches_without_court = []
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
                logger.debug(
                    f"Found match {match.id} on OUR court {match.court}"
                )

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
    return jfm.get_data()


@routes.get("/squore/matches")
async def matches(request):
    logger = request.app.logger

    params = {"court": request.query.get("court")}
    for p in ("only_this_court", "include_played", "include_not_ready"):
        val = is_truish(request.query.get(p))
        logger.debug(f"Setting '{p}={val}'")
        params[p] = val

    remote = request.headers.get("X-Forwarded-For", request.remote)
    logger.info(f"Matches request from {remote} {params}")

    tournament = request.app[APPKEY_TOURNAMENT]

    jret = tournament_to_squore(tournament, **params)
    return web.json_response(jret)


@routes.get("/squore/players")
async def players(request):
    logger = request.app.logger

    remote = request.headers.get("X-Forwarded-For", request.remote)
    logger.info(f"Players request from {remote}")

    tournament = request.app[APPKEY_TOURNAMENT]
    entries = sorted(tournament.get_entries())

    names = [Entry.make_team_name(e.players) for e in entries]
    return web.Response(text="\n".join(names))


async def post_matches(url, matches, *, retries=3, sleep=1, logger=None):
    if logger:
        logger.info(f"Posting matches to {url}")
    while True:
        try:
            async with aiohttp.ClientSession(
                raise_for_status=True,
                json_serialize=json_dump_with_default,
            ) as session:
                async with session.post(url, json=matches) as resp:
                    rt = await resp.json()
                    if logger:
                        logger.info(
                            "Success transferring "
                            f"{rt.get('nrecords', '(no count returned)')} "
                            "matches to {url}"
                        )
                    break

        except (
            aiohttp.ClientConnectorError,
            aiohttp.ClientResponseError,
        ) as err:

            if retries > 0:
                retries -= 1
                if logger:
                    logger.warning(
                        f"Problem posting to {url}: {err}, retrying…"
                    )
                await asyncio.sleep(sleep)
                continue

            else:
                if logger:
                    logger.error(f"Giving up posting to {url}: {err}")
                break

        except aiohttp.ServerDisconnectedError:
            if logger:
                logger.error(f"Server at {url} disconnected.")
            break


@click.group
@click.option(
    "--cfgfile",
    "-c",
    metavar="PATH",
    type=click.Path(path_type=pathlib.Path),
    default=get_config_file_path(),
    show_default=True,
    help="Config file to read instead of default",
)
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
@click.option(
    "--url",
    "-u",
    "urls",
    metavar="URL",
    multiple=True,
    help=(
        "POST data to this URL when the input changes"
        "(can be specified more than once)"
    ),
)
@click.option(
    "--stdout",
    "-o",
    is_flag=True,
    help="Print data to stdout when the input changes",
)
@click.option(
    "--verbose", "-v", count=True, help="Increase verbosity of log output"
)
@click.option(
    "--quiet",
    "-q",
    is_flag=True,
    help="Output as little information as possible",
)
@click.pass_context
def main(
    ctx,
    cfgfile,
    verbose,
    quiet,
    host,
    port,
    stdout,
    urls,
):
    """Serve match and player data via HTTP"""

    cfg = ConfigFile(cfgfile, section="tpsrv")
    merge_cli_opts_into_cfg(locals(), cfg, exclude=("ctx", "cfgfile", "cfg"))
    ctx.obj = {
        "cfg": cfg,
    }

    adjust_log_level(logger, cfg.get("verbose"), quiet=cfg.get("quiet"))

    app = web.Application(logger=logger)
    app.add_routes(routes)

    ctx.obj["app"] = app

    # The idea in the following is that we pass the `run` function on in the
    # context object. Whatever sub-command then parses a tournament provides
    # a watcher function that populates the tournament data.

    def async_run(watcher_ctx):
        app.cleanup_ctx.append(watcher_ctx)

        try:
            web.run_app(
                app,
                host=cfg.get("host"),
                port=cfg.get("port"),
                print=click.echo,
                access_log=None,
            )

        except Exception as err:
            logger.critical(str(err), exc_info=err)
            ctx.exit(1)

    ctx.obj["run_fn"] = async_run

    async def changed_fn(tournament):
        if not stdout and not urls:
            return

        matches = list(
            tournament.get_matches(include_played=True, include_not_ready=True)
        )
        if stdout:
            try:
                click.echo(json_dump_with_default(matches))
            except Exception as err:
                import ipdb; ipdb.set_trace()  # noqa:E402,E702

        if urls:
            async with asyncio.TaskGroup() as tg:
                for url in urls:
                    tg.create_task(post_matches(url, matches, logger=logger))

    ctx.obj["changed_fn"] = changed_fn


@main.command
@click.argument(
    "TP_file",
    type=click.Path(path_type=pathlib.Path),
    nargs=1,
)
@click.option(
    "--user",
    "-u",
    metavar="UID",
    default=TP_DEFAULT_USER,
    show_default=True,
    help="User name to access TP file",
)
@click.password_option(
    "--password",
    "-p",
    prompt_required=False,
    confirmation_prompt=False,
    prompt="Enter the password to access the TP file",
    metavar="PASSWORD",
    help="Password to access TP file",
)
@click.option(
    "--pollfreq",
    "-f",
    metavar="SECONDS",
    type=click.IntRange(min=1),
    help=(
        "Frequency in seconds to poll TP file in the absence of inotify"
    ),
    default=30,
    show_default=True,
)
@click.option(
    "--work-on-copy",
    "-c",
    is_flag=True,
    help="Always make a copy of the TP file before reading it",
)
@click.option(
    "--asynchronous",
    "-a",
    is_flag=True,
    help="Access TP file asynchronously (BUGGY)",
)
@click.pass_obj
def tp(obj, tp_file, user, password, pollfreq, work_on_copy, asynchronous):
    """Serve match and player data from a TP file"""

    from tptools.reader.mdb import make_connstring_from_path

    cfg = obj["cfg"]
    merge_cli_opts_into_cfg(
        locals(),
        cfg,
        exclude=("ctx", "cfgfile", "cfg"),
        typemap={"tp_file": pathlib.Path},
    )
    app = obj["app"]
    logger = app.logger

    # The following is best understood working your way up from the bottom,
    # starting at 1:

    # ========================================================================
    # 2. The job of `tp_handler` is essentially to invoke `run_fn` made
    #    available by the main CLI entry point and passed via the context
    #    object, either with a watcher function in asynchronous mode, or with a
    #    getter function in synchronous mode.
    #
    #    In synchronous mode, we can return the Tournament directly, whereas
    #    in asynchronous mode, we cache it in the `app` dict.
    run_fn = obj["run_fn"]
    changed_fn = obj["changed_fn"]

    def tp_handler(connstr):

        async def load_tournament():

            if cfg.get("asynchronous"):
                from tptools.tpfile import async_load_tournament_from_tpfile

                warnings.warn(
                    "Asynchronous ODBC access is buggy, "
                    "see https://github.com/aio-libs/aioodbc/issues/463",
                    RuntimeWarning,
                )
                logger.debug(f"async {connstr=}")
                tournament = await async_load_tournament_from_tpfile(
                    connstr, logger=logger
                )

            else:
                from tptools.tpfile import load_tournament_from_tpfile

                logger.debug(f"sync {connstr=}")
                tournament = load_tournament_from_tpfile(
                    connstr, logger=logger
                )

            logger.debug(f"Got tournament: {tournament}")
            app[APPKEY_TOURNAMENT] = tournament
            await changed_fn(tournament)

        async def watch_tp_file(app):
            from tptools.fswatcher import async_fswatcher

            path = cfg.get("tp_file")
            try:
                async with asyncio.TaskGroup() as tg:
                    task = tg.create_task(
                        async_fswatcher(
                            path=path,
                            callback=load_tournament,
                            logger=logger,
                            pollfreq=cfg.get("pollfreq"),
                        ),
                        name="TPWatcher",
                    )
                    logger.debug(f"Created TP watcher task: {task}")

                    yield

                    app.logger.debug(f"Tearing down TP watcher task: {task}")
                    task.cancel()

            except* FileNotFoundError:
                # override the silly Windows error message
                raise FileNotFoundError(f"TP file does not exist: {path}")

            except* Exception:
                raise task.exception()

        run_fn(watcher_ctx=watch_tp_file)

    tp_file = cfg.get("tp_file")
    if cfg.get("work_on_copy"):
        import tempfile
        import shutil

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpfile = pathlib.Path(tmpdir) / tp_file.name
            shutil.copy(tp_file, tmpfile)
            connstr = make_connstring_from_path(
                tmpfile, cfg.get("user"), cfg.get("password")
            )
            tp_handler(connstr)

    else:
        connstr = make_connstring_from_path(
            tp_file, cfg.get("user"), cfg.get("password")
        )
        tp_handler(connstr)


if __name__ == "__main__":
    sys.exit(main())
