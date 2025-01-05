#!/usr/bin/python

import argparse
import sys
import asyncio
import re
import json
import logging
import hashlib
import aiosqlite
import datetime
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


APPKEY_CLI_ARGS = web.AppKey("cli_args", argparse.Namespace)
APPKEY_TP_STATE = web.AppKey("tp_state", dict)
APPKEY_TOURNAMENT = web.AppKey("tournament", Tournament)
APPKEY_RESULTS_DB = web.AppKey("results_db", aiosqlite.core.Connection)


def make_cli_parser():

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
    parser.add_argument(
        "--database",
        "-d",
        type=Path,
        default=None,
        help="Database where to store results as they come in",
    )
    return parser


def create_app(*, logger=None, cli_parser=None):

    logger = logger or get_logger("tptools")
    parser = cli_parser or make_cli_parser()

    args = parser.parse_args()

    adjust_log_level(logger, args.verbose)

    if args.test:
        if args.user and args.user != parser.get_default("user"):
            logger.warning("Specifying --user with --test makes no sense")

        if args.password and args.password != parser.get_default("password"):
            logger.warning("Specifying --password with --test makes no sense")

        connstr = None

    elif not args.input.exists():
        logger.error(f"File {args.input} does not exist")
        sys.exit(2)

    else:
        connstr = make_connstring_from_path(
            args.input, args.user, args.password
        )

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

    app[APPKEY_CLI_ARGS] = args

    state = {}
    app[APPKEY_TP_STATE] = state

    if connstr:

        async def create_tp_watcher_task(app):
            async def cb_load_tp_file(logger):
                logger.info(f"Reloading TP data from {connstr}")

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

    async def connect_to_database(app):
        logging.getLogger("aiosqlite").setLevel(logging.INFO)
        dbname = args.database or ":memory:"
        init_required = not args.database or not args.database.exists()
        async with aiosqlite.connect(dbname) as db:
            if init_required:
                logger.info(f"Initialising database {dbname}")
                await db.execute(
                    """
                    create table results(
                      id integer primary key unique not null,
                      timestamp timestamp not null default CURRENT_TIMESTAMP,
                      matchid integer not null,
                      entry1 integer not null,
                      entry2 integer not null,
                      result text not null,
                      finished bool default 0,
                      acked bool default 0
                    );
                    """
                )

            # db.row_factory = aiosqlite.Row
            app.logger.debug(f"Connected to SQLite database: {dbname}")
            app[APPKEY_RESULTS_DB] = db
            yield
            app.logger.debug(f"Disconnecting from database: {db}")

    app.cleanup_ctx.append(connect_to_database)

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


@routes.get("/v1/squore/matches")
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
            logger.debug(f"Found a match {match.id} without an assigned court")
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
        ),
        "PostResult": str(request.url.parent / "result"),
    }

    jfm = JSONFeedMaker(
        matches=matches_by_court, court_xform=court_xform, **config
    )

    return web.json_response(jfm.get_data())


@routes.get("/v1/squore/players")
async def players(request):
    logger = request.app.logger
    logger.debug(f"{request.method} {request.url} from {request.remote}")

    entries = request.app[APPKEY_TP_STATE][APPKEY_TOURNAMENT].get_entries()
    names = {Entry.make_team_name(e.players) for e in entries}
    return web.Response(text="\n".join(names))


@routes.post("/v1/squore/result")
async def result(request):
    logger = request.app.logger
    logger.debug(f"{request.method} {request.url} from {request.remote}")

    try:
        try:
            data = await request.json()
            matchid = int(data["metadata"]["sourceID"])

        except json.decoder.JSONDecodeError:
            logger.error(f"Invalid JSON received: {await request.text()}")
            raise web.HTTPUnprocessableEntity(reason="Invalid JSON in request")

        except TypeError as e:
            logger.error(f"Invalid type received, probably match ID: {e}")
            raise web.HTTPUnprocessableEntity(reason="Invalid match ID")

        try:
            message = f"Received results for game with ID {matchid}"
            if "isVictoryFor" in data:
                message += (
                    f", won {data['gamescores']} by "
                    f"{data['players'][data['isVictoryFor']]}"
                )
            else:
                message += f", at game score {data['result']} ({data['gamescores']} …)"

            logger.info(message)

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

        tournament = request.app[APPKEY_TP_STATE][APPKEY_TOURNAMENT]

        match = tournament.get_match(matchid)

        if not match:
            logger.error(f"No match found for ID {matchid}")
            raise web.HTTPNotFound(text=f"No match found for ID {matchid}")

        logger.debug(f"Found match {match} for results")

        db = request.app[APPKEY_RESULTS_DB]

        def gamescores_to_json_array(scores):
            return json.dumps([tuple(g.split('-')) for g in scores.split(',')])

        await db.execute(
            "INSERT INTO results"
            "(matchid, entry1, entry2, result, finished) "
            "values (?, ?, ?, ?, ?)",
            (
                matchid,
                match.player1.id,
                match.player2.id,
                gamescores_to_json_array(data["gamescores"]),
                "isVictoryFor" in data,
            ),
        )
        await db.commit()

        message = (
            f'Recorded result {data["gamescores"]} for match {matchid}.\n\n'
            "Thank you for your time!\n\n"
            "Please make sure the players know\n"
            "they need to mark&ref the next game!"
        )

    except (web.HTTPUnprocessableEntity, web.HTTPNotFound) as e:
        message = (
            f"An error occurred processing match ID {matchid}.\n\n"
            f"Please show this to tournament control.\n\n"
            f"Error: {e}"
        )

    return web.json_response({"message": message})


