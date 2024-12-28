import csv

from .base import BaseReader


class CSVReader(BaseReader):

    def __init__(
        self,
        stream,
        *,
        auto_convert_emptystring=True,
        auto_convert_int=True,
        auto_convert_bool=True,
        makeiter=None
    ):
        super().__init__(
            auto_convert_emptystring=auto_convert_emptystring,
            auto_convert_int=auto_convert_int,
            auto_convert_bool=auto_convert_bool,
        )
        self._records = (
            CSVReader._makeiter(stream)
            if makeiter is None
            else makeiter(stream)
        )

    @staticmethod
    def _makeiter(stream):
        return csv.DictReader(stream)
