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

            except (
                MDBReader.MissingDriverException,
                MDBReader.InvalidPasswordError,
            ):
                raise

            except MDBReader.MDBException as err:
                if logger:
                    logger.warn(str(err))

                time.sleep(1)
                retries -= 1
                if retries > 0:
                    if logger:
                        logger.debug(f"retrying {retries} times…")
                    continue
                else:
                    if logger:
                        logger.error("Giving up!")
                    raise

        entries = list(reader.query(ENTRY_QUERY, klass=Entry))
        matches = list(reader.query(MATCH_QUERY, klass=PlayerMatch))

    return Tournament(entries=entries, playermatches=matches)


async def async_load_tournament_from_tpfile(
    connstr, *, logger=None, retries=3
):
    async with AsyncMDBReader(logger=logger) as reader:
        while True:
            try:
                await reader.connect(connstr)
                break

            except (
                MDBReader.MissingDriverException,
                MDBReader.InvalidPasswordError,
            ) as err:
                if logger:
                    logger.error(str(err))
                raise

            except MDBReader.MDBException as err:
                if logger:
                    logger.warn(str(err))

                await asyncio.sleep(1)
                retries -= 1
                if retries > 0:
                    if logger:
                        logger.debug(f"retrying {retries} times…")
                    continue
                else:
                    if logger:
                        logger.error("Giving up!")
                    raise

        entries = reader.query(ENTRY_QUERY, klass=Entry)
        matches = reader.query(MATCH_QUERY, klass=PlayerMatch)

        entries = [e async for e in entries]
        matches = [m async for m in matches]

    tournament = Tournament(entries=entries, playermatches=matches)

    if logger:
        logger.info(f"Parsed tournament: {tournament}")
    return tournament
