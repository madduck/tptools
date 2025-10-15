# needed < 3.14 so that annotations aren't evaluated
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, overload

from tptools.paramsmodel import ParamsModel

from .policybase import NamePolicy

if TYPE_CHECKING:
    from ..entry import Country

logger = logging.getLogger(__name__)


class CountryNamePolicyParams(ParamsModel):
    titlecase: bool = True
    use_country_code: bool = False


# TODO: remove redundancy between these two classes
# It currently seems impossible to do so:
# - https://github.com/pydantic/pydantic/discussions/12204
# - https://discuss.python.org/t/dataclasses-asdicttype-type/103448/2


@dataclass(frozen=True)
class CountryNamePolicy(NamePolicy):
    titlecase: bool = True
    use_country_code: bool = False

    @overload
    def __call__(self, country: Country) -> str: ...

    @overload
    def __call__(self, country: None) -> None: ...

    def __call__(self, country: Country | None) -> str | None:
        if country is None:
            return None

        if self.use_country_code and country.code:
            if self.titlecase or self.regexps:
                logger.warning(
                    "Ignoring CountryNamePolicy.titlecase and .regexp for country code"
                )
            return country.code

        else:
            ret = str(country).title() if self.titlecase else str(country)
            return self._apply_regexps(ret)
