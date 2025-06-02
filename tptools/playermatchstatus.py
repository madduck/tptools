from enum import StrEnum, auto


class PlayerMatchStatus(StrEnum):
    BYE = auto()
    PLAYER = auto()
    PENDING = auto()
    READY = auto()
    PLAYED = auto()
    NOTPLAYED = auto()

    @property
    def is_player(self) -> bool:
        return self in (self.BYE.value, self.PLAYER.value)

    @property
    def is_match(self) -> bool:
        return not self.is_player
