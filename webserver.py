#!/usr/bin/python

import argparse
import sys
import asyncio
import re
import json
import logging
import hashlib
from pathlib import Path
from aiohttp import web
from aiohttp_basicauth_middleware import basic_auth_middleware
from contextlib import suppress

from tptools.reader.tp import (
    make_connstring_from_path,
    async_tp_watcher,
    AsyncTPReader,
)
from tptools.reader.csv import CSVReader
from tptools.entry import Entry
from tptools.playermatch import PlayerMatch
from tptools.tournament import Tournament
from tptools.jsonfeed import JSONFeedMaker
from tptools.logger import get_logger, adjust_log_level


APPKEY_TP_STATE = web.AppKey("tp_state", dict)
APPKEY_TOURNAMENT = web.AppKey("tournament", Tournament)


def create_app(connstr=None, logger=None):
    if not logger:
        logger = get_logger()
        adjust_log_level(logger, 2)

    middlewares = [
        basic_auth_middleware(
            ("/resultDISABLED",),
            {
                "squore": "1c5643819209005cd924c5d0e05cbe70f5293c0f47dc53954224d5941b6beea0"  # noqa:E501
            },
            lambda x: hashlib.sha256(bytes(x, encoding="utf-8")).hexdigest(),
        )
    ]

    app = web.Application(logger=logger, middlewares=middlewares)

    state = {}
    app[APPKEY_TP_STATE] = state

    if connstr:
        async def create_tp_watcher_task(app):
            async def cb_load_tp_file(logger):
                logger.debug(f"Reloading TP data from {connstr}")

                entry_query = """
                    select e.id as entryid,
                    p1.id as player1id, p1.firstname as firstname1,
                      p1.name as name1, l1.name as club1, c1.code as country1,
                    p2.id as player2id, p2.firstname as firstname2,
                      p2.name as name2, l2.name as club2, c2.code as country2
                    from
                    (
                    (
                      (
                      (
                        (
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
                    (
                      (
                        (
                        PlayerMatch m inner join Draw d on (m.draw = d.id)
                        )
                        inner join Event v on (d.event = v.id)
                      )
                      left outer join Court c on (m.court = c.id)
                    )
                    left outer join Location l on (d.location = l.id)
                """

                async with AsyncTPReader(logger=logger) as reader:
                    await reader.connect(connstr)

                    entries = reader.query(entry_query, klass=Entry)
                    matches = reader.query(match_query, klass=PlayerMatch)

                    entries = [e async for e in entries]
                    matches = [m async for m in matches]

                    tournament = Tournament(
                        entries=entries, playermatches=matches
                    )

                logger.info(f"Parsed tournament: {tournament}")
                state[APPKEY_TOURNAMENT] = tournament

            task = asyncio.create_task(
                async_tp_watcher(
                    path=args.input,
                    logger=app.logger,
                    callback=cb_load_tp_file,
                ),
                name="TPWatcher",
            )
            app.logger.debug(f"Created TP watcher task: {task}")

            yield

            app.logger.debug(f"Tearing down TP watcher task: {task}")
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task

        app.cleanup_ctx.append(create_tp_watcher_task)

    else:
        logger.warning("Test-mode with static, fake data")

        with open("tests/csv_fixtures/playermatches.csv", newline="") as f:
            matches = [PlayerMatch(r) for r in CSVReader(f)]
        with open("tests/csv_fixtures/playerentries.csv", newline="") as f:
            entries = [Entry(r) for r in CSVReader(f)]

        tournament = Tournament(entries=entries, playermatches=matches)

        logger.info(f"Parsed test tournament: {tournament}")
        state[APPKEY_TOURNAMENT] = tournament

    routes.static("/flags", "./flags")
    app.add_routes(routes)

    return app


routes = web.RouteTableDef()


# @routes.get("/feeds")
# async def feeds(request):
#    logger.debug(f"{request.method} {request.url} from {request.remote}")
#
#    feeds = dict(
#        ValidFrom="19700101",
#        ValidTo="20991231",
#        Section="Section",
#        Name="Name",
#        FeedMatches="http://192.168.122.33:8080/matches",
#    )
#    return web.json_response(
#        [
#            feeds,
#        ]
#    )


