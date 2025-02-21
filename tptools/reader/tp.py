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
            self._cursor = self._conn.cursor()
        except pyodbc.Error as err:
            if (
                "Can't open lib 'Microsoft Access Driver (*.mdb, *.accdb)'"
                in str(err)
            ):
                raise self.DriverMissingException()

            else:
                raise

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
        logger.warning("No inotify support, resorting to polling…")
        mtime_last = 0
        while True:
            logger.debug(f"Polling {path}…")
            if (mtime := path.stat().st_mtime) > mtime_last:
                logger.debug(f"{path} has been modified.")
                mtime_last = mtime
                await callback(logger)
            await asyncio.sleep(pollsecs)
