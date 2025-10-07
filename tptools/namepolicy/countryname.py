# needed < 3.14 so that annotations aren't evaluated
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, overload

from tptools.paramsmodel import ParamsModel

from .policybase import NamePolicy

if TYPE_CHECKING:
    from ..entry import Country


class CountryNamePolicyParams(ParamsModel):
    titlecase: bool = True


# TODO: remove redundancy between these two classes
# It currently seems impossible to do so:
# - https://github.com/pydantic/pydantic/discussions/12204
# - https://discuss.python.org/t/dataclasses-asdicttype-type/103448/2


@dataclass(frozen=True)
class CountryNamePolicy(NamePolicy):
    titlecase: bool = True

    @overload
    def __call__(self, country: Country) -> str: ...

    @overload
    def __call__(self, country: None) -> None: ...

    def __call__(self, country: Country | None) -> str | None:
        if country is None:
            return None

        ret = str(country).title() if self.titlecase else str(country)
        return self._apply_regexps(ret)