@routes.get("/matches")
async def matches(request):
    logger = request.app.logger
    logger.debug(f"{request.method} {request.url} from {request.remote}")

    include_params = {}
    for p in ("include_played", "include_not_ready"):
        if request.query.get(p) in ("1", "true", "yes"):
            logger.debug(f"Setting '{p}=True'")
            include_params[p] = True

    matches = request.app[APPKEY_TP_STATE][APPKEY_TOURNAMENT].get_matches(
        **include_params
    )

    def court_xform(court):
        return (
            re.sub(r"^(?:Court *|C)?(?P<nr>\d+)$", r"Court \g<nr>", court)
            if court
            else None
        )

    if court := request.query.get("court"):
        logger.info(
            f"Matches request received for court '{court_xform(court)}'"
        )

    matches_by_court = {}
    matches_without_court = []
    only_this_court = request.query.get("only_this_court") in ("1", "true", "yes")
    for match in sorted(matches, key=lambda m: m.time):

        if not match.court and not only_this_court:
            logger.debug("Found a match without an assigned court")
            matches_without_court.append(match)

        else:
            sect = " " + court_xform(match.court)
            court_nr = re.search(r"0*(?P<nr>[1-9]\d*)$", match.court)

            if court == match.court or (court_nr and court_nr["nr"] == court):
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
            "${FirstOfList:~${A}~${A.name}~} [${A.club}] - "
            "${FirstOfList:~${B}~${B.name}~} [${B.club}] : "
            "${result}"
        )
    }

    jfm = JSONFeedMaker(
        matches=matches_by_court, court_xform=court_xform, **config
    )

    return web.json_response(jfm.get_data())


@routes.get("/players")
async def players(request):
    logger = request.app.logger
    logger.debug(f"{request.method} {request.url} from {request.remote}")

    entries = request.app[APPKEY_TP_STATE][APPKEY_TOURNAMENT].get_entries()
    names = {Entry.make_team_name(e.players) for e in entries}
    return web.Response(text="\n".join(names))


@routes.post("/result")
async def result(request):
    logger = request.app.logger
    logger.debug(f"{request.method} {request.url} from {request.remote}")

    try:
        data = await request.json()

    except json.decoder.JSONDecodeError:
        logger.error(f"Invalid JSON received: {await request.text()}")
        raise web.HTTPUnprocessableEntity(reason="Invalid JSON in request")

    try:
        message = f"Recorded game with ID {data['metadata']['sourceID']}"
        if "isVictoryFor" in data:
            message += (
                f", won {data['gamescores']} by "
                f"{data['players'][data['isVictoryFor']]}"
            )
        else:
            message += (
                f", at game score {data['result']} ({data['gamescores']} …)"
            )

    except KeyError as e:
        raise web.HTTPUnprocessableEntity(
            reason="Missing information in JSON data",
            text=f"The following key is missing from the JSON data: {e}",
        )

    except TypeError as e:
        raise web.HTTPUnprocessableEntity(
            reason="Wrong information in JSON data",
            text=f"The following TypeError occurred: {e}",
        )

    logger.info(message)
    return web.json_response({"message": message})


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Read TP files into JSON data structures",
        argument_default=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="count",
        default=0,
        help="Increase verbosity beyond WARNING",
    )
    hgroup = parser.add_mutually_exclusive_group(required=False)
    hgroup.add_argument(
        "--host",
        action="append",
        default=None,
        help="IP/host or sequence of IPs/hosts for HTTP server to listen on",
    )
    hgroup.add_argument(
        "--public",
        action="store_true",
        default=False,
        help="Listen on all interfaces and IPs",
    )
    parser.add_argument(
        "--port",
        "-p",
        type=int,
        default=8080,
        help="Port for HTTP server to listen on",
    )
    ingroup = parser.add_mutually_exclusive_group(required=True)
    ingroup.add_argument(
        "--test",
        "-t",
        default=False,
        action="store_true",
        help="Use fake test data for this run",
    )
    ingroup.add_argument(
        "--input",
        "-i",
        type=Path,
        help="TP file to read",
    )
    parser.add_argument(
        "--user",
        default="Admin",
        help="DB user to use with --input",
    )
    parser.add_argument(
        "--password",
        default="d4R2GY76w2qzZ",
        help="DB password to use with --input",
    )

    args = parser.parse_args()

    logger = get_logger()
    adjust_log_level(logger, args.verbose)

    if args.test:
        if args.user and args.user != parser.get_default("user"):
            logger.warning(f"Specifying --user with --test makes no sense")

        if args.password and args.password != parser.get_default("password"):
            logger.warning("Specifying --password with --test makes no sense")

    elif not args.input.exists():
        logger.error(f"File {args.input} does not exist")
        sys.exit(2)

    try:
        if args.test:
            connstr = None

        else:
            connstr = make_connstring_from_path(
                args.input, args.user, args.password
            )

        adjust_log_level(get_logger("aiohttp.access"), 0)

        host = args.host or (
            ["::", "0.0.0.0"] if args.public else ["::1", "127.0.0.1"]
        )

        app = create_app(connstr, logger)
        logger.info(f"Starting HTTP server to listen on {host}, port {args.port}")
        web.run_app(
            app,
            host=host,
            port=args.port,
            print=None,
            handler_cancellation=True,
        )

    except Exception as e:
        import traceback

        traceback.print_exception(e, file=sys.stderr)
