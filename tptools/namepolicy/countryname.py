# needed < 3.14 so that annotations aren't evaluated
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, overload

from .policybase import PolicyBase

if TYPE_CHECKING:
    from ..entry import Country


@dataclass(frozen=True)
class CountryNamePolicy(PolicyBase):
    def __init__(self) -> None: ...

    def __call__(self, country: Country | None) -> str | None:
        return str(country) if country is not None else None
