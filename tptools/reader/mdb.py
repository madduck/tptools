import asyncio
import aioodbc
import pyodbc
import re
from collections import OrderedDict
import asyncstdlib as a

from .base import BaseReader, AsyncBaseReader


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
        DBQ=path.absolute(),
        Pwd=pwd,
    )

    if uid != "Admin":
        params["Uid"] = uid

    if exclusive:
        params["Exclusive"] = 1

    return ";".join(f"{k}={v}" for k, v in params.items())


class MDBReader(BaseReader):

    def __init__(
        self,
        *,
        auto_convert_int=True,
        auto_convert_bool=True,
        auto_convert_emptystring=False,
        logger=None,
    ):
        super().__init__(
            auto_convert_int=auto_convert_int,
            auto_convert_bool=auto_convert_bool,
            auto_convert_emptystring=auto_convert_emptystring,
        )
        self._logger = logger
        self._connstr = None
        self._conn = None
        self._cursor = None

    def connect(self, connstr):
        if self._logger:
            self._logger.debug(f"Connecting with connstr '{connstr}'")
        self._connstr = connstr
        try:
            self._conn = pyodbc.connect(connstr)

        except pyodbc.Error as err:
            if "Can't open lib 'Microsoft Access Driver (*.mdb, *.accdb)'" in str(err):
                raise self.MissingDriverException()

            elif "Not a valid password." in str(err):
                raise self.InvalidPasswordError()

            elif "The driver did not supply an error" in str(err):
                raise self.UnspecifiedDriverError()

            else:
                import ipdb

                ipdb.set_trace()  # noqa:E402,E702
                raise

        else:
            self._cursor = self._conn.cursor()

    def disconnect(self):
        if self._logger and self._connstr:
            self._logger.debug(f"Closing connection '{self._connstr}'")
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


class AsyncMDBReader(AsyncBaseReader):

    def __init__(
        self,
        *,
        auto_convert_int=True,
        auto_convert_bool=True,
        auto_convert_emptystring=False,
        logger=None,
    ):
        super().__init__(
            auto_convert_int=auto_convert_int,
            auto_convert_bool=auto_convert_bool,
            auto_convert_emptystring=auto_convert_emptystring,
        )
        self._logger = logger
        self._connstr = None
        self._conn = None
        self._cursor = None

    async def connect(self, connstr):
        if self._logger:
            self._logger.debug(f"Connecting with connstr '{connstr}'")
        try:
            pool = None if True else await aioodbc.create_pool(dsn=connstr)
            async with asyncio.timeout(5):
                if pool:
                    self._conn = await pool.acquire()
                else:
                    self._conn = await aioodbc.connect(dsn=connstr)
                self._logger.debug(f"Connection acquired: {self._conn}")

        except asyncio.TimeoutError:
            if self._conn:
                await self._conn.disconnect()
            raise self.ConnectionTimeoutError()

        except pyodbc.Error as err:
            if "Can't open lib 'Microsoft Access Driver (*.mdb, *.accdb)'" in str(err):
                raise self.MissingDriverException()

            elif "Not a valid password." in str(err):
                raise self.InvalidPasswordError()

            elif "The driver did not supply an error" in str(err):
                raise self.UnspecifiedDriverError()

            else:
                import ipdb

                ipdb.set_trace()  # noqa:E402,E702
                raise

        else:
            self._cursor = await self._conn.cursor()

    async def disconnect(self):
        if self._logger and self._connstr:
            self._logger.debug(f"Closing connection '{self._connstr}'")
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
