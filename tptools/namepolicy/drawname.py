from dataclasses import dataclass
from typing import overload

from ..draw import Draw
from .policybase import PolicyBase


@dataclass(frozen=True)
class DrawNamePolicy(PolicyBase):
    def __init__(self) -> None: ...

    @overload
    def __call__(self, draw: Draw) -> str: ...

    @overload
    def __call__(self, draw: None) -> None: ...

    def __call__(self, draw: Draw | None) -> str | None:
        return str(draw) if draw is not None else None
