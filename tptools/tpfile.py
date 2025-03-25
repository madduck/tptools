import asyncio
import time

from tptools.entry import Entry
from tptools.playermatch import PlayerMatch
from tptools.tournament import Tournament
from tptools.reader.mdb import MDBReader, AsyncMDBReader

ENTRY_QUERY = """
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

MATCH_QUERY = """
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


def load_tournament_from_tpfile(connstr, *, logger=None, retries=3):
    with MDBReader(logger=logger) as reader:
        while True:
            try:
                reader.connect(connstr)
                break

            except MDBReader.UnspecifiedDriverError:
                logger.info("Access driver connection yielded an unspecified error")

            except MDBReader.ConnectionTimeoutError:
                logger.info("Access driver failed to reconnect within due time")

            time.sleep(1)
            retries -= 1
            if retries > 0:
                logger.debug(f"retrying {retries} times…")
                continue
            else:
                logger.error("Access connection failed with unspecified error")
                return

        entries = list(reader.query(ENTRY_QUERY, klass=Entry))
        matches = list(reader.query(MATCH_QUERY, klass=PlayerMatch))

    tournament = Tournament(entries=entries, playermatches=matches)

    if logger:
        logger.info(f"Parsed tournament: {tournament}")
    return tournament


async def async_tp_watcher(*, path, logger, callback, pollfreq=30):
    try:
        from asyncinotify import Inotify, Mask

        _INOTIFY = True
    except TypeError:
        _INOTIFY = False

    if _INOTIFY:
        with Inotify() as inotify:
            inotify.add_watch(path, Mask.MODIFY | Mask.ATTRIB)
            logger.debug(f"Added watcher on {path}")
            await callback(path, logger=logger)
            async for event in inotify:
                logger.debug(f"Event in {path}: {event}")
                await callback(path, logger=logger)

    else:
        logger.warning(f"No inotify support, resorting to polling ({pollfreq}s)…")
        mtime_last = 0
        while True:
            logger.debug(f"Polling {path}…")
            if (mtime := path.stat().st_mtime) > mtime_last:
                logger.debug(f"{path} has been modified.")
                mtime_last = mtime
                await callback(path, logger=logger)
            await asyncio.sleep(pollfreq)


async def async_load_tournament_from_tpfile(connstr, *, logger=None, retries=3):
    async with AsyncMDBReader(logger=logger) as reader:
        while True:
            try:
                await reader.connect(connstr)
                break

            except AsyncMDBReader.UnspecifiedDriverError:
                logger.info("Access driver connection yielded an unspecified error")

            except AsyncMDBReader.ConnectionTimeoutError:
                logger.info("Access driver failed to reconnect within due time")

            await asyncio.sleep(1)
            retries -= 1
            if retries > 0:
                logger.debug(f"retrying {retries} times…")
                continue
            else:
                logger.error("Access connection failed with unspecified error")
                return

        entries = reader.query(ENTRY_QUERY, klass=Entry)
        matches = reader.query(MATCH_QUERY, klass=PlayerMatch)

        entries = [e async for e in entries]
        matches = [m async for m in matches]

    tournament = Tournament(entries=entries, playermatches=matches)

    if logger:
        logger.info(f"Parsed tournament: {tournament}")
    return tournament
