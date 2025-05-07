# needed < 3.14 so that annotations aren't evaluated
from __future__ import annotations

import logging
import warnings
from collections.abc import Iterator
from contextlib import AbstractContextManager, ExitStack, contextmanager
from csv import DictReader
from typing import TYPE_CHECKING

from .interfaces import ConnectsToSource, Queryable, RecordType

if TYPE_CHECKING:
    from collections.abc import Callable, Generator
    from io import TextIOWrapper
    from typing import Any, Type

logger = logging.getLogger(__name__)


class CSVReader(
    AbstractContextManager["CSVReader"],
    Iterator[RecordType],
    ConnectsToSource,
    Queryable,
):
    def __init__(
        self,
        *,
        opener: Callable[..., TextIOWrapper] = open,
    ) -> None:
        self._opener = opener
        self._exitstack = ExitStack()
        self._file: TextIOWrapper | None = None
        self._reader: DictReader[str] | None = None

    def connect(self, connstr: str) -> None:
        logger.debug(f"Opening CSV file: {connstr}")
        self._file = self._exitstack.enter_context(
            self._opener(connstr, mode="r", newline="")
        )

    def disconnect(self) -> None:
        if self._file is not None:
            logger.debug(f"Closing CSV file: {self._file.name}")
            self._file = None
        self._exitstack.close()

    def __exit__(self, *_: Any) -> None:
        self.disconnect()

    def __next__(self) -> RecordType:
        if self._reader is None:
            if self._file:
                self._reader = DictReader(self._file)
            else:
                raise ValueError("CSVReader was not given a file to read")
        return next(self._reader)

    def query(
        self, query: str, *, cls: Type[RecordType] = dict
    ) -> Generator[RecordType]:
        if query:
            warnings.warn(
                "Argument 'query' is ignored in call to CSVReader.query",
                UserWarning,
                stacklevel=2,
            )
        for row in self:
            yield cls(**row)


@contextmanager
def connect(
    connstr: str, *, opener: Callable[..., TextIOWrapper] = open
) -> Generator[CSVReader, Any, Any]:
    with CSVReader(opener=opener) as reader:
        reader.connect(connstr)
        yield reader
