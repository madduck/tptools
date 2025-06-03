# needed < 3.14 so that annotations aren't evaluated
from __future__ import annotations

from enum import StrEnum, auto

from .playermatchstatus import PlayerMatchStatus


class MatchStatus(StrEnum):
    READY = auto()
    PENDING = PlayerMatchStatus.PENDING
    PLAYED = PlayerMatchStatus.PLAYED
    NOTPLAYED = PlayerMatchStatus.NOTPLAYED

    @classmethod
    def from_playermatch_status_pair(
        cls, a: PlayerMatchStatus, b: PlayerMatchStatus
    ) -> MatchStatus:
        if a.is_player or b.is_player:
            raise ValueError(
                "MatchStatus needs two PlayerMatchStatus that are not players or byes"
            )

        if a == b:
            return cls(a)

        elif PlayerMatchStatus.NOTPLAYED in (a, b):
            return cls.NOTPLAYED

        else:
            return cls.PENDING
