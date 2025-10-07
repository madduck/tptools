# needed < 3.14 so that annotations aren't evaluated
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, overload

from .policybase import NamePolicy

if TYPE_CHECKING:
    from ..entry import Country


@dataclass(frozen=True)
class CountryNamePolicy(NamePolicy):
    def __init__(self) -> None: ...

    @overload
    def __call__(self, country: Country) -> str: ...

    @overload
    def __call__(self, country: None) -> None: ...

    def __call__(self, country: Country | None) -> str | None:
        return self._apply_regexps(str(country)) if country is not None else None
