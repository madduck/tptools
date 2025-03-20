import click
import sys
import aiohttp
import asyncio
import pathlib
import re

from tptools.reader.tp import (
    make_connstring_from_path,
    async_tp_watcher,
    AsyncTPReader,
)
from tptools.asyncio import asyncio_run
from tptools.reader.csv import CSVReader
from tptools.entry import Entry
from tptools.playermatch import PlayerMatch
from tptools.tournament import Tournament
from tptools.logger import get_logger, adjust_log_level
from tptools.util import json_dump_with_default

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
                    raise_for_status=True, json_serialize=json_dump_with_default
                ) as session:
                    async with session.post(url, json=matches) as resp:
                        if resp.status != 200:
                            logger.error(f"Data POST failed: {resp.reason}")
                        else:
                            ret = await resp.json()
                            logger.info(
                                "Success transferring "
                                f"{ret.get('nrecords', '(no number returned)')} matches"
                            )
                break

            except aiohttp.ClientConnectorError as err:
                logger.error(f"Connection error: {err}, retrying…")

            except aiohttp.ClientResponseError as err:
                logger.error(f"Response error: {err}, retrying…")

            await asyncio.sleep(5)


async def cb_load_tp_file(connstr, *, logger=None, retries=3):
    entry_query = """
        select e.id as entryid,
        p1.id as player1id, p1.firstname as firstname1,
            p1.name as name1, l1.name as club1, c1.code as country1,
        p2.id as player2id, p2.firstname as firstname2,
            p2.name as name2, l2.name as club2, c2.code as country2
        from
        ( ( ( ( (
                  Entry e inner join Player p1 on e.player1 = p1.id
                )
                left outer join Player p2 on e.player2 = p2.id
              )
              left outer join Country c1 on p1.country = c1.id
            )
            left outer join Country c2 on p2.country = c2.id
          )
          left outer join Club l1 on p1.club = l1.id
        )
        left outer join Club l2 on p2.club = l2.id
    """

    match_query = """
        select *, m.id as matchid, d.id as drawid,
        d.name as drawname, v.name as eventname,
        c.name as courtname, l.name as locationname
        from
        ( ( (
              PlayerMatch m inner join Draw d on (m.draw = d.id)
            )
            inner join Event v on (d.event = v.id)
          )
          left outer join Court c on (m.court = c.id)
        )
        left outer join Location l on (d.location = l.id)
    """

    async with AsyncTPReader(logger=logger) as reader:
        while True:
            try:
                await reader.connect(connstr)
                break

            except AsyncTPReader.UnspecifiedDriverError:
                import ipdb; ipdb.set_trace()  # noqa:E402,E702
                await asyncio.sleep(1)
                retries -= 1
                if retries > 0:
                    continue
                else:
                    return

        entries = reader.query(entry_query, klass=Entry)
        matches = reader.query(match_query, klass=PlayerMatch)

        entries = [e async for e in entries]
        matches = [m async for m in matches]

    tournament = Tournament(entries=entries, playermatches=matches)

    if logger:
        logger.info(f"Parsed tournament: {tournament}")
    return tournament


@click.command
@click.option(
    "--url", "-u", help="URL to send events to (stdout if not provided)"
)
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
    "--pollsecs",
    "-p",
    type=click.INT,
    help="Frequency in seconds to poll TP file in the absence of inotify",
    default=30,
)
@click.option(
    "--verbose", "-v", count=True, help="Increase verbosity of log output"
)
@click.option(
    "--quiet",
    "-q",
    is_flag=True,
    help="Output as little information as possible"
)
@click.option("--test", "-t", is_flag=True, help="Use test data for this run")
@click.pass_context
@asyncio_run
async def main(
    ctx, verbose, quiet, url, tpfile, tpuser, tppasswd, test, pollsecs
):
    adjust_log_level(logger, verbose, quiet=quiet)

    if test:
        if tpfile:
            raise click.BadParameter("--tpfile and --test cannot be combined")
        if tpuser and tpuser != TP_DEFAULT_USER:
            raise click.BadParameter("--tpuser and --test cannot be combined")
        if tppasswd:
            raise click.BadParameter(
                "--tppasswd and --test cannot be combined"
            )
        connstr = None

    elif tpfile:
        if not tppasswd:
            raise click.BadParameter("Missing TP password")

        connstr = make_connstring_from_path(tpfile, tpuser, tppasswd)

    else:
        raise click.BadParameter("--tpfile must be specified without --test")

    if connstr:

        async def callback(logger):
            tournament = await cb_load_tp_file(connstr, logger=logger)
            if tournament:
                await post_tournament_data(url, tournament, logger=logger)

        try:
            async with asyncio.TaskGroup() as tg:
                t1 = tg.create_task(
                    async_tp_watcher(
                        path=tpfile,
                        logger=logger,
                        callback=callback,
                        pollsecs=pollsecs,
                    ),
                    name="TPWatcher",
                )
                logger.debug(f"Created TP watcher task: {t1}")

        except* AsyncTPReader.DriverMissingException:
            if isinstance(
                t1.exception(), AsyncTPReader.DriverMissingException
            ):
                logger.error(
                    "Missing Microsoft Access driver. Are you on Windows?"
                )
                sys.exit(1)

            else:
                raise

    else:
        logger.warning("Test-mode with static, fake data")

        fixtures = (
            pathlib.Path(__file__).parent.parent / "tests" / "csv_fixtures"
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
