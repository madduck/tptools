# needed < 3.14 so that annotations aren't evaluated
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, overload

from .policybase import NamePolicy

if TYPE_CHECKING:
    from ..entry import Club


@dataclass(frozen=True)
class ClubNamePolicy(NamePolicy):
    @overload
    def __call__(self, club: Club) -> str: ...

    @overload
    def __call__(self, club: None) -> None: ...

    def __call__(self, club: Club | None) -> str | None:
        if club is None:
            return None

        ret = self._apply_regexps(str(club))
        return ret if ret else None