@routes.get("/v1/tc/results")
async def todo(request):
    logger = request.app.logger
    logger.debug(f"{request.method} {request.url} from {request.remote}")

    tournament = request.app[APPKEY_TP_STATE][APPKEY_TOURNAMENT]
    ret = []
    db = request.app[APPKEY_RESULTS_DB]
    query = "SELECT * FROM results WHERE finished "
    if not request.query.get("include_acked", 0) in ("1", "yes", "true"):
        query += "AND NOT acked "
    query += "ORDER BY timestamp"
    logger.debug(f"Running query: {query}")
    async with db.execute(query) as cursor:
        colnames = [x[0] for x in cursor.description]
        async for result in cursor:
            record = dict(zip(colnames, result))
            matchid = record.get("matchid")
            match = tournament.get_match(record.get("matchid"))
            if not match:
                logger.error(
                    f"Cannot find match ID {matchid} "
                    f"for result record {record['id']}"
                )
                continue
            ret.append(
                {
                    "record": record,
                    "match": match.as_dict(),
                }
            )

    ret = {
        "timestamp": datetime.datetime.now().strftime("%F %H:%M:%S"),
        "version": 1,
        "data": ret,
    }
    return web.json_response(
        ret, headers={"Access-Control-Allow-Origin": "*"}
    )


@routes.get(r"/v1/tc/results/ack/{resid:\d+}")
async def ack(request):
    logger = request.app.logger
    logger.debug(f"{request.method} {request.url} from {request.remote}")

    resid = request.match_info["resid"]
    db = request.app[APPKEY_RESULTS_DB]
    unack = request.query.get("unack", 0)
    query = (
        "UPDATE results SET acked = ? "
        f"WHERE id = ? AND {'' if unack else 'not '}acked RETURNING *"
    )
    logger.debug(f"Running query: {query}, ({not(unack)}, {resid})")
    async with db.execute(query, (not (unack), resid)) as cursor:
        rec = await cursor.fetchone()
        if rec:
            status = 200
            message = f"Success updating record with ID {resid}"
        else:
            status = 404
            message = (
                f"No record with ID {resid} found to "
                f"{'un' if unack else ''}ack"
            )

    await db.commit()
    return web.json_response(
        {"message": message, "record": rec}, status=status,
        headers={"Access-Control-Allow-Origin": "*"}
    )


@routes.get("/v1/tc/results/ws")
async def ws_handler(request):

    ws = web.WebSocketResponse()
    await ws.prepare(request)

    async for msg in ws:
        if msg.type == aiohttp.WSMsgType.TEXT:
            if msg.data == 'close':
                await ws.close()
            elif msg.data == 'sub':
                
                await ws.send_str(msg.data + '/answer')
        elif msg.type == aiohttp.WSMsgType.ERROR:
            print('ws connection closed with exception %s' %
                  ws.exception())

    return ws


if __name__ == "__main__":

    try:
        parser = make_cli_parser()

        hgroup = parser.add_mutually_exclusive_group(required=False)
        hgroup.add_argument(
            "--host",
            action="append",
            default=None,
            help="IP/host / sequence of IPs/hosts for HTTP server to listen on",  # noqa:E501
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

        app = create_app(cli_parser=parser)

        logger = app.logger
        args = app[APPKEY_CLI_ARGS]

        host = args.host or (
            ["::", "0.0.0.0"] if args.public else ["::1", "127.0.0.1"]
        )

        logger.info(
            f"Starting HTTP server to listen on {host}, port {args.port}"
        )
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
