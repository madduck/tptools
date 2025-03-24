import click
import sys
import aiohttp
import asyncio
import pathlib

from tptools.reader.tp import (
    make_connstring_from_path,
    async_tp_watcher,
    TPReader,
    load_tournament_from_tpfile,
)
from tptools.asyncio import asyncio_run
from tptools.reader.csv import CSVReader
from tptools.entry import Entry
from tptools.playermatch import PlayerMatch
from tptools.tournament import Tournament
from tptools.logger import get_logger, adjust_log_level
from tptools.util import json_dump_with_default, get_config_file_path
from tptools.configfile import ConfigFile

logger = get_logger(__name__)


TP_DEFAULT_USER = "Admin"


async def post_tournament_data(url, tournament, *, logger):
    matches = list(tournament.get_matches(include_played=False))

    if not url:
        print(json_dump_with_default(matches))

    else:
        while True:
            try:
                async with aiohttp.ClientSession(
                    raise_for_status=True,
                    json_serialize=json_dump_with_default,
                ) as session:
                    async with session.post(url, json=matches) as resp:
                        if resp.status != 200:
                            logger.error(f"Data POST failed: {resp.reason}")
                        else:
                            rt = await resp.json()
                            logger.info(
                                "Success transferring "
                                f"{rt.get('nrecords', '(no count returned)')} "
                                "matches"
                            )
                break

            except aiohttp.ClientConnectorError as err:
                logger.error(f"Connection error: {err}, retrying…")

            except aiohttp.ClientResponseError as err:
                logger.error(f"Response error: {err}, retrying…")

            await asyncio.sleep(5)


@click.command
@click.option("--url", "-u", help="URL to send events to (stdout if not provided)")
@click.option(
    "--tpfile",
    "-i",
    type=click.Path(path_type=pathlib.Path),
    help="TP file to watch and read",
)
@click.option(
    "--tpuser",
    "-U",
    help="User name to use for TP file",
    default=TP_DEFAULT_USER,
    show_default=True,
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
@click.option("--test", "-t", is_flag=True, help="Use test data for this run")
@click.pass_context
@asyncio_run
async def main(
    ctx,
    cfgfile,
    verbose,
    quiet,
    url,
    tpfile,
    tpuser,
    tppasswd,
    test,
    pollfreq,
):
    adjust_log_level(logger, verbose, quiet=quiet)

    if test:
        if tpfile:
            raise click.BadParameter("--tpfile and --test cannot be combined")
        if tpuser != TP_DEFAULT_USER:
            raise click.BadParameter("--tpuser and --test cannot be combined")
        if tppasswd:
            raise click.BadParameter("--tppasswd and --test cannot be combined")
        connstr = None

    elif tpfile:
        cfg = ConfigFile(cfgfile)

        params = {}
        for param in ("tpfile", "tpuser", "tppasswd", "pollfreq"):
            params[param] = locals()[param] or cfg.get(f"{param}")
        for param in ("url",):
            params[param] = locals()[param] or cfg.get(f"squoresrv.{param}")

        if not params["tppasswd"]:
            raise click.BadParameter("Missing TP password")

        params["tpfile"] = params["tpfile"].expanduser().absolute()

        connstr = make_connstring_from_path(
            params["tpfile"], params["tpuser"], params["tppasswd"]
        )

    else:
        raise click.BadParameter("--tpfile must be specified without --test")

    if connstr:

        async def callback(path, logger):
            tournament = load_tournament_from_tpfile(connstr, logger=logger)
            if tournament:
                await post_tournament_data(url, tournament, logger=logger)

        try:
            async with asyncio.TaskGroup() as tg:
                t1 = tg.create_task(
                    async_tp_watcher(
                        path=tpfile,
                        logger=logger,
                        callback=callback,
                        pollfreq=pollfreq,
                    ),
                    name="TPWatcher",
                )
                logger.debug(f"Created TP watcher task: {t1}")

        except* TPReader.DriverMissingException:
            if isinstance(t1.exception(), TPReader.DriverMissingException):
                logger.error("Missing Microsoft Access driver. Are you on Windows?")
                sys.exit(1)

            else:
                raise

    else:
        logger.warning("Test-mode with static, fake data")

        fixtures = (
            pathlib.Path(__file__).parent.parent.parent / "tests" / "csv_fixtures"
        )

        with open(fixtures / "playermatches.csv", newline="") as f:
            matches = [PlayerMatch(r) for r in CSVReader(f)]
        with open(fixtures / "playerentries.csv", newline="") as f:
            entries = [Entry(r) for r in CSVReader(f)]

        tournament = Tournament(entries=entries, playermatches=matches)
        logger.info(f"Parsed test tournament: {tournament}")

        await post_tournament_data(url, tournament, logger=logger)


if __name__ == "__main__":
    sys.exit(main())
