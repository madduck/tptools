import asyncio
import time


class BaseReader:

    class ReaderException(Exception):
        pass

    class MissingDriverException(ReaderException):
        def __init__(self):
            super().__init__("Missing driver")

    class InvalidPasswordError(ReaderException):
        def __init__(self):
            super().__init__("Invalid password for data file")

    class UnspecifiedDriverError(ReaderException):
        def __init__(self):
            super().__init__("Driver threw an unspecified error")

    class ConnectionTimeoutError(ReaderException):
        def __init__(self):
            super().__init__("Failure to read data within due time")

    def __init__(
        self,
        *,
        auto_convert_int=True,
        auto_convert_bool=True,
        auto_convert_emptystring=True,
        logger=None,
    ):
        self._auto_convert_int = auto_convert_int
        self._auto_convert_bool = auto_convert_bool
        self._auto_convert_emptystring = auto_convert_emptystring
        self._logger = logger
        self._records = {}

    def __iter__(self):
        return self

    def _auto_convert(self, value):
        if self._auto_convert_int:
            try:
                return int(value)
            except ValueError:
                pass

        if self._auto_convert_bool:
            if value in ("True", "true"):
                return True
            elif value in ("False", "false"):
                return False

        if self._auto_convert_emptystring:
            if value == "":
                return None

        return value

    def __next__(self):
        return {k: self._auto_convert(v) for k, v in next(self._records).items()}

    def _connect(self, connstr):
        raise NotImplementedError

    def connect(self, connstr, *, retries=3):
        while True:
            try:
                self._connect(connstr)
                break

            except (
                BaseReader.MissingDriverException,
                BaseReader.InvalidPasswordError,
            ):
                raise

            except BaseReader.ReaderException as err:
                if self._logger:
                    self._logger.warn(str(err))

                retries -= 1
                if retries > 0:
                    time.sleep(1)
                    if self._logger:
                        self._logger.debug(f"retrying {retries} times…")
                    continue
                else:
                    if self._logger:
                        self._logger.error("Giving up!")
                    raise

    def disconnect(self):
        raise NotImplementedError

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.disconnect()

    def query(self, query, *, wrapper_fn=None, klasse=dict):
        raise NotImplementedError

    @staticmethod
    def get_record_from_row(klass, colnames, row, *, skipcols=None):
        skipcols = skipcols or []
        return dict(
            (col[0], field)
            for col, field in zip(colnames, row)
            if not col[0] in skipcols
        )


class AsyncBaseReader(BaseReader):
    def __init__(
        self,
        *,
        auto_convert_int=True,
        auto_convert_bool=True,
        auto_convert_emptystring=True,
        logger=None,
    ):
        super().__init__(
            auto_convert_int=auto_convert_int,
            auto_convert_bool=auto_convert_bool,
            auto_convert_emptystring=auto_convert_emptystring,
            logger=logger,
        )
        del self.__enter__
        del self.__exit__
        del self.__iter__
        del self.__next__

    async def __aiter__(self):
        return self

    async def __anext__(self):
        return {k: self._auto_convert(v) for k, v in next(self._records).items()}

    async def _connect(self, connstr):
        raise NotImplementedError

    async def connect(self, connstr, *, retries=3):
        while True:
            try:
                await self._connect(connstr)
                break

            except (
                BaseReader.MissingDriverException,
                BaseReader.InvalidPasswordError,
            ):
                raise

            except BaseReader.ReaderException as err:
                if self._logger:
                    self._logger.warn(str(err))

                retries -= 1
                if retries > 0:
                    await asyncio.sleep(1)
                    if self._logger:
                        self._logger.debug(f"retrying {retries} times…")
                    continue
                else:
                    if self._logger:
                        self._logger.error("Giving up!")
                    raise

    async def disconnect(self):
        raise NotImplementedError

    async def __aenter__(self):
        return self

    async def __aexit__(self, type, value, traceback):
        await self.disconnect()

    async def query(self, query, *, wrapper_fn=None, klasse=dict):
        raise NotImplementedError
