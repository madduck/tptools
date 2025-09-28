from dataclasses import dataclass

from ..sqlmodels import TPClub
from .policybase import PolicyBase


@dataclass(frozen=True)
class ClubNamePolicy(PolicyBase):
    def __init__(self) -> None: ...

    def __call__(self, club: TPClub | None) -> str | None:
        return str(club) if club is not None else None
