import asyncio
import aioodbc
import pyodbc
import re
from collections import OrderedDict
import asyncstdlib as a

try:
    from asyncinotify import Inotify, Mask

    _INOTIFY = True
except TypeError:
    _INOTIFY = False

from tptools.entry import Entry
from tptools.playermatch import PlayerMatch
from tptools.tournament import Tournament
from .base import BaseReader


def make_connstring_from_path(
    path,
    uid,
    pwd,
    *,
    driver="{Microsoft Access Driver (*.mdb, *.accdb)}",
    exclusive=False,
):
    params = OrderedDict(
        DRIVER=driver,
        DBQ=path,
        Pwd=pwd,
    )

    if uid != "Admin":
        params["Uid"] = uid

    if exclusive:
        params["Exclusive"] = 1

    return ";".join(f"{k}={v}" for k, v in params.items())


class TPReader(BaseReader):

    class DriverMissingException(RuntimeError):
        pass

    class UnspecifiedDriverError(RuntimeError):
        pass

    def __init__(
        self, *, auto_convert_int=True, auto_convert_bool=True, logger=None
    ):
        super().__init__(
            auto_convert_int=auto_convert_int,
            auto_convert_bool=auto_convert_bool,
        )
        self._logger = logger

        self._conn = None
        self._cursor = None

    def connect(self, connstr):
        if self._logger:
            self._logger.debug(f"Connecting with connstr '{connstr}'")
        try:
            self._conn = pyodbc.connect(connstr)

        except pyodbc.Error as err:
            if (
                "Can't open lib 'Microsoft Access Driver (*.mdb, *.accdb)'"
                in str(err)
            ):
                raise self.DriverMissingException()

            elif "The driver did not supply an error" in str(err):
                raise self.UnspecifiedDriverError()

            else:
                import ipdb; ipdb.set_trace()  # noqa:E402,E702
                raise

        else:
            self._cursor = self._conn.cursor()

    def disconnect(self):
        if self._cursor:
            self._cursor.close()
            self._cursor = None
        if self._conn:
            self._conn.close()
            self._conn = None

    def query(self, query, *, wrapper_fn=None, klass=dict):
        self._cursor.execute(query)
        if self._logger:
            query = re.sub(r"\s+", " ", query, flags=re.MULTILINE).strip()
            self._logger.debug(f"Yielding records for: {query[:32]}…")
        desc = [x[0] for x in self._cursor.description]
        for n, rec in enumerate(self._cursor, 1):
            d = klass(zip(desc, rec))
            yield wrapper_fn(d) if callable(wrapper_fn) else d
        if self._logger:
            self._logger.debug(f"Query yielded {n} result(s)")

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        if self._logger:
            self._logger.debug(f"Closing connection '{self._connstr}'")
        self.disconnect()


class AsyncTPReader(TPReader):

    def __init__(
        self, *, auto_convert_int=True, auto_convert_bool=True, logger=None
    ):
        super().__init__(
            auto_convert_int=auto_convert_int,
            auto_convert_bool=auto_convert_bool,
            logger=logger,
        )

    async def connect(self, connstr):
        if self._logger:
            self._logger.debug(f"Connecting with connstr '{connstr}'")
        try:
            self._conn = await aioodbc.connect(dsn=connstr)
            self._cursor = await self._conn.cursor()
        except pyodbc.Error as err:
            if (
                "Can't open lib 'Microsoft Access Driver (*.mdb, *.accdb)'"
                in str(err)
            ):
                raise self.DriverMissingException()

            else:
                raise

    async def disconnect(self):
        if self._cursor:
            await self._cursor.close()
            self._cursor = None
        if self._conn:
            await self._conn.close()
            self._conn = None

    async def query(self, query, *, wrapper_fn=None, klass=dict):
        await self._cursor.execute(query)
        if self._logger:
            query = re.sub(r"\s+", " ", query, flags=re.MULTILINE).strip()
            self._logger.debug(f"Yielding records for: {query[:32]}…")
        desc = [x[0] for x in self._cursor.description]
        async for n, rec in a.enumerate(self._cursor, 1):
            d = klass(zip(desc, rec))
            yield wrapper_fn(d) if callable(wrapper_fn) else d
        if self._logger:
            self._logger.debug(f"Query yielded {n} result(s)")

    async def __aenter__(self):
        return self

    async def __aexit__(self, type, value, traceback):
        if self._logger:
            self._logger.debug("Closing connection")
        await self.disconnect()


async def async_tp_watcher(*, path, logger, callback, pollsecs=30):

    if _INOTIFY:
        with Inotify() as inotify:
            inotify.add_watch(path, Mask.MODIFY | Mask.ATTRIB)
            logger.debug(f"Added watcher on {path}")
            await callback(logger)
            async for event in inotify:
                logger.debug(f"Event in {path}: {event}")
                await callback(logger)

    else:
        logger.warning(
            f"No inotify support, resorting to polling ({pollsecs}s)…"
        )
        mtime_last = 0
        while True:
            logger.debug(f"Polling {path}…")
            if (mtime := path.stat().st_mtime) > mtime_last:
                logger.debug(f"{path} has been modified.")
                mtime_last = mtime
                await callback(logger)
            await asyncio.sleep(pollsecs)


async def load_tournament_from_tpfile(connstr, *, logger=None, retries=3):
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
