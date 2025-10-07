from dataclasses import dataclass
from typing import overload

from ..draw import Draw
from .policybase import NamePolicy


@dataclass(frozen=True)
class DrawNamePolicy(NamePolicy):
    def __init__(self) -> None: ...

    @overload
    def __call__(self, draw: Draw) -> str: ...

    @overload
    def __call__(self, draw: None) -> None: ...

    def __call__(self, draw: Draw | None) -> str | None:
        return self._apply_regexps(str(draw)) if draw is not None else None
