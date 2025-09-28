from dataclasses import dataclass

from ..sqlmodels import TPCountry
from .policybase import PolicyBase


@dataclass(frozen=True)
class CountryNamePolicy(PolicyBase):
    def __init__(self) -> None: ...

    def __call__(self, country: TPCountry | None) -> str | None:
        return str(country) if country is not None else None
