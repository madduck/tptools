class BaseReader:

    def __init__(self,
        *,
        auto_convert_int=True,
        auto_convert_bool=True
    ):
        self._auto_convert_int = auto_convert_int
        self._auto_convert_bool = auto_convert_bool

    def __iter__(self):
        return self

    def __next__(self):
        def auto_convert(value):
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

            return value

        return {k: auto_convert(v) for k, v in next(self._records).items()}

    @staticmethod
    def get_record_from_row(klass, colnames, row, *, skipcols=None):
        skipcols = skipcols or []
        return dict(
            (col[0], field)
            for col, field in zip(colnames, row)
            if not col[0] in skipcols
        )
