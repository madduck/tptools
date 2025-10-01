# needed < 3.14 so that annotations aren't evaluated
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .policybase import PolicyBase

if TYPE_CHECKING:
    from ..entry import Club


@dataclass(frozen=True)
class ClubNamePolicy(PolicyBase):
    def __init__(self) -> None: ...

    def __call__(self, club: Club | None) -> str | None:
        return str(club) if club is not None else None
